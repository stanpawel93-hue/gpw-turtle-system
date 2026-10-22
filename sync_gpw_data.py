"""
Moduł automatycznego pobierania i synchronizacji bazy spółek z oficjalnych plików GPW i NewConnect.
Adresy źródłowe:
- GPW: https://www.gpw.pl/pub/GPW/files/quotations_xls/PL/akcje-i-pda/notowania-ciagle/{date_str}.xls
- NewConnect: https://newconnect.pl/pub/NEWCONNECT/files/quotations_xls/PL/notowania-ciagle/{date_str}.xls

Dwuetapowa architektura:
1. Pobranie wszystkich tickerów z oficjalnych arkuszy GPW i NewConnect.
2. Zbadanie 60-dniowego średniego obrotu dla każdego tickera.
3. Pobranie pełnej historii od 2015 r. TYLKO dla spółek spełniających próg min. 100 000 PLN
   i zapisanie ich na dysku do plików Parquet (katalog cache_data/).
"""

import os
import re
import sys
import io
import urllib.request
from datetime import datetime, timedelta, date
import pandas as pd
import yfinance as yf

CACHE_DIR = "cache_data"
os.makedirs(CACHE_DIR, exist_ok=True)


def get_latest_trading_date_str(days_back=0) -> str:
    """Zwraca datę ostatniej sesji giełdowej w formacie YYYY-MM-DD."""
    dt = date.today() - timedelta(days=days_back)
    # Jeśli weekend, cofnij do piątku
    if dt.weekday() == 5: # sobota
        dt -= timedelta(days=1)
    elif dt.weekday() == 6: # niedziela
        dt -= timedelta(days=2)
    return dt.strftime("%Y-%m-%d")


