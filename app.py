"""
System Transakcyjny Żółwi (Turtle Trading System) dla GPW i NewConnect
Aplikacja Streamlit do zarządzania portfelem, automatycznego wykrywania trwających trendów,
skanowania wyłącznie świeżych wejść dla rynku oraz piramidowania/sprzedaży dla portfela.
"""

import os
import json
from datetime import datetime, date
import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots

try:
    from gpw_tickers import GPW_TICKERS, get_ticker_list, get_ticker_info
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
        "BDX.WA": {"name": "Budimex", "index": "WIG20", "sector": "Budownictwo"},
        "ACP.WA": {"name": "Asseco Poland", "index": "mWIG40", "sector": "IT"},
        "MIL.WA": {"name": "Bank Millennium", "index": "mWIG40", "sector": "Bankowość"},
        "ING.WA": {"name": "ING Bank Śląski", "index": "mWIG40", "sector": "Bankowość"},
        "XTB.WA": {"name": "XTB", "index": "mWIG40", "sector": "Finanse / Broker"},
        "CCC.WA": {"name": "CCC", "index": "mWIG40", "sector": "Obuwie / Retail"},
        "ENA.WA": {"name": "Enea", "index": "mWIG40", "sector": "Energetyka"},
        "TEN.WA": {"name": "Ten Square Games", "index": "mWIG40", "sector": "Gry Wideo"},
        "11B.WA": {"name": "11 bit studios", "index": "mWIG40", "sector": "Gry Wideo"},
        "CAR.WA": {"name": "Inter Cars", "index": "mWIG40", "sector": "Motoryzacja"},
        "DOM.WA": {"name": "Dom Development", "index": "mWIG40", "sector": "Deweloperzy"},
        "ATD.WA": {"name": "Autopartner", "index": "mWIG40", "sector": "Motoryzacja"},
        "NEU.WA": {"name": "Neuca", "index": "mWIG40", "sector": "Farmacja"},
        "TXT.WA": {"name": "Text (LiveChat)", "index": "mWIG40", "sector": "IT / SaaS"},
        "ALR.WA": {"name": "Alior Bank", "index": "mWIG40", "sector": "Bankowość"},
        "GPW.WA": {"name": "GPW", "index": "mWIG40", "sector": "Finanse"},
        "UNT.WA": {"name": "Unimot", "index": "sWIG80", "sector": "Paliwa i Gaz"},
        "TOR.WA": {"name": "Torpol", "index": "sWIG80", "sector": "Infrastruktura"},
        "VEE.WA": {"name": "Vee", "index": "NewConnect", "sector": "Voice AI"},
        "SFD.WA": {"name": "SFD", "index": "NewConnect", "sector": "Suplementy"},
        "BLO.WA": {"name": "Bloober Team", "index": "GPW/NC", "sector": "Gry Wideo"},
        "PLW.WA": {"name": "PlayWay", "index": "GPW/NC", "sector": "Gry Wideo"}
    }

    def get_ticker_list(universe: str = "ALL"):
        return sorted(list(GPW_TICKERS.keys()))

    def get_ticker_info(symbol: str):
        return GPW_TICKERS.get(symbol, {"name": symbol.replace(".WA", ""), "index": "GPW", "sector": "Inne"})

# ==========================================
# KONFIGURACJA STRONY STREAMLIT
# ==========================================
st.set_page_config(
    page_title="GPW Turtle Trading System",
    page_icon="🐢",
    layout="wide",
    initial_sidebar_state="expanded",
)

def safe_rerun():
    if hasattr(st, "rerun"):
        st.rerun()
    elif hasattr(st, "experimental_rerun"):
        st.experimental_rerun()

st.markdown("""
<style>
    .metric-card {
        background-color: #1e293b;
        border-radius: 8px;
        padding: 16px;
        color: white;
        border: 1px solid #334155;
    }
</style>
""", unsafe_allow_html=True)

CACHE_DIR = "cache_data"
os.makedirs(CACHE_DIR, exist_ok=True)

PORTFOLIO_FILE = os.path.join(CACHE_DIR, "user_portfolio.json")
HISTORY_FILE = os.path.join(CACHE_DIR, "portfolio_history.json")

def get_cache_decorator():
    if hasattr(st, "cache_data"):
        return st.cache_data(ttl=3600 * 6, show_spinner=False)
    elif hasattr(st, "experimental_memo"):
        return st.experimental_memo(ttl=3600 * 6)
    else:
        def noop(f):
            return f
        return noop

