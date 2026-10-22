#!/usr/bin/env python3
"""
Automatyczny skaner sesyjny GPW / NewConnect z powiadomieniami E-mail.
Skrypt do uruchamiania codziennie po godz. 18:00 (np. przez GitHub Actions o 18:15).

Analizuje spółki z GPW i NewConnect pod kątem Strategii Żółwi (Klasycznej i Własnej),
sprawdza filtr obrotu 100k PLN z 60 sesji, oblicza Unit Size i wysyła raport e-mail.
"""

import os
import sys
import argparse
import smtplib
from datetime import datetime, date
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import pandas as pd
import numpy as np
import yfinance as yf

from gpw_tickers import GPW_TICKERS, get_ticker_list, get_ticker_info


def calculate_indicators(df: pd.DataFrame, entry_period: int, exit_period: int, atr_period: int = 20):
    """Oblicza wskaźniki Turtle dla danej spółki."""
    data = df.copy()
    prev_close = data["Close"].shift(1)
    hl = data["High"] - data["Low"]
    hc = (data["High"] - prev_close).abs()
    lc = (data["Low"] - prev_close).abs()
    data["TR"] = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    data["ATR"] = data["TR"].rolling(window=atr_period, min_periods=1).mean()
    data["Donchian_High"] = data["High"].shift(1).rolling(window=entry_period).max()
    data["Donchian_Low"] = data["Low"].shift(1).rolling(window=exit_period).min()
    data["Turnover"] = data["Close"] * data["Volume"]
    return data


def calculate_unit_size(capital: float, risk_pct: float, atr: float, price: float) -> int:
    """Kalkulacja liczby akcji wg wzoru Żółwi (1% ryzyka kapitału)."""
    if atr <= 0 or price <= 0:
        return 0
    cash_at_risk = capital * (risk_pct / 100.0)
    raw_units = int(np.floor(cash_at_risk / atr))
    max_units = int(np.floor(capital / price))
    return max(0, min(raw_units, max_units))


def run_scanner(min_turnover: float = 100000, turnover_days: int = 60,
                capital: float = 100000, risk_pct: float = 1.0):
    """
    Skanuje spółki pod kątem dwóch wariantów strategii:
    1. System 1 (Klasyczny): 20 dni wejście / 10 dni wyjście
    2. System 2 (Długoterminowy / Własny): 55 dni wejście / 20 dni wyjście
    """
    tickers = get_ticker_list()
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Rozpoczynanie skanowania {len(tickers)} spółek GPW/NC...")

    classic_signals = []
    custom_signals = []
    liquid_count = 0

    for symbol in tickers:
        try:
            df = yf.download(symbol, start="2023-01-01", progress=False, auto_adjust=False)
            if df.empty or len(df) < turnover_days:
                continue

            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            # Filtr płynności
            recent_turnover = (df["Close"] * df["Volume"]).tail(turnover_days).mean()
            if recent_turnover < min_turnover:
                continue

            liquid_count += 1
            info = get_ticker_info(symbol)

            # 1. System Klasyczny (20 / 10)
            df_c = calculate_indicators(df, entry_period=20, exit_period=10, atr_period=20)
            last_c = df_c.iloc[-1]
            close = float(last_c["Close"])
            atr = float(last_c["ATR"])
            c_high = float(last_c["Donchian_High"])
            c_low = float(last_c["Donchian_Low"])
            unit = calculate_unit_size(capital, risk_pct, atr, close)
            sl = round(close - 2.0 * atr, 2)

            if close > c_high:
                classic_signals.append({
                    "symbol": symbol,
                    "name": info["name"],
                    "action": "KUPUJ (Breakout)",
                    "price": round(close, 2),
                    "channel": round(c_high, 2),
                    "atr": round(atr, 2),
                    "sl": sl,
                    "units": unit,
                    "exposure": round(unit * close, 2),
                    "turnover": round(recent_turnover, 0)
                })
            elif close < c_low:
                classic_signals.append({
                    "symbol": symbol,
                    "name": info["name"],
                    "action": "SPRZEDAJ (Exit)",
                    "price": round(close, 2),
                    "channel": round(c_low, 2),
                    "atr": round(atr, 2),
                    "sl": sl,
                    "units": 0,
                    "exposure": 0,
                    "turnover": round(recent_turnover, 0)
                })

            # 2. System Własny / Długoterminowy (55 / 20)
            df_cust = calculate_indicators(df, entry_period=55, exit_period=20, atr_period=20)
            last_cust = df_cust.iloc[-1]
            cust_high = float(last_cust["Donchian_High"])
            cust_low = float(last_cust["Donchian_Low"])

            if close > cust_high:
                custom_signals.append({
                    "symbol": symbol,
                    "name": info["name"],
                    "action": "KUPUJ (Breakout 55d)",
                    "price": round(close, 2),
                    "channel": round(cust_high, 2),
                    "atr": round(atr, 2),
                    "sl": sl,
                    "units": unit,
                    "exposure": round(unit * close, 2),
                    "turnover": round(recent_turnover, 0)
                })
            elif close < cust_low:
                custom_signals.append({
                    "symbol": symbol,
                    "name": info["name"],
                    "action": "SPRZEDAJ (Exit 20d)",
                    "price": round(close, 2),
                    "channel": round(cust_low, 2),
                    "atr": round(atr, 2),
                    "sl": sl,
                    "units": 0,
                    "exposure": 0,
                    "turnover": round(recent_turnover, 0)
                })

        except Exception as e:
            print(f"Błąd analizy {symbol}: {e}", file=sys.stderr)

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Zakończono analizę. Płynne spółki: {liquid_count}. Sygnały klasyczne: {len(classic_signals)}, Sygnały własne: {len(custom_signals)}.")
    return classic_signals, custom_signals, liquid_count


