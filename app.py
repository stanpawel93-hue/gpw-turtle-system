"""
System Transakcyjny Żółwi (Turtle Trading System) dla GPW i NewConnect
Aplikacja Streamlit do skanowania sygnałów dziennych oraz backtestu historycznego.
"""

import os
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
    # Wbudowany kompletny fallback głównych spółek GPW i NewConnect,
    # aby app.py działał nawet jeśli plik gpw_tickers.py nie został skopiowany
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

# Bezpieczny rerun kompatybilny z każdą wersją Streamlit
def safe_rerun():
    if hasattr(st, "rerun"):
        st.rerun()
    elif hasattr(st, "experimental_rerun"):
        st.experimental_rerun()

# Stylizacja CSS dla kart wskaźników
st.markdown("""
<style>
    .metric-card {
        background-color: #1e293b;
        border-radius: 8px;
        padding: 16px;
        color: white;
        border: 1px solid #334155;
    }
    .metric-value {
        font-size: 24px;
        font-weight: 700;
        margin-top: 4px;
    }
</style>
""", unsafe_allow_html=True)

# Katalog cache dla danych historycznych
CACHE_DIR = "cache_data"
os.makedirs(CACHE_DIR, exist_ok=True)

# Dekorator cache kompatybilny wstecznie
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
# FUNKCJE POBIERANIA I CACHOWANIA DANYCH
# ==========================================
@get_cache_decorator()
def fetch_ticker_data(symbol: str, start_date: str = "2015-01-01") -> pd.DataFrame:
    """
    Pobiera dane dzienne OHLCV z Yahoo Finance od wybranej daty.
    Zapisuje i odczytuje lokalny cache Parquet dla maksymalnej szybkości.
    """
    cache_file = os.path.join(CACHE_DIR, f"{symbol.replace('.', '_')}.parquet")
    
    # Odczytanie z trwałego cache lokalnego Parquet na dysku
    if os.path.exists(cache_file):
        try:
            df = pd.read_parquet(cache_file)
            if not df.empty:
                return df
        except Exception:
            pass

    try:
        # Pobieranie z yfinance
        df = yf.download(symbol, start=start_date, progress=False, auto_adjust=False)
        if df.empty:
            return pd.DataFrame()

        # Obsługa wielopoziomowych kolumn yfinance (MultiIndex)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # Standaryzacja kolumn
        df = df.rename(columns={
            "Open": "Open",
            "High": "High",
            "Low": "Low",
            "Close": "Close",
            "Volume": "Volume"
        })
        
        # Filtrujemy niepotrzebne i brakujące wiersze
        df = df.dropna(subset=["Close", "High", "Low", "Volume"])
        df = df[df["Volume"] >= 0]
        
        # Zapis do cache Parquet
        try:
            df.to_parquet(cache_file)
        except Exception:
            pass

        return df
    except Exception as e:
        return pd.DataFrame()


# ==========================================
# MATEMATYKA STRATEGII ŻÓŁWI (TURTLE)
# ==========================================
def calculate_indicators(df: pd.DataFrame, entry_period: int = 20, exit_period: int = 10, atr_period: int = 20):
    """
    Wylicza wskaźniki Turtle:
    1. True Range (TR) i ATR (N)
    2. Kanał Donchiana Górny (Entry) z wyłączeniem bieżącej świecy
    3. Kanał Donchiana Dolny (Exit) z wyłączeniem bieżącej świecy
    4. Średni obrót dzienny (Turnover) = Close * Volume
    """
    data = df.copy()
    
    # 1. True Range
    prev_close = data["Close"].shift(1)
    hl = data["High"] - data["Low"]
    hc = (data["High"] - prev_close).abs()
    lc = (data["Low"] - prev_close).abs()
    data["TR"] = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    
    # 2. ATR (N) - średnia ruchoma krocząca z TR
    data["ATR"] = data["TR"].rolling(window=atr_period, min_periods=1).mean()
    
    # 3. Kanały Donchiana (shift(1) chroni przed lookahead bias w analizie dziennej)
    data["Donchian_High"] = data["High"].shift(1).rolling(window=entry_period).max()
    data["Donchian_Low"] = data["Low"].shift(1).rolling(window=exit_period).min()
    
    # 4. Obrót dzienny i średni obrót
    data["Daily_Turnover"] = data["Close"] * data["Volume"]
    
    return data