def download_official_gpw_nc_tickers(max_lookback_days=5):
    """
    Pobiera oficjalną listę spółek z plików notowań ciągłych GPW i NewConnect.
    Zwraca słownik: { 'TICKER.WA': {'name': '...', 'market': 'GPW'|'NewConnect'} }
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "*/*"
    }

    discovered_tickers = {}

    for market, base_url_pattern in [
        ('GPW', "https://www.gpw.pl/pub/GPW/files/quotations_xls/PL/akcje-i-pda/notowania-ciagle/{date_str}.xls"),
        ('NewConnect', "https://newconnect.pl/pub/NEWCONNECT/files/quotations_xls/PL/notowania-ciagle/{date_str}.xls")
    ]:
        print(f"[{market}] Próba pobrania oficjalnego arkusza spółek...")
        success = False

        for offset in range(max_lookback_days):
            date_candidate = get_latest_trading_date_str(offset)
            url = base_url_pattern.format(date_str=date_candidate)

            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=10) as response:
                    content = response.read()
                    if len(content) > 1000:
                        # Pliki xls z GPW to w rzeczywistości tabele HTML / XML Excel
                        try:
                            # Próba parsowania jako HTML table przez pandas
                            tables = pd.read_html(io.BytesIO(content))
                            if tables:
                                df = tables[0]
                                # Szukamy kolumny z tickerem / skrótem / kodem ISIN
                                ticker_col = None
                                name_col = None
                                for col in df.columns:
                                    col_str = str(col).lower()
                                    if any(k in col_str for k in ['kod', 'ticker', 'skrót', 'walor']):
                                        ticker_col = col
                                    if any(k in col_str for k in ['nazwa', 'spółka', 'firma']):
                                        name_col = col

                                if ticker_col is not None:
                                    for _, row in df.iterrows():
                                        raw_ticker = str(row[ticker_col]).strip().upper()
                                        raw_name = str(row[name_col]).strip() if name_col else raw_ticker
                                        # Pomijamy nagłówki i puste wiersze
                                        if re.match(r'^[A-Z0-9]{3,5}$', raw_ticker):
                                            wa_sym = f"{raw_ticker}.WA"
                                            discovered_tickers[wa_sym] = {
                                                "name": raw_name,
                                                "market": market
                                            }
                                    print(f"[{market}] ✅ Pomyślnie wczytano z pliku sesji {date_candidate}: {len(discovered_tickers)} spółek.")
                                    success = True
                                    break
                        except Exception:
                            # Fallback regex na kod HTML
                            html_text = content.decode('utf-8', errors='ignore')
                            found = re.findall(r'<td>([A-Z0-9]{3,5})</td>', html_text)
                            if found:
                                for t in found:
                                    discovered_tickers[f"{t}.WA"] = {"name": t, "market": market}
                                print(f"[{market}] ✅ Wyciągnięto {len(found)} tickerów regexem z arkusza {date_candidate}.")
                                success = True
                                break

            except Exception:
                continue

        if not success:
            print(f"[{market}] ⚠️ Nie udało się pobrać pliku XLS z ostatnich {max_lookback_days} dni. Użyty zostanie wbudowany rejestr.")

    return discovered_tickers


def sync_database_with_liquidity_filter(min_turnover_pln: float = 100000.0,
                                        turnover_days: int = 60,
                                        start_history_date: str = "2015-01-01",
                                        progress_callback=None):
    """
    Główna procedura synchronizacji:
    1. Pobiera listę tickerów z oficjalnych plików GPW i NC (oraz z pliku lokalnego gpw_tickers.py).
    2. Dla każdego tickera pobiera lekki wycinek ostatnich 90 dni i bada 60-dniowy średni obrót.
    3. TYLKO dla spółek ze średnim obrotem >= min_turnover_pln pobiera pełną historię od 2015 r.
       i zapisuje na dysk do formatu Parquet.
    """
    try:
        from gpw_tickers import GPW_TICKERS
    except ImportError:
        GPW_TICKERS = {
            "PKN.WA": {"name": "Orlen", "index": "WIG20", "sector": "Paliwa i Energetyka"},
            "PKO.WA": {"name": "PKO Bank Polski", "index": "WIG20", "sector": "Bankowość"},
            "PEO.WA": {"name": "Bank Pekao", "index": "WIG20", "sector": "Bankowość"},
            "KGH.WA": {"name": "KGHM Polska Miedź", "index": "WIG20", "sector": "Górnictwo"},
            "CDR.WA": {"name": "CD Projekt", "index": "WIG20", "sector": "Gry Wideo"},
            "DNP.WA": {"name": "Dino Polska", "index": "WIG20", "sector": "Handel Detaliczny"},
            "ALE.WA": {"name": "Allegro.eu", "index": "WIG20", "sector": "E-commerce"},
            "PZU.WA": {"name": "PZU", "index": "WIG20", "sector": "Ubezpieczenia"},
            "LPP.WA": {"name": "LPP", "index": "WIG20", "sector": "Odzież i Obuwie"},
            "SPL.WA": {"name": "Santander Bank Polska", "index": "WIG20", "sector": "Bankowość"},
            "MBK.WA": {"name": "mBank", "index": "WIG20", "sector": "Bankowość"},
            "KRU.WA": {"name": "Kruk", "index": "WIG20", "sector": "Finanse / Windykacja"},
            "KTY.WA": {"name": "Grupa Kęty", "index": "WIG20", "sector": "Przemysł Aluminiowy"},
            "JSW.WA": {"name": "Jastrzębska Spółka Węglowa", "index": "WIG20", "sector": "Górnictwo"},
            "PGE.WA": {"name": "PGE Polska Grupa Energetyczna", "index": "WIG20", "sector": "Energetyka"},
            "TPE.WA": {"name": "Tauron PE", "index": "WIG20", "sector": "Energetyka"},
            "OPL.WA": {"name": "Orange Polska", "index": "WIG20", "sector": "Telekomunikacja"},
            "CPS.WA": {"name": "Cyfrowy Polsat", "index": "WIG20", "sector": "Media"},
            "BFT.WA": {"name": "Benefit Systems", "index": "WIG20", "sector": "Rekreacja"},
            "BDX.WA": {"name": "Budimex", "index": "WIG20", "sector": "Budownictwo"}
        }

    print(f"Rozpoczynanie synchronizacji bazy danych GPW & NewConnect...")
    print(f"Filtr minimalnego średniego obrotu: {min_turnover_pln:,.0f} PLN ({turnover_days} sesji)")

    # 1. Pobieramy oficjalne tickery z GPW i NC
    official_dict = download_official_gpw_nc_tickers()

    # Łączymy z naszą bazą bazową (jako pewny backup)
    all_tickers_map = {**GPW_TICKERS, **official_dict}
    tickers_list = sorted(list(all_tickers_map.keys()))
    total_count = len(tickers_list)

    print(f"Łącznie do weryfikacji płynności: {total_count} tickerów.")

    liquid_qualified = []
    rejected_count = 0

    # 2. Etap 1: Weryfikacja obrotu z ostatnich sesji
    for idx, sym in enumerate(tickers_list):
        if progress_callback:
            progress_callback(idx + 1, total_count, f"Badanie płynności {sym} ({idx+1}/{total_count})...")

        try:
            # Pobieramy tylko 4 miesiące danych do szybkiego testu płynności
            short_df = yf.download(sym, period="4mo", progress=False, auto_adjust=False)
            if short_df.empty or len(short_df) < turnover_days:
                rejected_count += 1
                continue

            if isinstance(short_df.columns, pd.MultiIndex):
                short_df.columns = short_df.columns.get_level_values(0)

            turnover_series = short_df["Close"] * short_df["Volume"]
            avg_turnover = float(turnover_series.tail(turnover_days).mean())

            if avg_turnover >= min_turnover_pln:
                liquid_qualified.append((sym, avg_turnover))
                print(f"  [+] {sym}: Śr. obrót = {avg_turnover:,.0f} PLN >= {min_turnover_pln:,.0f} PLN -> KWALIFIKACJA!")
            else:
                rejected_count += 1
        except Exception:
            rejected_count += 1

    print(f"\nEtap 1 zakończony: {len(liquid_qualified)} spółek spełnia warunek obrotu ({rejected_count} odrzucono).")

    # 3. Etap 2: Pobieranie pełnej historii od 2015 r. TYLKO dla zakwalifikowanych spółek
    saved_files = []
    for idx, (sym, avg_turn) in enumerate(liquid_qualified):
        if progress_callback:
            progress_callback(idx + 1, len(liquid_qualified), f"Pobieranie pełnej historii od 2015 dla {sym}...")

        print(f"[{idx+1}/{len(liquid_qualified)}] Pobieranie pełnych notowań od {start_history_date} dla {sym}...")
        try:
            full_df = yf.download(sym, start=start_history_date, progress=False, auto_adjust=False)
            if not full_df.empty:
                if isinstance(full_df.columns, pd.MultiIndex):
                    full_df.columns = full_df.columns.get_level_values(0)

                full_df = full_df.rename(columns={
                    "Open": "Open", "High": "High", "Low": "Low", "Close": "Close", "Volume": "Volume"
                }).dropna(subset=["Close", "High", "Low", "Volume"])

                cache_path = os.path.join(CACHE_DIR, f"{sym.replace('.', '_')}.parquet")
                full_df.to_parquet(cache_path)
                saved_files.append((sym, cache_path, len(full_df)))
        except Exception as e:
            print(f"Błąd zapisu {sym}: {e}")

    print(f"\n✅ Synchronizacja zakończona sukcesem!")
    print(f"Zapisano na dysku {len(saved_files)} plików Parquet w katalogu '{CACHE_DIR}/'.")
    print(f"Kolejne symulacje backtestów nie będą wymagały pobierania danych z internetu!")
    return saved_files


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Synchronizacja i buforowanie danych GPW/NC")
    parser.add_argument("--min-turnover", type=float, default=100000.0, help="Min. obrót 60d w PLN")
    parser.add_argument("--turnover-days", type=int, default=60, help="Liczba sesji obrotu")
    parser.add_argument("--start-date", type=str, default="2015-01-01", help="Data początkowa (YYYY-MM-DD)")
    args = parser.parse_args()

    sync_database_with_liquidity_filter(
        min_turnover_pln=args.min_turnover,
        turnover_days=args.turnover_days,
        start_history_date=args.start_date
    )