def build_html_report(classic_signals, custom_signals, liquid_count, capital, min_turnover):
    """Tworzy estetyczny raport HTML dla wiadomości e-mail."""
    today_str = date.today().strftime("%d.%m.%Y")
    
    def generate_table(signals):
        if not signals:
            return "<p style='color: #64748b; font-style: italic;'>Brak nowych sygnałów wybicia na dzisiejszej sesji.</p>"
        
        rows = ""
        for s in signals:
            is_buy = "KUPUJ" in s["action"]
            color = "#16a34a" if is_buy else "#dc2626"
            badge = f"<span style='background-color:{color}; color:white; padding:3px 8px; border-radius:4px; font-weight:bold;'>{s['action']}</span>"
            rows += f"""
            <tr style='border-bottom: 1px solid #e2e8f0; text-align: left;'>
                <td style='padding: 8px; font-weight: bold;'>{s['symbol']}</td>
                <td style='padding: 8px;'>{s['name']}</td>
                <td style='padding: 8px;'>{badge}</td>
                <td style='padding: 8px; font-weight: bold;'>{s['price']} PLN</td>
                <td style='padding: 8px;'>{s['channel']} PLN</td>
                <td style='padding: 8px;'>{s['atr']}</td>
                <td style='padding: 8px; color: #b91c1c;'>{s['sl']} PLN</td>
                <td style='padding: 8px; font-weight: bold;'>{s['units']} szt.</td>
                <td style='padding: 8px;'>{s['exposure']:,.0f} PLN</td>
            </tr>
            """

        return f"""
        <table style='width:100%; border-collapse: collapse; margin-top: 10px; font-family: sans-serif; font-size: 13px;'>
            <thead>
                <tr style='background-color: #0f172a; color: white;'>
                    <th style='padding: 8px;'>Ticker</th>
                    <th style='padding: 8px;'>Nazwa</th>
                    <th style='padding: 8px;'>Sygnał</th>
                    <th style='padding: 8px;'>Cena</th>
                    <th style='padding: 8px;'>Poziom Wybicia</th>
                    <th style='padding: 8px;'>ATR (N)</th>
                    <th style='padding: 8px;'>Stop Loss</th>
                    <th style='padding: 8px;'>Unit Size</th>
                    <th style='padding: 8px;'>Wartość</th>
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>
        """

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
    </head>
    <body style='font-family: Arial, sans-serif; line-height: 1.5; color: #1e293b; background-color: #f8fafc; padding: 20px;'>
        <div style='max-width: 900px; margin: 0 auto; background: #ffffff; border-radius: 8px; padding: 24px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);'>
            <div style='border-bottom: 2px solid #0f172a; padding-bottom: 12px; margin-bottom: 20px;'>
                <h1 style='margin: 0; color: #0f172a; font-size: 22px;'>🐢 GPW Turtle Trading - Raport Dzienny ({today_str})</h1>
                <p style='margin: 4px 0 0; color: #64748b; font-size: 14px;'>
                    Analiza po sesji giełdowej | Spółki spełniające płynność: <strong>{liquid_count}</strong> | Filtr: min. {min_turnover:,.0f} PLN (60 sesji) | Kapitał bazy: {capital:,.0f} PLN
                </p>
            </div>

            <h2 style='color: #0369a1; font-size: 17px; margin-top: 24px; border-left: 4px solid #0369a1; padding-left: 8px;'>
                1. Strategia Klasyczna Żółwi (System 1: Wejście 20d / Wyjście 10d / 1% ryzyka)
            </h2>
            {generate_table(classic_signals)}

            <h2 style='color: #4338ca; font-size: 17px; margin-top: 32px; border-left: 4px solid #4338ca; padding-left: 8px;'>
                2. Strategia Własna / Długoterminowa (System 2: Wejście 55d / Wyjście 20d / 1% ryzyka)
            </h2>
            {generate_table(custom_signals)}

            <div style='margin-top: 32px; padding: 12px; background-color: #f1f5f9; border-radius: 6px; font-size: 12px; color: #475569;'>
                <strong>Zasady Turtle Trading:</strong> Pozycja <em>Unit Size</em> kalkulowana jest tak, aby 1x ATR odpowiadał dokładnie 1% kapitału. Stop Loss umieszczony jest 2x ATR poniżej ceny zamknięcia.
            </div>
        </div>
    </body>
    </html>
    """
    return html


def send_email(subject: str, html_content: str):
    """Wysyła raport e-mail przez SMTP Gmail."""
    user = os.environ.get("EMAIL_USER")
    password = os.environ.get("EMAIL_PASS")
    receiver = os.environ.get("EMAIL_RECEIVER", user)
    smtp_server = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", 587))

    if not user or not password:
        print("[OSTRZEŻENIE] Brak zmiennych EMAIL_USER i EMAIL_PASS. E-mail nie został wysłany. Skonfiguruj Secrets w GitHub Actions.")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = receiver

    part_html = MIMEText(html_content, "html", "utf-8")
    msg.attach(part_html)

    try:
        print(f"Wysyłanie e-maila do {receiver} przez {smtp_server}:{smtp_port}...")
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.ehlo()
        server.starttls()
        server.login(user, password)
        server.sendmail(user, [receiver], msg.as_string())
        server.quit()
        print("✅ E-mail został pomyślnie wysłany!")
        return True
    except Exception as e:
        print(f"❌ Błąd wysyłania e-maila: {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(description="GPW Turtle Trading Daily Runner")
    parser.add_argument("--dry-run", action="store_true", help="Uruchom skaner bez wysyłania e-maila")
    parser.add_argument("--min-turnover", type=float, default=100000, help="Minimalny średni obrót 60d w PLN")
    parser.add_argument("--capital", type=float, default=100000, help="Kapitał referencyjny w PLN")
    parser.add_argument("--risk", type=float, default=1.0, help="Procent ryzyka na pozycję (np. 1.0)")
    args = parser.parse_args()

    classic_signals, custom_signals, liquid_count = run_scanner(
        min_turnover=args.min_turnover,
        turnover_days=60,
        capital=args.capital,
        risk_pct=args.risk
    )

    subject = f"🐢 GPW Turtle Signals [{date.today().strftime('%d.%m.%Y')}] - K: {len([s for s in classic_signals if 'KUPUJ' in s['action']])} Kup / S: {len([s for s in classic_signals if 'SPRZEDAJ' in s['action']])} Sprzedaj"
    html_report = build_html_report(classic_signals, custom_signals, liquid_count, args.capital, args.min_turnover)

    if args.dry_run:
        print("\n=== TRYB DRY RUN (BEZ WYSYŁANIA) ===")
        print(f"Temat: {subject}")
        print(f"Znaleziono {len(classic_signals)} sygnałów klasycznych i {len(custom_signals)} sygnałów własnych.")
    else:
        send_email(subject, html_report)


if __name__ == "__main__":
    main()