def calculate_turtle_unit_size(capital: float, risk_pct: float, atr: float, price: float) -> int:
    """
    Oblicza wielkość pozycji wg reguły Żółwi:
    Ryzyko kwotowe = Kapitał * (Procent Ryzyka / 100)
    Unit Size = floor(Ryzyko kwotowe / ATR)
    """
    if atr <= 0 or price <= 0 or capital <= 0:
        return 0
    cash_at_risk = capital * (risk_pct / 100.0)
    raw_units = int(np.floor(cash_at_risk / atr))
    max_affordable = int(np.floor(capital / price))
    return max(0, min(raw_units, max_affordable))


def run_portfolio_turtle_backtest(data_dict: dict, initial_capital: float, risk_pct: float,
                                 entry_period: int, exit_period: int, atr_period: int,
                                 commission_pct: float, min_turnover: float, turnover_days: int,
                                 max_positions: int = 8):
    """
    Symulacja portfelowa strategii Żółwi dla WSZYSTKICH spółek spełniających warunek obrotu RAZEM.
    Wspólny kapitał (cash pool), współdzielone ryzyko i dynamiczny filtr płynności na każdą sesję.
    """
    if not data_dict:
        return None

    # Zbieramy wszystkie unikalne daty sesji w porządku chronologicznym
    all_dates = sorted(list(set().union(*[df.index.tolist() for df in data_dict.values()])))
    if len(all_dates) < max(entry_period, exit_period, turnover_days) + 10:
        return None

    cash = initial_capital
    open_positions = {} # {symbol: {"shares": int, "entry_price": float, "entry_date": date, "stop_loss": float}}
    trades = []
    equity_curve = []
    peak_equity = initial_capital
    max_dd = 0.0

    # Baza cenowa dla benchmarku (Kup i Trzymaj równoważony)
    base_prices = {sym: df["Close"].iloc[0] for sym, df in data_dict.items() if not df.empty and df["Close"].iloc[0] > 0}

    for current_date in all_dates:
        # 1. Wyjścia z pozycji (Stop Loss lub Donchian Low Exit)
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
                exit_reason = "Stop Loss (2x ATR)"
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
                cost = pos["shares"] * pos["entry_price"] * (1 + commission_pct / 100.0)
                pnl = net_rev - cost
                pnl_pct = (pnl / cost) * 100.0

                trades.append({
                    "Symbol": sym,
                    "Data Wejścia": pos["entry_date"].strftime("%Y-%m-%d") if hasattr(pos["entry_date"], "strftime") else str(pos["entry_date"])[:10],
                    "Cena Wejścia": round(pos["entry_price"], 2),
                    "Data Wyjścia": current_date.strftime("%Y-%m-%d") if hasattr(current_date, "strftime") else str(current_date)[:10],
                    "Cena Wyjścia": round(actual_exit, 2),
                    "Liczba Akcji": pos["shares"],
                    "Wynik (PLN)": round(pnl, 2),
                    "Wynik (%)": round(pnl_pct, 2),
                    "Powód Wyjścia": exit_reason
                })

                cash += net_rev
                del open_positions[sym]

        # 2. Wycena portfela przed nowymi wejściami (do kalkulacji wielkości ryzyka)
        curr_holdings_val = sum(
            pos["shares"] * float(data_dict[sym].loc[current_date]["Close"])
            for sym, pos in open_positions.items()
            if current_date in data_dict[sym].index
        )
        current_equity = cash + curr_holdings_val

        # 3. Wejścia w pozycje dla spółek spełniających obrót (jeśli mamy wolne sloty)
        if len(open_positions) < max_positions and current_date != all_dates[-1]:
            for sym, df in data_dict.items():
                if sym in open_positions:
                    continue
                if len(open_positions) >= max_positions:
                    break
                if current_date not in df.index:
                    continue

                # Badanie obrotu z ostatnich N sesji na bieżący dzień
                sub_history = df.loc[:current_date]
                if len(sub_history) < turnover_days:
                    continue
                rolling_turnover = sub_history["Daily_Turnover"].tail(turnover_days).mean()
                if rolling_turnover < min_turnover:
                    continue

                row = sub_history.iloc[-1]
                close = float(row["Close"])
                atr = float(row["ATR"])
                donch_high = float(row["Donchian_High"])

                # Sygnał kupna: Wybicie Donchian High
                if not np.isnan(donch_high) and close > donch_high and atr > 0:
                    cash_at_risk = current_equity * (risk_pct / 100.0)
                    raw_units = int(np.floor(cash_at_risk / atr))
                    max_cap_units = int(np.floor((current_equity * 0.25) / close)) # max 25% w 1 spółce
                    affordable_units = int(np.floor(cash / (close * (1 + commission_pct / 100.0))))
                    final_units = max(0, min(raw_units, max_cap_units, affordable_units))

                    if final_units > 0:
                        trade_cost = final_units * close
                        comm = trade_cost * (commission_pct / 100.0)
                        total_cost = trade_cost + comm
                        if cash >= total_cost:
                            cash -= total_cost
                            open_positions[sym] = {
                                "shares": final_units,
                                "entry_price": close,
                                "entry_date": current_date,
                                "stop_loss": round(close - (2.0 * atr), 2)
                            }

        # 4. Wycena EOD portfela i benchmarku
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

        # Benchmark równoważony
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

    # Statystyki per ticker
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
    st.sidebar.info("💡 **System 1 (Klasyczny):**\n- Wejście: Wybicie 20-dniowe\n- Wyjście: Wybicie 10-dniowe\n- ATR: 20 dni\n- Ryzyko: 1.0% kapitału")
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
        st.sidebar.error("Plik `sync_gpw_data.py` nie został znaleziony w bieżącym katalogu. Upewnij się, że pobrano wszystkie pliki projektu.")
    except Exception as e:
        st.sidebar.error(f"Błąd synchronizacji: {e}")