# ==========================================
# ZARZĄDZANIE TRWAŁYM PORTFELEM (JSON)
# ==========================================
def load_portfolio():
    if os.path.exists(PORTFOLIO_FILE):
        try:
            with open(PORTFOLIO_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_portfolio(positions):
    try:
        with open(PORTFOLIO_FILE, "w", encoding="utf-8") as f:
            json.dump(positions, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def load_closed_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_closed_history(history):
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# ==========================================
# FUNKCJE POBIERANIA I CACHOWANIA DANYCH
# ==========================================
@get_cache_decorator()
def fetch_ticker_data(symbol: str, start_date: str = "2015-01-01") -> pd.DataFrame:
    cache_file = os.path.join(CACHE_DIR, f"{symbol.replace('.', '_')}.parquet")
    if os.path.exists(cache_file):
        try:
            df = pd.read_parquet(cache_file)
            if not df.empty:
                return df
        except Exception:
            pass

    try:
        df = yf.download(symbol, start=start_date, progress=False, auto_adjust=False)
        if df.empty:
            return pd.DataFrame()

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df = df.rename(columns={
            "Open": "Open", "High": "High", "Low": "Low", "Close": "Close", "Volume": "Volume"
        })
        df = df.dropna(subset=["Close", "High", "Low", "Volume"])
        df = df[df["Volume"] >= 0]
        
        try:
            df.to_parquet(cache_file)
        except Exception:
            pass

        return df
    except Exception:
        return pd.DataFrame()


# ==========================================
# MATEMATYKA STRATEGII ŻÓŁWI (TURTLE)
# ==========================================
def calculate_indicators(df: pd.DataFrame, entry_period: int = 20, exit_period: int = 10, atr_period: int = 20):
    data = df.copy()
    prev_close = data["Close"].shift(1)
    hl = data["High"] - data["Low"]
    hc = (data["High"] - prev_close).abs()
    lc = (data["Low"] - prev_close).abs()
    data["TR"] = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    data["ATR"] = data["TR"].rolling(window=atr_period, min_periods=1).mean()
    data["Donchian_High"] = data["High"].shift(1).rolling(window=entry_period).max()
    data["Donchian_Low"] = data["Low"].shift(1).rolling(window=exit_period).min()
    data["Daily_Turnover"] = data["Close"] * data["Volume"]
    return data


def calculate_turtle_unit_size(capital: float, risk_pct: float, atr: float, price: float) -> int:
    """
    Tradycyjny model kalkulacji jednostki Żółwi (Classic Turtle Unit Size):
    Cash at risk = Kapitał * (RiskPct / 100) (zazwyczaj 1% kapitału portfela)
    Zmienność na akcję N = ATR
    Unit Size = floor(Cash at risk / ATR)
    """
    if atr <= 0 or price <= 0 or capital <= 0:
        return 0
    cash_at_risk = capital * (risk_pct / 100.0)
    raw_units = int(np.floor(cash_at_risk / atr))
    max_affordable = int(np.floor(capital / price))
    return max(0, min(raw_units, max_affordable))


def find_active_turtle_trends(tickers, entry_period=20, exit_period=10, atr_period=20, min_turnover=100000, turnover_days=60, progress_cb=None):
    """
    Sprawdza, które spółki wybiły górny kanał Donchiana (20d) i od tamtej pory NIE wybiły dołka (10d) ani Stop Lossa (2xN).
    Wejście następuje kolejnego dnia po cenie otwarcia (Open T+1).
    Zwraca listę pozycji, które zgodnie z regułami Żółwi POWINNY ZNAJDOWAĆ SIĘ DZIŚ W PORTFELU.
    """
    active_trends = []
    total = len(tickers)
    for idx, sym in enumerate(tickers):
        if progress_cb:
            progress_cb(idx + 1, total, f"Badanie trendu {sym} ({idx+1}/{total})...")
        df = fetch_ticker_data(sym, start_date="2023-01-01")
        if df.empty or len(df) < max(entry_period, exit_period, turnover_days) + 10:
            continue
        recent_turnover = (df["Close"] * df["Volume"]).tail(turnover_days).mean()
        if recent_turnover < min_turnover:
            continue
        calc = calculate_indicators(df, entry_period=entry_period, exit_period=exit_period, atr_period=atr_period)
        if len(calc) < 30:
            continue
        
        # Analiza ostatnich 120 sesji chronologicznie
        sub = calc.tail(120)
        in_pos = False
        pos_entry_date = None
        pos_entry_price = 0.0
        pos_last_price = 0.0
        pos_atr = 0.0
        pos_stop = 0.0
        pos_units = 1
        pending_breakout = False
        pending_signal_close = 0.0
        pending_signal_atr = 0.0
        
        for i in range(1, len(sub)):
            row = sub.iloc[i]
            prev_row = sub.iloc[i-1]
            open_p = float(row["Open"])
            close = float(row["Close"])
            low = float(row["Low"])
            atr = float(row["ATR"])
            donch_high = float(row["Donchian_High"])
            prev_donch_high = float(prev_row["Donchian_High"])
            donch_low = float(row["Donchian_Low"])
            
            # Realizacja wejścia na otwarciu sesji po wczorajszym wybiciu
            if pending_breakout and not in_pos:
                in_pos = True
                pos_entry_date = row.name if hasattr(row, "name") else str(i)
                pos_entry_price = open_p  # Wejście po cenie otwarcia kolejnego dnia (Open T+1)
                pos_last_price = open_p
                pos_atr = pending_signal_atr
                pos_stop = round(pending_signal_close - 2.0 * pending_signal_atr, 2)
                pos_units = 1
                pending_breakout = False

            if in_pos:
                if (pos_stop > 0 and low <= pos_stop) or (donch_low > 0 and close < donch_low):
                    in_pos = False
                else:
                    # Piramidowanie: +0.5 N
                    if pos_units < 4 and close >= pos_last_price + 0.5 * pos_atr and pos_atr > 0:
                        pos_units += 1
                        pos_last_price = close
                        pos_stop = round(close - 2.0 * pos_atr, 2)
            else:
                # Świeże wejście (zamknięcie dzisiaj ponad kanałem, a wczoraj poniżej -> wejście jutro na Open)
                if not np.isnan(donch_high) and close > donch_high and (np.isnan(prev_donch_high) or float(prev_row["Close"]) <= prev_donch_high):
                    pending_breakout = True
                    pending_signal_close = close
                    pending_signal_atr = atr
                    
        if in_pos:
            last_close = float(calc.iloc[-1]["Close"])
            gain_pct = ((last_close - pos_entry_price) / pos_entry_price) * 100.0 if pos_entry_price > 0 else 0.0
            info = get_ticker_info(sym)
            active_trends.append({
                "symbol": sym,
                "name": info["name"],
                "index": info["index"],
                "sector": info["sector"],
                "entry_date": str(pos_entry_date)[:10],
                "entry_price": round(pos_entry_price, 2),
                "last_entry_price": round(pos_last_price, 2),
                "current_price": round(last_close, 2),
                "gain_pct": round(gain_pct, 2),
                "units": pos_units,
                "entry_atr": round(pos_atr, 2),
                "stop_loss": pos_stop,
                "avg_turnover": round(recent_turnover, 0)
            })
    return active_trends


def run_portfolio_turtle_backtest(data_dict: dict, initial_capital: float, risk_pct: float,
                                 entry_period: int, exit_period: int, atr_period: int,
                                 commission_pct: float, min_turnover: float, turnover_days: int,
                                 max_positions: int = 8):
    if not data_dict:
        return None

    all_dates = sorted(list(set().union(*[df.index.tolist() for df in data_dict.values()])))
    if len(all_dates) < max(entry_period, exit_period, turnover_days) + 10:
        return None

    cash = initial_capital
    open_positions = {}
    pending_entries = []  # Zlecenia oczekujące na otwarcie kolejnej sesji (Open T+1)
    trades = []
    equity_curve = []
    peak_equity = initial_capital
    max_dd = 0.0

    base_prices = {sym: df["Close"].iloc[0] for sym, df in data_dict.items() if not df.empty and df["Close"].iloc[0] > 0}

    for current_date in all_dates:
        # 1. Realizacja zleceń kupna na OTWARCIU sesji (Open T+1) po wcześniejszym sygnale wybicia
        if pending_entries:
            for pending in pending_entries:
                sym = pending["symbol"]
                if sym in open_positions or len(open_positions) >= max_positions:
                    continue
                df = data_dict.get(sym)
                if df is None or current_date not in df.index:
                    continue
                row = df.loc[current_date]
                open_p = float(row["Open"])
                comm_rate = commission_pct / 100.0
                max_afford = int(np.floor(cash / (open_p * (1.0 + comm_rate))))
                final_shares = min(pending["shares"], max_afford)
                if final_shares > 0:
                    trade_cost = final_shares * open_p
                    comm = trade_cost * comm_rate
                    total_cost = trade_cost + comm
                    if cash >= total_cost:
                        cash -= total_cost
                        open_positions[sym] = {
                            "shares": final_shares,
                            "avg_price": open_p,
                            "last_entry_price": open_p,
                            "total_cost": total_cost,
                            "units": 1,
                            "atr": pending["atr"],
                            "entry_date": current_date,
                            "stop_loss": pending["stop_loss"]
                        }
            pending_entries = []

        # 2. Wyjścia z pozycji
        for sym in list(open_positions.keys()):
            pos = open_positions[sym]
            df = data_dict.get(sym)
            if df is None or current_date not in df.index:
                continue

            row = df.loc[current_date]
            close = float(row["Close"])
            low = float(row["Low"])
            open_p = float(row["Open"])
            donch_low = float(row["Donchian_Low"]) if "Donchian_Low" in row and not np.isnan(row["Donchian_Low"]) else -1

            exit_triggered = False
            exit_reason = ""
            actual_exit = close

            if pos["stop_loss"] > 0 and low <= pos["stop_loss"]:
                exit_triggered = True
                actual_exit = min(open_p, pos["stop_loss"])
                exit_reason = "Stop Loss (2x N)"
            elif donch_low > 0 and close < donch_low:
                exit_triggered = True
                actual_exit = close
                exit_reason = f"Wybicie dołka ({exit_period}d)"
            elif current_date == all_dates[-1]:
                exit_triggered = True
                actual_exit = close
                exit_reason = "Koniec Okresu Testu"

            if exit_triggered:
                gross_rev = pos["shares"] * actual_exit
                comm = gross_rev * (commission_pct / 100.0)
                net_rev = gross_rev - comm
                cost = pos["total_cost"]
                pnl = net_rev - cost
                pnl_pct = (pnl / cost) * 100.0 if cost > 0 else 0.0

                trades.append({
                    "Symbol": sym,
                    "Data Wejścia": pos["entry_date"].strftime("%Y-%m-%d") if hasattr(pos["entry_date"], "strftime") else str(pos["entry_date"])[:10],
                    "Cena Średnia": round(pos["avg_price"], 2),
                    "Data Wyjścia": current_date.strftime("%Y-%m-%d") if hasattr(current_date, "strftime") else str(current_date)[:10],
                    "Cena Wyjścia": round(actual_exit, 2),
                    "Liczba Akcji": pos["shares"],
                    "Jednostki (Units)": pos["units"],
                    "Wynik (PLN)": round(pnl, 2),
                    "Wynik (%)": round(pnl_pct, 2),
                    "Powód Wyjścia": exit_reason
                })

                cash += net_rev
                del open_positions[sym]

        curr_holdings_val = sum(
            pos["shares"] * float(data_dict[sym].loc[current_date]["Close"])
            for sym, pos in open_positions.items()
            if current_date in data_dict[sym].index
        )
        current_equity = cash + curr_holdings_val

        # 3. Piramidowanie: +0.5 N
        if current_date != all_dates[-1]:
            for sym, pos in list(open_positions.items()):
                if pos["units"] >= 4:
                    continue
                df = data_dict.get(sym)
                if df is None or current_date not in df.index:
                    continue
                close = float(df.loc[current_date]["Close"])
                atr = pos["atr"]
                pyramid_trigger = pos["last_entry_price"] + 0.5 * atr

                if close >= pyramid_trigger and atr > 0:
                    new_stop = round(close - (2.0 * atr), 2)
                    add_units = calculate_turtle_unit_size(current_equity, risk_pct, atr, close)
                    afford = int(np.floor(cash / (close * (1 + commission_pct / 100.0))))
                    add_units = max(0, min(add_units, afford))

                    if add_units > 0:
                        add_cost = add_units * close * (1 + commission_pct / 100.0)
                        if cash >= add_cost:
                            cash -= add_cost
                            new_total_shares = pos["shares"] + add_units
                            new_total_cost = pos["total_cost"] + add_cost
                            pos["shares"] = new_total_shares
                            pos["total_cost"] = new_total_cost
                            pos["avg_price"] = new_total_cost / new_total_shares
                            pos["last_entry_price"] = close
                            pos["units"] += 1
                            pos["stop_loss"] = new_stop

        # 4. Skanowanie świeżych wybić po zamknięciu (do zakupu na otwarciu jutro)
        available_slots = max_positions - len(open_positions) - len(pending_entries)
        if available_slots > 0 and current_date != all_dates[-1]:
            for sym, df in data_dict.items():
                if sym in open_positions or any(p["symbol"] == sym for p in pending_entries):
                    continue
                if len(pending_entries) >= available_slots:
                    break
                if current_date not in df.index:
                    continue

                sub_history = df.loc[:current_date]
                if len(sub_history) < turnover_days or len(sub_history) < 2:
                    continue
                rolling_turnover = sub_history["Daily_Turnover"].tail(turnover_days).mean()
                if rolling_turnover < min_turnover:
                    continue

                today_row = sub_history.iloc[-1]
                prev_row = sub_history.iloc[-2]

                close = float(today_row["Close"])
                prev_close = float(prev_row["Close"])
                atr = float(today_row["ATR"])
                donch_high = float(today_row["Donchian_High"])
                prev_donch_high = float(prev_row["Donchian_High"])

                fresh_breakout = (not np.isnan(donch_high) and close > donch_high and
                                  (np.isnan(prev_donch_high) or prev_close <= prev_donch_high))

                if fresh_breakout and atr > 0:
                    calculated_stop = round(close - 2.0 * atr, 2)
                    raw_units = calculate_turtle_unit_size(current_equity, risk_pct, atr, close)
                    max_cap_units = int(np.floor((current_equity * 0.25) / close))
                    final_units = min(raw_units, max_cap_units)

                    if final_units > 0:
                        pending_entries.append({
                            "symbol": sym,
                            "shares": final_units,
                            "stop_loss": calculated_stop,
                            "atr": atr,
                            "signal_date": current_date,
                            "signal_close": close
                        })

        final_holdings = sum(
            pos["shares"] * float(data_dict[sym].loc[current_date]["Close"])
            for sym, pos in open_positions.items()
            if current_date in data_dict[sym].index
        )
        port_val = cash + final_holdings
        if port_val > peak_equity:
            peak_equity = port_val
        curr_dd = ((port_val - peak_equity) / peak_equity) * 100.0 if peak_equity > 0 else 0.0
        if curr_dd < max_dd:
            max_dd = curr_dd

        bench_ratios = [
            float(data_dict[sym].loc[current_date]["Close"]) / base_prices[sym]
            for sym in data_dict.keys()
            if current_date in data_dict[sym].index and sym in base_prices
        ]
        bench_val = (np.mean(bench_ratios) if bench_ratios else 1.0) * initial_capital

        equity_curve.append({
            "Date": current_date,
            "Equity": port_val,
            "Cash": cash,
            "Holdings": final_holdings,
            "Active_Positions": len(open_positions),
            "Benchmark": bench_val,
            "Drawdown": curr_dd
        })

    eq_df = pd.DataFrame(equity_curve)
    if eq_df.empty:
        return None

    final_eq = eq_df["Equity"].iloc[-1]
    total_ret = ((final_eq - initial_capital) / initial_capital) * 100.0

    eq_df["Daily_Ret"] = eq_df["Equity"].pct_change().fillna(0)
    sharpe = 0.0
    if eq_df["Daily_Ret"].std() > 0:
        sharpe = (eq_df["Daily_Ret"].mean() * 252 - 0.03) / (eq_df["Daily_Ret"].std() * np.sqrt(252))

    trades_df = pd.DataFrame(trades)
    win_rate = 0.0
    profit_factor = 0.0
    if not trades_df.empty:
        wins = trades_df[trades_df["Wynik (PLN)"] > 0]
        losses = trades_df[trades_df["Wynik (PLN)"] < 0]
        win_rate = (len(wins) / len(trades_df)) * 100.0
        gross_p = wins["Wynik (PLN)"].sum()
        gross_l = abs(losses["Wynik (PLN)"].sum())
        profit_factor = gross_p / gross_l if gross_l > 0 else (99.0 if gross_p > 0 else 0.0)

    sym_stats = []
    if not trades_df.empty:
        for sym, grp in trades_df.groupby("Symbol"):
            w = len(grp[grp["Wynik (PLN)"] > 0])
            sym_stats.append({
                "Symbol": sym,
                "Nazwa": GPW_TICKERS.get(sym, {}).get("name", sym),
                "Liczba Transakcji": len(grp),
                "Win Rate (%)": round((w / len(grp)) * 100.0, 1),
                "Łączny Zysk (PLN)": round(grp["Wynik (PLN)"].sum(), 2),
                "Średni Zwrot (%)": round(grp["Wynik (%)"].mean(), 2)
            })
        sym_stats = pd.DataFrame(sym_stats).sort_values("Łączny Zysk (PLN)", ascending=False)
    else:
        sym_stats = pd.DataFrame()

    return {
        "final_equity": final_eq,
        "total_return_pct": total_ret,
        "max_drawdown_pct": max_dd,
        "sharpe_ratio": sharpe,
        "total_trades": len(trades_df),
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "trades_df": trades_df,
        "equity_df": eq_df,
        "symbol_stats_df": sym_stats
    }


# ==========================================
# PANEL BOCZNY (SIDEBAR) - KONFIGURACJA
# ==========================================
st.sidebar.title("🐢 Turtle System GPW")
st.sidebar.markdown("**Zarządzanie Strategią i Filtrami**")

strategy_mode = st.sidebar.radio(
    "Wariant Strategii:",
    options=["Klasyczna (System 1)", "Własna (Edytowalna)"],
    index=0
)

if strategy_mode == "Klasyczna (System 1)":
    st.sidebar.info("💡 **System 1 (Klasyczny):**\n- Świeże Wejście: Wybicie 20-dniowe\n- Dokupienie: +0.5 N (maks. 4 jednostki)\n- Wyjście: Wybicie dołka 10-dniowego\n- ATR: 20 dni | Ryzyko: 1.0%")
    entry_days, exit_days, atr_days, risk_pct = 20, 10, 20, 1.0
else:
    st.sidebar.subheader("⚙️ Parametry Własne")
    entry_days = st.sidebar.number_input("Długość wejścia (Donchian High)", 5, 120, 20, 5)
    exit_days = st.sidebar.number_input("Długość wyjścia (Donchian Low)", 3, 60, 10, 1)
    atr_days = st.sidebar.number_input("Okres wskaźnika ATR (N)", 5, 60, 20, 1)
    risk_pct = st.sidebar.slider("Ryzyko na transakcję (% kapitału)", 0.25, 5.0, 1.0, 0.25)

st.sidebar.markdown("---")
st.sidebar.subheader("💧 Filtr Płynności i Obrotu")
min_turnover = st.sidebar.number_input("Minimalny średni obrót dzienny (PLN)", 10000, 5000000, 100000, 25000)
turnover_window = st.sidebar.number_input("Okres badania obrotu (dni/sesje)", 10, 250, 60, 5)

st.sidebar.markdown("---")
st.sidebar.subheader("💰 Kapitał i Prowizje")
initial_cap = st.sidebar.number_input("Kapitał portfela (PLN)", 5000, 10000000, 100000, 10000)
max_simul_pos = st.sidebar.slider("Maks. jednoczesnych pozycji w portfelu", 2, 20, 8, 1)
commission = st.sidebar.number_input("Prowizja maklerska (%)", 0.0, 1.5, 0.29, 0.05)

st.sidebar.markdown("---")
st.sidebar.subheader("💾 Baza Danych na Dysku (Parquet)")
cached_files = [f for f in os.listdir(CACHE_DIR) if f.endswith(".parquet")] if os.path.exists(CACHE_DIR) else []
st.sidebar.caption(f"Liczba spółek zapisanych na dysku: **{len(cached_files)}**")

if st.sidebar.button("🔄 Pobierz z oficjalnych arkuszy GPW/NC"):
    try:
        from sync_gpw_data import sync_database_with_liquidity_filter
        with st.spinner("Pobieranie arkuszy GPW/NC, filtr 60d obrotu i pobieranie danych od 2015 r..."):
            prog = st.sidebar.progress(0, text="Synchronizacja...")
            def p_cb(cur, tot, msg):
                prog.progress(cur / tot, text=msg)
            saved = sync_database_with_liquidity_filter(
                min_turnover_pln=min_turnover,
                turnover_days=turnover_window,
                progress_callback=p_cb
            )
            prog.empty()
            st.sidebar.success(f"Zapisano {len(saved)} płynnych spółek na dysku!")
    except ImportError:
        st.sidebar.error("Plik `sync_gpw_data.py` nie został znaleziony w bieżącym katalogu.")
    except Exception as e:
        st.sidebar.error(f"Błąd synchronizacji: {e}")


# ==========================================
# GŁÓWNA STRUKTURA ZAKŁADEK (TABS)
# ==========================================
st.title("🐢 Turtle Trading GPW & NewConnect")
st.caption("Rozłączny System: Portfel (tylko dokupienie/sprzedaż) • Skaner (tylko świeże wejścia) • Audyt trwających trendów")

if "user_portfolio" not in st.session_state:
    st.session_state["user_portfolio"] = load_portfolio()

tab_portfolio, tab_scanner, tab_backtest, tab_database, tab_guide = st.tabs([
    "💼 Mój Portfel Żółwia (Tylko Dokupienie / Sprzedaż)",
    "🎯 Skaner Rynku (Tylko Świeże Wejścia)",
    "📈 Backtest Portfela GPW (Wszystkie Spółki Razem)",
    "💾 Baza Danych na Dysku (Parquet)",
    "📚 Kompendium i Opis Strategii"
])


# ==========================================
# ZAKŁADKA 1: MÓJ PORTFEL ŻÓŁWIA
# ==========================================
with tab_portfolio:
    st.subheader("💼 Mój Portfel Żółwia – Aktywne Pozycje")
    st.markdown("""
    **Ścisła reguła Żółwi:** Dla spółek, które już masz w portfelu, **nie sprawdzamy górnych wybić 20-dniowych**.
    Monitorujemy dla nich **WYŁĄCZNIE**:
    1. 🟢 **DOKUPIENIE (+1 Unit co +0.5 N)** – do limitu 4 jednostek, z podnoszeniem Stop Lossa.
    2. 🚨 **SPRZEDAŻ (Stop Loss 2xN)** – obrona kapitału.
    3. ⚠️ **SPRZEDAŻ (Wyjście 10-dniowe)** – realizacja zysku przy wybiciu dołka Donchiana.
    """)

    # -------------------------------------------------------------
    # SEKCJA: AUDYT STARTOWY (Które spółki już wybiły i powinny być w portfelu?)
    # -------------------------------------------------------------
    with st.expander("🔍 Audyt Rynku: Które spółki już wybiły i powinny być teraz w portfelu?", expanded=False):
        st.markdown("""
        To narzędzie analizuje historię ostatnich miesięcy na GPW i NewConnect i wskazuje spółki, które:
        - **Wybiły górny kanał Donchiana (20d)** w przeszłości,
        - **Do dnia dzisiejszego NIE wybiły dołka (10d) ani Stop Lossa (2xN)**.
        Możesz jednym kliknięciem załadować je jako swój aktualny portfel startowy!
        """)

        if st.button("🔎 Sprawdź rynek: Wykryj spółki będące aktualnie w trendzie", type="primary"):
            with st.spinner("Analiza trwających trendów na GPW i NC..."):
                prog = st.progress(0, text="Skanowanie...")
                def cb(c, t, m):
                    prog.progress(c / t, text=m)
                detected = find_active_turtle_trends(
                    tickers=get_ticker_list(),
                    entry_period=entry_days,
                    exit_period=exit_days,
                    atr_period=atr_days,
                    min_turnover=min_turnover,
                    turnover_days=turnover_window,
                    progress_cb=cb
                )
                prog.empty()
                st.session_state["detected_active_trends"] = detected

        detected_trends = st.session_state.get("detected_active_trends", [])
        if detected_trends:
            st.success(f"Znaleziono **{len(detected_trends)} spółek**, które wybiły wcześniej i nadal trzymają trend!")
            det_df = pd.DataFrame(detected_trends)
            display_det = det_df[[
                "symbol", "name", "entry_date", "entry_price", "current_price",
                "gain_pct", "units", "stop_loss", "entry_atr"
            ]].copy()
            display_det.columns = [
                "Symbol", "Nazwa", "Data Wybicia", "Cena Wejścia", "Kurs Dziś",
                "Wynik Trendu (%)", "Jednostki (Units)", "Stop Loss (2xN)", "ATR (N)"
            ]
            st.dataframe(display_det, use_container_width=True)

            if st.button(f"📥 Załaduj wykryte spółki ({len(detected_trends)}) jako mój portfel", type="secondary"):
                new_positions = []
                for dt in detected_trends:
                    # Obliczenie sugerowanej liczby akcji wg kapitału i ATR
                    u_size = calculate_turtle_unit_size(initial_cap, risk_pct, dt["entry_atr"], dt["entry_price"])
                    total_shares = max(10, u_size * dt["units"])
                    new_positions.append({
                        "symbol": dt["symbol"],
                        "name": dt["name"],
                        "entry_date": dt["entry_date"],
                        "shares": total_shares,
                        "units": dt["units"],
                        "avg_price": dt["entry_price"],
                        "last_entry_price": dt["last_entry_price"],
                        "entry_atr": dt["entry_atr"],
                        "stop_loss": dt["stop_loss"]
                    })
                save_portfolio(new_positions)
                st.session_state["user_portfolio"] = new_positions
                st.success("Pomyślnie załadowano spółki do Twojego portfela!")
                safe_rerun()

    positions = st.session_state.get("user_portfolio", [])
    enhanced_positions = []
    portfolio_alerts = []

    if positions:
        with st.spinner("Pobieranie notowań dla spółek w portfelu..."):
            for pos in positions:
                sym = pos["symbol"]
                df = fetch_ticker_data(sym, start_date="2023-01-01")
                if df.empty or len(df) < 5:
                    enhanced_positions.append({**pos, "current_price": pos["avg_price"], "pnl_pln": 0, "pnl_pct": 0, "status": "BRAK_DANYCH"})
                    continue

                calc_df = calculate_indicators(df, entry_period=entry_days, exit_period=exit_days, atr_period=atr_days)
                last_row = calc_df.iloc[-1]
                close = float(last_row["Close"])
                donch_low = float(last_row["Donchian_Low"])
                current_atr = float(last_row["ATR"])

                avg_price = float(pos.get("avg_price", pos.get("entry_price", close)))
                last_price = float(pos.get("last_entry_price", avg_price))
                shares = int(pos.get("shares", 0))
                units = int(pos.get("units", 1))
                entry_atr = float(pos.get("entry_atr", current_atr))
                stop_loss = float(pos.get("stop_loss", round(last_price - 2.0 * entry_atr, 2)))

                curr_val = shares * close
                cost_basis = shares * avg_price
                pnl_pln = curr_val - cost_basis
                pnl_pct = ((close - avg_price) / avg_price) * 100.0 if avg_price > 0 else 0.0

                next_pyramid_price = round(last_price + 0.5 * entry_atr, 2)

                status = "TRZYMAJ"
                action_badge = "🛡️ TRZYMAJ (W trendzie)"
                
                if close <= stop_loss:
                    status = "STOP_LOSS"
                    action_badge = "🚨 SPRZEDAJ (STOP LOSS 2xN!)"
                    portfolio_alerts.append({
                        "type": "error",
                        "symbol": sym,
                        "msg": f"**{sym}**: Kurs ({close:.2f} PLN) spadł poniżej Stop Lossa ({stop_loss:.2f} PLN). **ZAMKNIJ POZYCJĘ**, aby uciąć stratę!"
                    })
                elif close < donch_low:
                    status = "EXIT_DONCHIAN"
                    action_badge = "⚠️ SPRZEDAJ (WYJŚCIE 10d)"
                    portfolio_alerts.append({
                        "type": "warning",
                        "symbol": sym,
                        "msg": f"**{sym}**: Kurs ({close:.2f} PLN) wybił w dół 10-dniowe minimum ({donch_low:.2f} PLN). **ZREALIZUJ ZYSK / ZAMKNIJ POZYCJĘ**!"
                    })
                elif units < 4 and close >= next_pyramid_price:
                    status = "DOKUP"
                    action_badge = f"🟢 DOKUP (+1 UNIT #{units+1})"
                    suggested_add_units = calculate_turtle_unit_size(initial_cap, risk_pct, entry_atr, close)
                    portfolio_alerts.append({
                        "type": "success",
                        "symbol": sym,
                        "msg": f"**{sym}**: Kurs ({close:.2f} PLN) przekroczył poziom dokupienia {next_pyramid_price:.2f} PLN. **DOKUP JEDNOSTKĘ #{units+1}** (sugerowane: {suggested_add_units} akcji). Nowy Stop Loss: {round(close - 2*entry_atr, 2):.2f} PLN."
                    })

                enhanced_positions.append({
                    **pos,
                    "name": pos.get("name", get_ticker_info(sym)["name"]),
                    "current_price": close,
                    "current_val": curr_val,
                    "pnl_pln": pnl_pln,
                    "pnl_pct": pnl_pct,
                    "stop_loss": stop_loss,
                    "next_pyramid_price": next_pyramid_price if units < 4 else "-",
                    "donch_low": donch_low,
                    "current_atr": current_atr,
                    "status": status,
                    "action_badge": action_badge
                })

    if portfolio_alerts:
        st.subheader("🔔 Pilne Alerty Operacyjne dla Portfela:")
        for al in portfolio_alerts:
            if al["type"] == "error":
                st.error(al["msg"])
            elif al["type"] == "warning":
                st.warning(al["msg"])
            else:
                st.success(al["msg"])
    else:
        if positions:
            st.info("✅ Brak pilnych działań: Wszystkie otwarte pozycje rozwijają się w trendzie. Żadna nie osiągnęła poziomu Stop Loss ani sygnału wyjścia.")

    if enhanced_positions:
        total_port_val = sum(p["current_val"] for p in enhanced_positions)
        total_pnl_pln = sum(p["pnl_pln"] for p in enhanced_positions)
        total_cost = sum(p["shares"] * float(p["avg_price"]) for p in enhanced_positions)
        total_pnl_pct = (total_pnl_pln / total_cost) * 100.0 if total_cost > 0 else 0.0

        kp1, kp2, kp3, kp4 = st.columns(4)
        kp1.metric("Wycena Akcji w Portfelu", f"{total_port_val:,.2f} PLN")
        kp2.metric("Łączny Wynik Portfela", f"{total_pnl_pln:+,.2f} PLN", delta=f"{total_pnl_pct:+.2f}%")
        kp3.metric("Pozycje w Portfelu", f"{len(enhanced_positions)} / {max_simul_pos}")
        kp4.metric("Sygnały Dokupienia (+0.5N)", f"{sum(1 for p in enhanced_positions if p['status'] == 'DOKUP')}")

        st.markdown("---")
        st.subheader("📋 Tabela Twoich Aktywnych Pozycji")

        table_rows = []
        for p in enhanced_positions:
            table_rows.append({
                "Symbol": p["symbol"],
                "Nazwa": p["name"],
                "Data Zakupu": p.get("entry_date", "-"),
                "Akcje": p["shares"],
                "Units": f"{p.get('units', 1)} / 4",
                "Śr. Zakup (PLN)": round(float(p["avg_price"]), 2),
                "Ostatni Zakup (PLN)": round(float(p.get("last_entry_price", p["avg_price"])), 2),
                "Kurs (PLN)": round(p["current_price"], 2),
                "Wynik (PLN)": round(p["pnl_pln"], 2),
                "Wynik (%)": f"{p['pnl_pct']:+.2f}%",
                "Stop Loss (PLN)": p["stop_loss"],
                "Kolejne Dokupienie (+0.5N)": p["next_pyramid_price"],
                "Zalecenie": p["action_badge"]
            })

        st.dataframe(pd.DataFrame(table_rows), use_container_width=True)

        st.markdown("---")
        st.subheader("⚙️ Operacje na Wybranej Pozycji Portfela")
        col_sel, col_act = st.columns([2, 3])

        with col_sel:
            selected_sym = st.selectbox(
                "Wybierz spółkę z portfela:",
                options=[p["symbol"] for p in enhanced_positions]
            )

        with col_act:
            if selected_sym:
                cur_pos = next(p for p in enhanced_positions if p["symbol"] == selected_sym)
                c_btn1, c_btn2 = st.columns(2)

                with c_btn1:
                    if cur_pos["units"] < 4:
                        if st.button(f"➕ Zrealizuj Dokupienie (+1 Unit) dla {selected_sym}", use_container_width=True):
                            add_price = cur_pos["current_price"]
                            new_stop = round(add_price - 2.0 * cur_pos["current_atr"], 2)
                            s_units = calculate_turtle_unit_size(initial_cap, risk_pct, add_price, new_stop, commission)
                            s_units = max(1, s_units)
                            new_shares = cur_pos["shares"] + s_units
                            new_total_cost = (cur_pos["shares"] * float(cur_pos["avg_price"])) + (s_units * add_price)
                            new_avg = new_total_cost / new_shares

                            for p in positions:
                                if p["symbol"] == selected_sym:
                                    p["shares"] = new_shares
                                    p["avg_price"] = new_avg
                                    p["last_entry_price"] = add_price
                                    p["units"] = p.get("units", 1) + 1
                                    p["stop_loss"] = new_stop
                            save_portfolio(positions)
                            st.session_state["user_portfolio"] = positions
                            st.success(f"Dodano jednostkę dla {selected_sym}! Nowy stan: {new_shares} akcji, średnia cena {new_avg:.2f} PLN, Stop Loss: {new_stop:.2f} PLN.")
                            safe_rerun()
                    else:
                        st.info(f"{selected_sym} osiągnął już maksymalny limit 4 jednostek.")

                with c_btn2:
                    if st.button(f"❌ Zamknij Pozycję {selected_sym}", type="secondary", use_container_width=True):
                        hist = load_closed_history()
                        hist.append({
                            "Symbol": selected_sym,
                            "Nazwa": cur_pos["name"],
                            "Data Zakupu": cur_pos.get("entry_date", "-"),
                            "Data Zamknięcia": date.today().strftime("%Y-%m-%d"),
                            "Akcje": cur_pos["shares"],
                            "Jednostki": cur_pos["units"],
                            "Śr. Cena Zakupu": round(float(cur_pos["avg_price"]), 2),
                            "Cena Zamknięcia": round(cur_pos["current_price"], 2),
                            "Zysk/Strata (PLN)": round(cur_pos["pnl_pln"], 2),
                            "Zysk/Strata (%)": f"{cur_pos['pnl_pct']:+.2f}%",
                            "Powód": cur_pos["status"]
                        })
                        save_closed_history(hist)

                        positions = [p for p in positions if p["symbol"] != selected_sym]
                        save_portfolio(positions)
                        st.session_state["user_portfolio"] = positions
                        st.warning(f"Zamknięto pozycję {selected_sym} i przeniesiono do historii transakcji.")
                        safe_rerun()

    else:
        st.info("Twój portfel jest obecnie pusty. Skorzystaj z powyższego narzędzia 'Audyt Rynku', aby jednym kliknięciem załadować trwające trendy, lub dodaj spółkę ręcznie.")

    st.markdown("---")
    with st.expander("➕ Dodaj Spółkę do Portfela Ręcznie"):
        all_syms = get_ticker_list()
        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            manual_sym = st.selectbox("Symbol spółki:", options=all_syms)
        with fc2:
            manual_date = st.date_input("Data otwarcia pozycji:", value=date.today())
        with fc3:
            manual_shares = st.number_input("Liczba akcji (Units):", min_value=1, value=100, step=10)

        fc4, fc5, fc6 = st.columns(3)
        with fc4:
            manual_price = st.number_input("Cena zakupu za akcję (PLN):", min_value=0.01, value=10.0, step=0.1)
        with fc5:
            manual_atr = st.number_input("Wartość ATR (N) przy wejściu:", min_value=0.01, value=1.0, step=0.05)
        with fc6:
            calc_manual_stop = round(manual_price - 2.0 * manual_atr, 2)
            manual_stop = st.number_input("Stop Loss (domyślnie 2x ATR):", value=calc_manual_stop)

        if st.button("💾 Zapisz Pozycję w Portfelu", type="primary"):
            positions = st.session_state.get("user_portfolio", [])
            if any(p["symbol"] == manual_sym for p in positions):
                st.error(f"Spółka {manual_sym} już znajduje się w Twoim portfelu!")
            else:
                positions.append({
                    "symbol": manual_sym,
                    "name": get_ticker_info(manual_sym)["name"],
                    "entry_date": manual_date.strftime("%Y-%m-%d"),
                    "shares": int(manual_shares),
                    "units": 1,
                    "avg_price": float(manual_price),
                    "last_entry_price": float(manual_price),
                    "entry_atr": float(manual_atr),
                    "stop_loss": float(manual_stop)
                })
                save_portfolio(positions)
                st.session_state["user_portfolio"] = positions
                st.success(f"Dodano {manual_sym} do portfela!")
                safe_rerun()

    closed_trades = load_closed_history()
    if closed_trades:
        st.markdown("---")
        with st.expander(f"📜 Historia Zamkniętych Pozycji ({len(closed_trades)} transakcji)"):
            st.dataframe(pd.DataFrame(closed_trades), use_container_width=True)


# ==========================================
# ZAKŁADKA 2: SKANER RYNKU (TYLKO ŚWIEŻE WEJŚCIA)
# ==========================================
with tab_scanner:
    st.subheader("🎯 Skaner Rynku GPW & NewConnect – Wyłącznie Świeże Wybicia")
    
    portfolio_symbols = [p["symbol"] for p in st.session_state.get("user_portfolio", [])]
    if portfolio_symbols:
        st.info(f"💡 **Spółki w Twoim portfelu ({len(portfolio_symbols)}):** {', '.join(portfolio_symbols)}. Zostały wyłączone z tego skanera, ponieważ są już monitorowane w zakładce Portfel pod kątem dokupienia lub sprzedaży.")

    st.markdown("""
    **Zasada działania skanera i egzekucji:**
    * Przeszukuje rynek pod kątem **TYLKO I WYŁĄCZNIE ŚWIEŻEGO WYBICIA 20-DNIOWEGO KANAŁU DONCHIANA** (Breakout High na sesji T).
    * **Egzekucja wejścia:** Zlecenie kupna składane jest na **kolejny dzień sesyjny po cenie otwarcia (Open T+1)**.
    * **Zarządzanie wielkością pozycji (Tradycyjny model Żółwi):** 1 Unit = floor((Kapitał × 1%) / ATR). Stop Loss wynosi standardowo 2 × ATR ($2N$) od poziomu wejścia.
    * Spółki z portfela są wyłączone ze skanera i monitorowane w zakładce Portfel pod kątem dokupienia (+0.5 ATR) lub sprzedaży.
    """)

    col_btn, col_info = st.columns([1, 3])
    with col_btn:
        run_scan = st.button("🚀 Skanuj Rynek (Świeże Wybicia)", type="primary", use_container_width=True)
    with col_info:
        st.caption(f"Filtr: Płynność min. {min_turnover:,.0f} PLN | Długość kanału: {entry_days} sesji | Tradycyjny model Żółwi (1 Unit = 1% / ATR)")

    if run_scan or "scan_results" in st.session_state:
        if run_scan:
            scan_data = []
            all_tickers = get_ticker_list()
            # Wykluczamy spółki będące już w portfelu!
            available_tickers = [s for s in all_tickers if s not in portfolio_symbols]
            total = len(available_tickers)
            progress_bar = st.progress(0, text="Skanowanie rynku w poszukiwaniu świeżych wybić...")

            for idx, symbol in enumerate(available_tickers):
                progress_bar.progress((idx + 1) / total, text=f"Analiza {symbol} ({idx+1}/{total})...")
                df = fetch_ticker_data(symbol, start_date="2023-01-01")
                if df.empty or len(df) < turnover_window:
                    continue

                recent_turnover = (df["Close"] * df["Volume"]).tail(turnover_window).mean()
                if recent_turnover < min_turnover:
                    continue

                info = get_ticker_info(symbol)
                calc_df = calculate_indicators(df, entry_period=entry_days, exit_period=exit_days, atr_period=atr_days)
                if calc_df.empty or len(calc_df) < 2:
                    continue

                last_row = calc_df.iloc[-1]
                prev_row = calc_df.iloc[-2]

                close = float(last_row["Close"])
                prev_close = float(prev_row["Close"])
                change_pct = ((close - prev_close) / prev_close) * 100 if prev_close > 0 else 0.0
                atr = float(last_row["ATR"])
                donch_high = float(last_row["Donchian_High"])
                prev_donch_high = float(prev_row["Donchian_High"])

                # ŚWIEŻE WYBICIE GÓRNEGO KANAŁU DZIŚ:
                is_fresh_buy = (close > donch_high) and (prev_close <= prev_donch_high)

                if is_fresh_buy:
                    stop_loss = round(close - (2.0 * atr), 2)
                    unit_size = calculate_turtle_unit_size(initial_cap, risk_pct, atr, close)
                    position_val = unit_size * close
                    total_risk_val = unit_size * atr

                    scan_data.append({
                        "Symbol": symbol,
                        "Nazwa": info["name"],
                        "Cena Sygnału (Close T)": round(close, 2),
                        "Zlecenie Egzekucji": "Kupno na Otwarcie (Open T+1)",
                        "Zmiana (%)": round(change_pct, 2),
                        "Donchian High (20d)": round(donch_high, 2),
                        "ATR (20) [N]": round(atr, 2),
                        "Stop Loss (2x N)": stop_loss,
                        "Unit Size (Tradycyjny 1 Unit)": unit_size,
                        "Wartość Zlecenia (PLN)": round(position_val, 2),
                        "Ekspozycja Ryzyka (1N)": f"{total_risk_val:,.0f} PLN",
                        "Śr. Obrót 60d (PLN)": round(recent_turnover, 0),
                        "Indeks": info["index"],
                        "Sektor": info["sector"]
                    })

            progress_bar.empty()
            st.session_state["scan_results"] = pd.DataFrame(scan_data)

        fresh_results = st.session_state.get("scan_results", pd.DataFrame())

        if not fresh_results.empty:
            st.success(f"🎉 Wykryto **{len(fresh_results)} ŚWIEŻYCH SYGNAŁÓW KUPNA** na GPW/NC po ostatniej sesji!")
            st.dataframe(fresh_results, use_container_width=True)

            # Szybkie kupno i dodanie do portfela
            st.markdown("---")
            st.subheader("⚡ Kup i Przenieś Świeże Wybicie do Mojego Portfela (Egzekucja na Open T+1):")
            q_col1, q_col2 = st.columns([2, 1])
            with q_col1:
                fresh_pick = st.selectbox(
                    "Wybierz spółkę ze świeżego wybicia:",
                    options=fresh_results["Symbol"].tolist()
                )
            with q_col2:
                st.write("")
                st.write("")
                if st.button("📥 Kup 1. Jednostkę i Dodaj do Portfela", type="primary", use_container_width=True):
                    pick_row = fresh_results[fresh_results["Symbol"] == fresh_pick].iloc[0]
                    cur_positions = st.session_state.get("user_portfolio", [])
                    cur_positions.append({
                        "symbol": fresh_pick,
                        "name": pick_row["Nazwa"],
                        "entry_date": (date.today() + pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
                        "shares": int(pick_row["Unit Size (Tradycyjny 1 Unit)"]),
                        "units": 1,
                        "avg_price": float(pick_row["Cena Sygnału (Close T)"]),
                        "last_entry_price": float(pick_row["Cena Sygnału (Close T)"]),
                        "entry_atr": float(pick_row["ATR (20) [N]"]),
                        "stop_loss": float(pick_row["Stop Loss (2x N)"]),
                        "note": "Wejście po cenie otwarcia kolejnej sesji (Open T+1)"
                    })
                    save_portfolio(cur_positions)
                    st.session_state["user_portfolio"] = cur_positions
                    st.success(f"Pomyślnie dodano {fresh_pick}! Spółka trafiła do Portfela (wejście na Otwarcie T+1) i od teraz będą dla niej generowane sygnały dokupienia lub sprzedaży.")
                    safe_rerun()
        else:
            st.info("Brak świeżych wybić na ostatniej sesji dla wolnych spółek z rynku. Żadna nowa spółka nie wybiła dzisiaj 20-dniowego szczytu.")


# ==========================================
# ZAKŁADKA 3: BACKTEST PORTFELA RAZEM
# ==========================================
with tab_backtest:
    st.subheader("Symulacja Portfelowa dla WSZYSTKICH Spółek GPW / NC Razem")
    st.markdown("""
    Symulacja uruchamia **jeden wspólny portfel inwestycyjny** dla całego koszyka spółek o zadanym poziomie obrotu (domyślnie min. 100k PLN z 60 sesji).
    Kapitał jest alokowany **wyłącznie przy świeżych wybiciach**, a w trakcie trwania trendu realizowane jest **dokupowanie (piramidowanie co +0.5 N do 4 jednostek)** z podnoszeniem Stop Lossa.
    """)

    col_d1, col_d2, col_btn = st.columns([1, 1, 1])
    with col_d1:
        start_date_input = st.date_input("Data początkowa (od 2015)", value=date(2015, 1, 1), min_value=date(2015, 1, 1), max_value=date.today())
    with col_d2:
        end_date_input = st.date_input("Data końcowa", value=date.today(), min_value=date(2015, 1, 2), max_value=date.today())
    with col_btn:
        st.write("")
        st.write("")
        run_port_btn = st.button("📊 Uruchom Symulację Całego Portfela", type="primary", use_container_width=True)

    if run_port_btn or "portfolio_backtest_res" in st.session_state:
        if run_port_btn:
            tickers = get_ticker_list()
            data_dict = {}
            prog = st.progress(0, text="Pobieranie notowań spółek koszyka...")

            for idx, symbol in enumerate(tickers):
                prog.progress((idx + 1) / len(tickers), text=f"Wczytywanie {symbol} ({idx+1}/{len(tickers)})...")
                raw = fetch_ticker_data(symbol, start_date=start_date_input.strftime("%Y-%m-%d"))
                if not raw.empty:
                    sliced = raw.loc[str(start_date_input):str(end_date_input)]
                    if len(sliced) >= turnover_window:
                        calc = calculate_indicators(sliced, entry_period=entry_days, exit_period=exit_days, atr_period=atr_days)
                        data_dict[symbol] = calc

            prog.empty()

            with st.spinner("Przetwarzanie portfelowej symulacji Turtle z piramidowaniem dla wszystkich spółek..."):
                res = run_portfolio_turtle_backtest(
                    data_dict=data_dict,
                    initial_capital=initial_cap,
                    risk_pct=risk_pct,
                    entry_period=entry_days,
                    exit_period=exit_days,
                    atr_period=atr_days,
                    commission_pct=commission,
                    min_turnover=min_turnover,
                    turnover_days=turnover_window,
                    max_positions=max_simul_pos
                )
                st.session_state["portfolio_backtest_res"] = res

        result = st.session_state.get("portfolio_backtest_res")

        if result is None:
            st.error("Brak wystarczających danych do przeprowadzenia symulacji portfelowej.")
        else:
            m1, m2, m3, m4, m5, m6 = st.columns(6)
            ret = result["total_return_pct"]
            m1.metric("Wynik Portfela", f"{ret:+.2f}%", delta=f"{result['final_equity'] - initial_cap:+,.0f} PLN")
            m2.metric("Max Drawdown Portfela", f"{result['max_drawdown_pct']:.2f}%")
            m3.metric("Sharpe Ratio", f"{result['sharpe_ratio']:.2f}")
            m4.metric("Liczba Transakcji Razem", result["total_trades"])
            m5.metric("Skuteczność (Win Rate)", f"{result['win_rate']:.1f}%")
            m6.metric("Profit Factor", f"{result['profit_factor']:.2f}")

            st.markdown("---")

            eq_df = result["equity_df"]
            trades_df = result["trades_df"]

            fig = make_subplots(
                rows=3, cols=1,
                shared_xaxes=True,
                vertical_spacing=0.04,
                subplot_titles=(
                    f"Krzywa Kapitału Portfela Turtle (Wszystkie Płynne Spółki Razem) vs Benchmark",
                    "Liczba Jednocześnie Otwartych Pozycji w Portfelu",
                    "Obsunięcie Kapitału Portfela (Drawdown %)"
                ),
                row_heights=[0.55, 0.25, 0.20]
            )

            fig.add_trace(go.Scatter(
                x=eq_df["Date"], y=eq_df["Equity"],
                mode="lines", name="Kapitał Portfela Turtle (PLN)",
                line=dict(color="#10b981", width=2.5)
            ), row=1, col=1)

            fig.add_trace(go.Scatter(
                x=eq_df["Date"], y=eq_df["Benchmark"],
                mode="lines", name="Benchmark Kup i Trzymaj (PLN)",
                line=dict(color="#94a3b8", width=1.5, dash="dot")
            ), row=1, col=1)

            fig.add_trace(go.Bar(
                x=eq_df["Date"], y=eq_df["Active_Positions"],
                name="Aktywne Spółki w Portfelu",
                marker_color="#38bdf8"
            ), row=2, col=1)

            fig.add_trace(go.Scatter(
                x=eq_df["Date"], y=eq_df["Drawdown"],
                mode="lines", name="Obsunięcie (%)",
                line=dict(color="#ef4444", width=1.5),
                fill="tozeroy"
            ), row=3, col=1)

            fig.update_layout(
                height=850,
                template="plotly_dark",
                hovermode="x unified",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )

            st.plotly_chart(fig, use_container_width=True)

            st.subheader("📊 Wyniki w Rozbiciu na Poszczególne Spółki Portfela")
            sym_df = result["symbol_stats_df"]
            if not sym_df.empty:
                st.dataframe(sym_df, use_container_width=True)

            st.subheader(f"📋 Chronologiczny Dziennik Wszystkich Transakcji Portfela ({len(trades_df)})")
            if not trades_df.empty:
                st.dataframe(trades_df, use_container_width=True)
                csv_trades = trades_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    "📥 Pobierz pełny dziennik transakcji (CSV)",
                    data=csv_trades,
                    file_name=f"portfolio_turtle_trades_{date.today().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
            else:
                st.info("Brak zamkniętych transakcji w zadanym oknie czasowym.")


# ==========================================
# ZAKŁADKA 4: BAZA DANYCH NA DYSKU (PARQUET)
# ==========================================
with tab_database:
    st.subheader("💾 Trwała Baza Danych na Dysku Komputera (Format Apache Parquet)")
    st.markdown(f"""
    Dane historyczne od 2015 r. pobierane są **dwuetapowo** i zapisywane **trwale na dysku w plikach `.parquet`** (katalog `{CACHE_DIR}/`).
    
    > 💡 **Dlaczego to idealne rozwiązanie?**  
    > Ponieważ symulacje testowe wykonujesz maksymalnie **1-2 razy w roku**, nie potrzebujesz codziennego odpytywania API. Raz pobrana baza pozwala na błyskawiczne, wielokrotne testowanie strategii offline w ułamku sekundy bez obciążania łącza.
    """)

    if st.button("🚀 Uruchom Dwuetapową Synchronizację i Zapisz do Parquet", type="primary", use_container_width=True):
        try:
            from sync_gpw_data import sync_database_with_liquidity_filter
            prog = st.progress(0, text="Inicjalizacja pobierania arkuszy GPW & NC...")
            def progress_tracker(curr, total, msg):
                prog.progress(curr / total, text=msg)

            with st.spinner("Pobieranie oficjalnych arkuszy, selekcja płynności i zapis do bazy Parquet..."):
                saved_tickers = sync_database_with_liquidity_filter(
                    min_turnover_pln=min_turnover,
                    turnover_days=turnover_window,
                    progress_callback=progress_tracker
                )
            prog.empty()
            st.success(f"✅ Pomyślnie zsynchronizowano bazę danych! Zapisano {len(saved_tickers)} płynnych spółek w katalogu {CACHE_DIR}/.")
            safe_rerun()
        except ImportError:
            st.error("Plik `sync_gpw_data.py` nie został znaleziony w bieżącym katalogu.")
        except Exception as e:
            st.error(f"Wystąpił błąd podczas synchronizacji: {e}")

    if cached_files:
        st.markdown("---")
        st.subheader(f"📁 Pliki Parquet Aktualnie Zapisane na Dysku ({len(cached_files)} plików)")
        file_stats = []
        for cf in cached_files:
            fp = os.path.join(CACHE_DIR, cf)
            size_kb = os.path.getsize(fp) / 1024.0
            mtime = datetime.fromtimestamp(os.path.getmtime(fp)).strftime("%Y-%m-%d %H:%M")
            sym = cf.replace("_parquet", "").replace(".parquet", "").replace("_WA", ".WA")
            try:
                p_df = pd.read_parquet(fp)
                rows = len(p_df)
                d_start = str(p_df.index.min())[:10] if not p_df.empty else "-"
                d_end = str(p_df.index.max())[:10] if not p_df.empty else "-"
            except Exception:
                rows = 0
                d_start, d_end = "-", "-"

            file_stats.append({
                "Plik Parquet": cf,
                "Symbol Ticker": sym,
                "Liczba Sesji": rows,
                "Zakres Dat": f"{d_start} -> {d_end}",
                "Rozmiar (KB)": round(size_kb, 1),
                "Ostatnia Modyfikacja": mtime
            })

        df_stats = pd.DataFrame(file_stats)
        st.dataframe(df_stats, use_container_width=True)
    else:
        st.info(f"Katalog `{CACHE_DIR}` jest obecnie pusty. Kliknij powyższy przycisk, aby pobrać oficjalne arkusze GPW i stworzyć bazę Parquet.")


# ==========================================
# ZAKŁADKA 5: KOMPENDIUM I OPIS STRATEGII
# ==========================================
with tab_guide:
    st.subheader("Filozofia i Zasady Żółwi (The Turtle Trading System)")
    st.markdown("""
    Eksperyment Żółwi został przeprowadzony w 1983 roku przez legendarnych inwestorów **Richarda Dennisa** i **Williama Eckhardta**, aby udowodnić, że skutecznego tradingu można nauczyć każdego za pomocą ścisłych, algorytmicznych reguł.

    ### 1. Rozłączny Model Portfela i Rynku
    * **Spółki poza portfelem (Rynek):** Skanujemy wyłącznie pod kątem **świeżego wybicia 20-dniowego szczytu**. Nie ma sensu badać dla nich dołków ani sygnałów sprzedaży, dopóki nie są w portfelu.
    * **Spółki w portfelu:** Gdy spółka zostanie kupiona, nie czekamy na nowe wybicia 20-dniowe. Obserwujemy ją wyłącznie pod kątem:
      - **Dokupienia (+0.5 N)**,
      - **Stop Lossa (2x N)**,
      - **Wyjścia z trendu (przebicie dołka 10-dniowego)**.

    ### 2. Dokupowanie (Piramidowanie – Pyramiding Units)
    * Wejście w trend następuje 1 jednostką (*Unit*).
    * Jeśli rynek porusza się w dobrą stronę, dokupujemy kolejną 1 jednostkę za każdym razem, gdy kurs wzrośnie o **$+0.5 \\times N$** powyżej ceny ostatniego zakupu (maksymalnie do 4 jednostek).
    * Każde dokupienie podnosi Stop Loss dla WSZYSTKICH jednostek:
      $$\\text{Stop Loss} = \\text{Cena Ostatniego Zakupu} - 2 \\times N$$

    ### 3. Dobór Wielkości Jednostki (Unit Size)
    * Każda pojedyncza jednostka ryzykuje dokładnie **1% kapitału**:
      $$\\text{Unit Size} = \\left\\lfloor \\frac{\\text{Kapitał} \\times 1\\%}{\\text{ATR}} \\right\\rfloor$$
    """)