# ==========================================
# GŁÓWNA STRUKTURA ZAKŁADEK (TABS)
# ==========================================
st.title("🇵🇱 Analiza i Automatyzacja Strategii Żółwi (GPW / NewConnect)")
st.caption(f"Uniwersum GPW (.WA) od 2015 r. | Filtr: min. {min_turnover:,.0f} PLN z {turnover_window} sesji | Tryb: {strategy_mode}")

tab_database, tab_scanner, tab_backtest, tab_guide = st.tabs([
    "💾 Baza Danych na Dysku (Parquet & Linki GPW/NC)",
    "🎯 Dzienne Sygnały (Skaner)",
    "📈 Backtest Portfela GPW (Wszystkie Spółki Razem)",
    "📚 Kompendium i Opis Strategii"
])


# ==========================================
# ZAKŁADKA 0: BAZA DANYCH NA DYSKU (PARQUET)
# ==========================================
with tab_database:
    st.subheader("💾 Trwała Baza Danych na Dysku Komputera (Format Apache Parquet)")
    st.markdown(f"""
    Zgodnie z wymaganiem, dane historyczne od 2015 r. pobierane są **dwuetapowo** i zapisywane **trwale na dysku w plikach `.parquet`** (katalog `{CACHE_DIR}/`).
    
    > 💡 **Dlaczego to idealne rozwiązanie?**  
    > Ponieważ symulacje testowe wykonujesz maksymalnie **1-2 razy w roku**, nie potrzebujesz codziennego odpytywania API. Raz pobrana baza pozwala na błyskawiczne, wielokrotne testowanie strategii offline w ułamku sekundy bez obciążania łącza.
    """)

    # 4 karty metryk
    cached_files = [f for f in os.listdir(CACHE_DIR) if f.endswith(".parquet")] if os.path.exists(CACHE_DIR) else []
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Spółki w Bazie na Dysku", f"{len(cached_files)} walorów", delta="cache_data/*.parquet")
    c2.metric("Filtr Średniego Obrotu", f"{min_turnover:,.0f} PLN", delta=f"{turnover_window} ostatnich sesji")
    c3.metric("Zakres Historyczny", "od 2015 r. do dziś", delta="ponad 2 700 świec")
    c4.metric("Format Zapisu", "Apache Parquet", delta="kompresja snappy")

    st.markdown("---")
    st.subheader("🔗 Sprawdzone Oficjalne Źródła Notowań Ciągłych GPW i NewConnect")
    st.markdown("Skrypt automatycznie odpytuje poniższe oficjalne arkusze kalkulacyjne dla bieżącej lub wybranej sesji giełdowej:")

    col_l1, col_l2 = st.columns(2)
    with col_l1:
        st.markdown("**1. Giełda Papierów Wartościowych w Warszawie (Rynek Główny):**")
        st.code("https://www.gpw.pl/pub/GPW/files/quotations_xls/PL/akcje-i-pda/notowania-ciagle/{date_str}.xls", language="text")
    with col_l2:
        st.markdown("**2. Rynek NewConnect (NC):**")
        st.code("https://newconnect.pl/pub/NEWCONNECT/files/quotations_xls/PL/notowania-ciagle/{date_str}.xls", language="text")

    st.markdown("---")
    st.subheader("⚙️ Dwuetapowy Mechanizm Pobierania i Aktualizacji")
    st.markdown(f"""
    1. **Krok 1 (Pobranie pełnej listy):** Skrypt pobiera oba oficjalne pliki `.xls` zawierające komplet spółek (~760 walorów).
    2. **Krok 2 (Weryfikacja płynności):** Bada średni obrót dzienny (Cena * Wolumen) z ostatnich **{turnover_window} sesji**. Spółki o obrocie poniżej **{min_turnover:,.0f} PLN** są natychmiast odrzucane.
    3. **Krok 3 (Pobranie i zapis Parquet):** Pełna historia OHLCV od 2015 r. pobierana jest **tylko dla spółek spełniających warunek płynności** i zapisywana w `{CACHE_DIR}/<SYMBOL>.parquet`.
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
            st.error("Plik `sync_gpw_data.py` nie został znaleziony w bieżącym katalogu. Upewnij się, że plik `sync_gpw_data.py` znajduje się w tym samym folderze co `app.py`.")
        except Exception as e:
            st.error(f"Wystąpił błąd podczas synchronizacji: {e}")

    # Tabela istniejących plików Parquet
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
# ZAKŁADKA 1: SKANER SYGNAŁÓW DZIENNYCH
# ==========================================
with tab_scanner:
    st.subheader("Skaner Rynku GPW & NewConnect po zamknięciu sesji")
    st.markdown("Wykrywa aktualne wybicia ze szczytów i dołków kanału Donchiana oraz kalkuluje bezpieczną wielkość pozycji (*Unit Size*) zgodnie z zasadami Richarda Dennisa.")

    col_btn, col_opt = st.columns([1, 3])
    with col_btn:
        run_scan = st.button("🚀 Uruchom Skanowanie Rynku", type="primary", use_container_width=True)
    with col_opt:
        filter_signal = st.selectbox("Filtruj tabelę:", ["Wszystkie spółki spełniające płynność", "Tylko Sygnały KUPNA (Breakout High)", "Tylko Sygnały SPRZEDAŻY (Exit Low)"])

    if run_scan or "scan_results" in st.session_state:
        if run_scan:
            scan_data = []
            progress_bar = st.progress(0, text="Pobieranie notowań z GPW...")
            tickers = get_ticker_list()
            total = len(tickers)

            for idx, symbol in enumerate(tickers):
                progress_bar.progress((idx + 1) / total, text=f"Analiza {symbol} ({idx+1}/{total})...")
                df = fetch_ticker_data(symbol, start_date="2023-01-01")
                if df.empty or len(df) < turnover_window:
                    continue

                recent_turnover = (df["Close"] * df["Volume"]).tail(turnover_window).mean()
                if recent_turnover < min_turnover:
                    continue

                info = get_ticker_info(symbol)
                calc_df = calculate_indicators(df, entry_period=entry_days, exit_period=exit_days, atr_period=atr_days)
                if calc_df.empty:
                    continue

                last_row = calc_df.iloc[-1]
                prev_row = calc_df.iloc[-2] if len(calc_df) >= 2 else last_row

                close = float(last_row["Close"])
                prev_close = float(prev_row["Close"])
                change_pct = ((close - prev_close) / prev_close) * 100 if prev_close > 0 else 0.0
                atr = float(last_row["ATR"])
                donch_high = float(last_row["Donchian_High"])
                donch_low = float(last_row["Donchian_Low"])

                signal = "BRAK"
                if close > donch_high:
                    signal = "KUPUJ (Breakout)"
                elif close < donch_low:
                    signal = "SPRZEDAJ (Exit)"

                unit_size = calculate_turtle_unit_size(initial_cap, risk_pct, atr, close)
                position_val = unit_size * close
                stop_loss = round(close - (2.0 * atr), 2)

                scan_data.append({
                    "Symbol": symbol,
                    "Nazwa": info["name"],
                    "Indeks": info["index"],
                    "Sektor": info["sector"],
                    "Cena (PLN)": round(close, 2),
                    "Zmiana (%)": round(change_pct, 2),
                    "Śr. Obrót 60d (PLN)": round(recent_turnover, 0),
                    "ATR (20)": round(atr, 2),
                    "Sygnał": signal,
                    "Donchian High": round(donch_high, 2),
                    "Donchian Low": round(donch_low, 2),
                    "Stop Loss (2x ATR)": stop_loss,
                    "Unit Size (Akcje)": unit_size,
                    "Wartość Pozycji (PLN)": round(position_val, 2),
                    "Ryzyko PLN (1%)": round(initial_cap * (risk_pct / 100), 2)
                })

            progress_bar.empty()
            st.session_state["scan_results"] = pd.DataFrame(scan_data)

        results_df = st.session_state.get("scan_results", pd.DataFrame())

        if not results_df.empty:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Spółki spełniające płynność", len(results_df))
            buy_count = len(results_df[results_df["Sygnał"] == "KUPUJ (Breakout)"])
            sell_count = len(results_df[results_df["Sygnał"] == "SPRZEDAJ (Exit)"])
            c2.metric("Sygnały KUPNA", buy_count)
            c3.metric("Sygnały SPRZEDAŻY", sell_count)
            c4.metric("Kapitał w kalkulatorze", f"{initial_cap:,.0f} PLN")

            filtered_df = results_df.copy()
            if filter_signal == "Tylko Sygnały KUPNA (Breakout High)":
                filtered_df = filtered_df[filtered_df["Sygnał"] == "KUPUJ (Breakout)"]
            elif filter_signal == "Tylko Sygnały SPRZEDAŻY (Exit Low)":
                filtered_df = filtered_df[filtered_df["Sygnał"] == "SPRZEDAJ (Exit)"]

            st.dataframe(filtered_df, use_container_width=True, height=500)

            csv = filtered_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                "📥 Pobierz wyniki skanera do CSV",
                data=csv,
                file_name=f"turtle_signals_gpw_{date.today().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )


# ==========================================
# ZAKŁADKA 2: BACKTEST PORTFELA RAZEM (WSZYSTKIE SPÓŁKI)
# ==========================================
with tab_backtest:
    st.subheader("Symulacja Portfelowa dla WSZYSTKICH Spółek GPW / NC Razem")
    st.markdown("""
    Symulacja uruchamia **jeden wspólny portfel inwestycyjny** dla całego koszyka spółek o zadanym poziomie obrotu (domyślnie min. 100k PLN z 60 sesji).
    Kapitał jest dynamicznie alokowany pomiędzy pojawiające się wybicia szczytów wg zasady 1% ryzyka kapitału na 1x ATR, a pozycje zamykane są po osiągnięciu Stop Lossa (2x ATR) lub wybicia dołka kanału Donchiana.
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
                    # Ograniczenie do wybranego przedziału dat
                    sliced = raw.loc[str(start_date_input):str(end_date_input)]
                    if len(sliced) >= turnover_window:
                        calc = calculate_indicators(sliced, entry_period=entry_days, exit_period=exit_days, atr_period=atr_days)
                        data_dict[symbol] = calc

            prog.empty()

            with st.spinner("Przetwarzanie portfelowej symulacji Turtle dla wszystkich płynnych spółek..."):
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
            # Główne metryki portfela
            m1, m2, m3, m4, m5, m6 = st.columns(6)
            ret = result["total_return_pct"]
            m1.metric("Wynik Portfela", f"{ret:+.2f}%", delta=f"{result['final_equity'] - initial_cap:+,.0f} PLN")
            m2.metric("Max Drawdown Portfela", f"{result['max_drawdown_pct']:.2f}%")
            m3.metric("Sharpe Ratio", f"{result['sharpe_ratio']:.2f}")
            m4.metric("Liczba Transakcji Razem", result["total_trades"])
            m5.metric("Skuteczność (Win Rate)", f"{result['win_rate']:.1f}%")
            m6.metric("Profit Factor", f"{result['profit_factor']:.2f}")

            st.markdown("---")

            # Wykres Plotly: Krzywa Kapitału Portfela vs Benchmark
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

            # 1. Krzywa kapitału
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

            # 2. Liczba aktywnych pozycji
            fig.add_trace(go.Bar(
                x=eq_df["Date"], y=eq_df["Active_Positions"],
                name="Aktywne Spółki w Portfelu",
                marker_color="#38bdf8"
            ), row=2, col=1)

            # 3. Drawdown
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

            # Rozbicie wyników na poszczególne spółki z portfela
            st.subheader("📊 Wyniki w Rozbiciu na Poszczególne Spółki Portfela")
            sym_df = result["symbol_stats_df"]
            if not sym_df.empty:
                st.dataframe(sym_df, use_container_width=True)

            # Pełny chronologiczny dziennik transakcji
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
# ZAKŁADKA 3: KOMPENDIUM I OPIS STRATEGII
# ==========================================
with tab_guide:
    st.subheader("Filozofia i Zasady Żółwi (The Turtle Trading System)")
    st.markdown("""
    Eksperyment Żółwi został przeprowadzony w 1983 roku przez legendarnych inwestorów **Richarda Dennisa** i **Williama Eckhardta**, aby udowodnić, że skutecznego tradingu można nauczyć każdego za pomocą ścisłych, algorytmicznych reguł.

    ### 1. Kanał Donchiana (Donchian Breakout)
    * **System 1 (Klasyczny):**
      - **Kupno (Wejście):** Zamknięcie świecy dziennej powyżej najwyższego maksimum z ostatnich **20 dni**.
      - **Sprzedaż (Wyjście):** Zamknięcie świecy dziennej poniżej najniższego minimum z ostatnich **10 dni**.
    * **Własna modyfikacja:** Możesz dowolnie testować dłuższe trendy (np. wejście 55 dni, wyjście 20 dni).

    ### 2. Zmienność i Wskaźnik ATR (N)
    * Zmienność rynku mierzona jest wskaźnikiem **ATR (Average True Range)** z okresu 20 dni, oznaczanym w systemie jako **$N$**.
    * Prawdziwy zasięg (*True Range*):
      $$\\text{TR} = \\max(H - L, |H - C_{\\text{prev}}|, |L - C_{\\text{prev}}|)$$
    * ATR normalizuje zmienność pomiędzy różnymi spółkami (np. Orlen vs CD Projekt).

    ### 3. Dobór Wielkości Pozycji (Turtle Unit Sizing)
    * Każda pozycja ryzykować może dokładnie **1% kapitału** (lub inną wartość zdefiniowaną w panelu bocznym).
    * Liczba kupowanych akcji (*Unit Size*):
      $$\\text{Unit Size} = \\left\\lfloor \\frac{\\text{Kapitał} \\times \\text{Ryzyko (\\%)}}{\\text{ATR}} \\right\\rfloor$$
    * **Twardy Stop Loss:** Zgodnie z regułami Żółwi, obronne zlecenie stop loss ustawiane jest na poziomie **$2 \\times N$ (2 ATR)** poniżej ceny wejścia.

    ### 4. Filtr Płynności na GPW
    * Rynek polski posiada mniejszą płynność niż rynek amerykański, dlatego domyślny filtr **100 000 PLN średniego obrotu z 60 sesji** chroni przed spółkami groszowymi oraz ryzykiem braku płynności przy zamykaniu pozycji.
    """)
