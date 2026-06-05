"""
============================================================
  INDIAN STOCK EMA 20/50 SWING TRADE SCANNER
  Scans Nifty 100 + Midcap 150 stocks
  Signals: Golden Cross + EMA 20 Bounce
============================================================

SETUP (run once):ṇ
    pip install yfinance pandas pandas-ta colorama

RUN:
    python indian_ema_scanner.py
"""

import yfinance as yf
import pandas as pd
import pandas_ta as ta
from datetime import datetime, timedelta
import time
import warnings
warnings.filterwarnings("ignore")

try:
    from colorama import Fore, Style, init
    init(autoreset=True)
    GREEN  = Fore.GREEN
    RED    = Fore.RED
    YELLOW = Fore.YELLOW
    CYAN   = Fore.CYAN
    BOLD   = Style.BRIGHT
    RESET  = Style.RESET_ALL
except ImportError:
    GREEN = RED = YELLOW = CYAN = BOLD = RESET = ""


# ─────────────────────────────────────────────
#  STOCK UNIVERSE — Nifty 100 + Midcap 150
#  Format: Yahoo Finance NSE symbols (.NS suffix)
# ─────────────────────────────────────────────

from nifty500 import get_nifty500_symbols

ALL_STOCKS = get_nifty500_symbols()


# ─────────────────────────────────────────────
#  SECTOR MAP — for max 3/sector rule
# ─────────────────────────────────────────────

SECTOR_MAP = {
    "Banking":     ["HDFCBANK.NS","ICICIBANK.NS","KOTAKBANK.NS","AXISBANK.NS","SBIN.NS",
                    "INDUSINDBK.NS","BANDHANBNK.NS","FEDERALBNK.NS","IDFCFIRSTB.NS",
                    "AUBANK.NS","KARURVYSYA.NS","PNB.NS","BANKBARODA.NS","CANBK.NS",
                    "INDIANB.NS","YESBANK.NS","UNIONBANK.NS","UCOBANK.NS"],
    "IT":          ["TCS.NS","INFY.NS","WIPRO.NS","HCLTECH.NS","TECHM.NS","LTIM.NS",
                    "MPHASIS.NS","COFORGE.NS","PERSISTENT.NS","KPITTECH.NS",
                    "TATAELXSI.NS","LTTS.NS","CYIENT.NS","ZENSARTECH.NS","OFSS.NS"],
    "Finance":     ["BAJFINANCE.NS","BAJAJFINSV.NS","MUTHOOTFIN.NS","CHOLAFIN.NS",
                    "ABCAPITAL.NS","MOTILALOFS.NS","CANFINHOME.NS","LICHSGFIN.NS",
                    "HDFCLIFE.NS","SBILIFE.NS","MFSL.NS","STARHEALTH.NS",
                    "NAM-INDIA.NS","CAMS.NS","MCX.NS","IEX.NS"],
    "Pharma":      ["SUNPHARMA.NS","DRREDDY.NS","CIPLA.NS","DIVISLAB.NS","LUPIN.NS",
                    "BIOCON.NS","AUROPHARMA.NS","GLENMARK.NS","TORNTPHARM.NS",
                    "GRANULES.NS","LAURUSLABS.NS","LALPATHLAB.NS","METROPOLIS.NS",
                    "THYROCARE.NS","SYNGENE.NS","PFIZER.NS","NAVINFLUOR.NS"],
    "Auto":        ["MARUTI.NS","TATAMOTORS.NS","M&M.NS","EICHERMOT.NS","HEROMOTOCO.NS",
                    "BAJAJ-AUTO.NS","TVSMOTOR.NS","TVSHLTD.NS","BHARATFORG.NS",
                    "BALKRISIND.NS","SONACOMS.NS","TIINDIA.NS","UNOMINDA.NS"],
    "FMCG":        ["HINDUNILVR.NS","ITC.NS","NESTLEIND.NS","BRITANNIA.NS","DABUR.NS",
                    "MARICO.NS","GODREJCP.NS","COLPAL.NS","EMAMILTD.NS","UBL.NS",
                    "RADICO.NS","TATACONSUM.NS","PATANJALI.NS","VBL.NS","BIKAJI.NS"],
    "Energy":      ["RELIANCE.NS","ONGC.NS","BPCL.NS","IOC.NS","COALINDIA.NS",
                    "NTPC.NS","POWERGRID.NS","TATAPOWER.NS","JSWENERGY.NS",
                    "ADANIENT.NS","ADANIPORTS.NS","PETRONET.NS","OIL.NS",
                    "GSPL.NS","MRPL.NS","TORNTPOWER.NS","CESC.NS","MGL.NS"],
    "Metals":      ["TATASTEEL.NS","JSWSTEEL.NS","HINDALCO.NS","VEDL.NS","SAIL.NS",
                    "NATIONALUM.NS","NMDC.NS","WELCORP.NS","APLAPOLLO.NS"],
    "Infra":       ["LT.NS","ADANIPORTS.NS","GMRINFRA.NS","NCC.NS","KEC.NS",
                    "ENGINERSIN.NS","NBCC.NS","RITES.NS","RAILTEL.NS",
                    "BEL.NS","BHEL.NS","CGPOWER.NS"],
    "Cement":      ["ULTRACEMCO.NS","SHREECEM.NS","AMBUJACEM.NS","DALBHARAT.NS",
                    "JKCEMENT.NS","RAMCOCEM.NS"],
    "Consumer":    ["ASIANPAINT.NS","TITAN.NS","BERGEPAINT.NS","HAVELLS.NS",
                    "VOLTAS.NS","CROMPTON.NS","BLUESTARCO.NS","WHIRLPOOL.NS",
                    "PIDILITIND.NS","KANSAINER.NS","NILKAMAL.NS","SUPREMEIND.NS"],
    "Realty":      ["DLF.NS","GODREJPROP.NS","OBEROIRLTY.NS","PRESTIGE.NS",
                    "SOBHA.NS","PHOENIXLTD.NS"],
    "Healthcare":  ["APOLLOHOSP.NS","MAXHEALTH.NS","INDHOTEL.NS"],
    "Internet":    ["ZOMATO.NS","NAUKRI.NS","INDIAMART.NS","PAYTM.NS",
                    "NYKAA.NS","POLICYBZR.NS","DMART.NS"],
    "Chemicals":   ["UPL.NS","SRF.NS","DEEPAKNTR.NS","ATUL.NS","GNFC.NS",
                    "VINATIORGA.NS","NAVINFLUOR.NS","RAJESHEXPO.NS"],
    "Telecom":     ["BHARTIARTL.NS","TATACOMM.NS","HFCL.NS","RAILTEL.NS","TTML.NS"],
    "Diversified": ["SIEMENS.NS","BOSCHLTD.NS","ABB.NS","HONAUT.NS","SCHAEFFLER.NS",
                    "TIMKEN.NS","SKFINDIA.NS","ELGIEQUIP.NS","CUMMINSIND.NS"],
}

def get_sector(symbol):
    for sector, stocks in SECTOR_MAP.items():
        if symbol in stocks:
            return sector
    return "Other"


# ─────────────────────────────────────────────
#  CORE FUNCTIONS
# ─────────────────────────────────────────────

def fetch_data(symbol, period="6mo"):
    """Download OHLCV data for a stock."""
    try:
        df = yf.download(symbol, period=period, auto_adjust=True, progress=False)
        if df.empty or len(df) < 55:
            return None
        # Flatten multi-index columns if present
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df[["Open","High","Low","Close","Volume"]].copy()
        df.dropna(inplace=True)
        return df
    except Exception:
        return None


def calculate_ema(df):
    """Calculate EMA 20 and EMA 50."""
    df = df.copy()
    df["EMA20"] = ta.ema(df["Close"], length=20)
    df["EMA50"] = ta.ema(df["Close"], length=50)
    return df.dropna()


def detect_signals(df, symbol):
    """
    Detect two signals:
    1. Golden Cross  — EMA20 crossed above EMA50 in last 5 days
    2. EMA20 Bounce  — Price bounced off EMA20 while EMA20 > EMA50
    """
    if df is None or len(df) < 55:
        return None

    df  = calculate_ema(df)
    if len(df) < 10:
        return None

    latest      = df.iloc[-1]
    prev        = df.iloc[-2]
    price       = round(float(latest["Close"]), 2)
    ema20       = round(float(latest["EMA20"]), 2)
    ema50       = round(float(latest["EMA50"]), 2)
    vol_today   = float(latest["Volume"])
    vol_avg20   = float(df["Volume"].tail(20).mean())
    vol_ratio   = round(vol_today / vol_avg20, 2) if vol_avg20 > 0 else 0

    # ── Signal 1: Golden Cross ──────────────────
    # EMA20 just crossed above EMA50 in last 5 candles
    golden_cross = False
    cross_days_ago = None
    for i in range(1, 6):
        if len(df) > i + 1:
            curr_row = df.iloc[-i]
            prev_row = df.iloc[-(i+1)]
            if (float(prev_row["EMA20"]) <= float(prev_row["EMA50"]) and
                float(curr_row["EMA20"]) > float(curr_row["EMA50"])):
                golden_cross = True
                cross_days_ago = i
                break

    # ── Signal 2: EMA20 Bounce ──────────────────
    # Conditions:
    # a) EMA20 > EMA50 (uptrend)
    # b) Price dipped near/below EMA20 in last 3 days then recovered
    # c) Current price above EMA20
    ema20_bounce = False
    if ema20 > ema50 and price > ema20:
        # Check if price touched EMA20 zone (within 1.5%) in last 3 days
        for i in range(2, 5):
            if len(df) > i:
                past = df.iloc[-i]
                past_low   = float(past["Low"])
                past_ema20 = float(past["EMA20"])
                touch_pct  = abs(past_low - past_ema20) / past_ema20 * 100
                if touch_pct <= 1.5:
                    ema20_bounce = True
                    break

    # ── No signal ──────────────────────────────
    if not golden_cross and not ema20_bounce:
        return None

    # ── Distance from EMAs ─────────────────────
    price_vs_ema20 = round((price - ema20) / ema20 * 100, 2)
    price_vs_ema50 = round((price - ema50) / ema50 * 100, 2)
    ema20_vs_ema50 = round((ema20 - ema50) / ema50 * 100, 2)

    # ── Simple target & SL from EMA levels ─────
    sl    = round(ema50 * 0.985, 2)   # 1.5% below EMA50
    tgt1  = round(price * 1.05, 2)    # 5% target
    tgt2  = round(price * 1.10, 2)    # 10% target
    risk  = round(((price - sl) / price) * 100, 2)

    signal_type = []
    if golden_cross:
        signal_type.append(f"Golden Cross ({cross_days_ago}d ago)")
    if ema20_bounce:
        signal_type.append("EMA20 Bounce")

    return {
        "Symbol":         symbol.replace(".NS",""),
        "Sector":         get_sector(symbol),
        "Signal":         " + ".join(signal_type),
        "Price":          price,
        "EMA20":          ema20,
        "EMA50":          ema50,
        "EMA20_vs_50":    ema20_vs_ema50,
        "Price_vs_EMA20": price_vs_ema20,
        "Vol_Ratio":      vol_ratio,
        "SL":             sl,
        "Target_5pct":    tgt1,
        "Target_10pct":   tgt2,
        "Risk_pct":       risk,
    }


def apply_sector_cap(results, max_per_sector=3):
    """Keep max 3 stocks per sector, prioritising Golden Cross > EMA20 Bounce."""
    sector_count = {}
    final = []
    # Priority: Golden Cross first
    sorted_results = sorted(
        results,
        key=lambda x: (0 if "Golden Cross" in x["Signal"] else 1, x["Risk_pct"])
    )
    for r in sorted_results:
        sec = r["Sector"]
        count = sector_count.get(sec, 0)
        if count < max_per_sector:
            final.append(r)
            sector_count[sec] = count + 1
    return final


def print_results(results):
    """Print a clean formatted table."""
    if not results:
        print(f"\n{RED}No signals found today. Market may be consolidating.{RESET}")
        return

    print(f"\n{BOLD}{CYAN}{'─'*100}{RESET}")
    print(f"{BOLD}{CYAN}  {'SYMBOL':<12} {'SECTOR':<14} {'SIGNAL':<28} {'PRICE':>7} {'EMA20':>7} {'EMA50':>7} {'SL':>7} {'TGT5%':>8} {'VOL':>6}{RESET}")
    print(f"{BOLD}{CYAN}{'─'*100}{RESET}")

    for r in results:
        signal_color = GREEN if "Golden Cross" in r["Signal"] else YELLOW
        vol_flag = f"{YELLOW}↑{RESET}" if r["Vol_Ratio"] >= 1.5 else " "
        print(
            f"  {BOLD}{r['Symbol']:<12}{RESET}"
            f"{r['Sector']:<14}"
            f"{signal_color}{r['Signal']:<28}{RESET}"
            f"{r['Price']:>8.2f}"
            f"{r['EMA20']:>8.2f}"
            f"{r['EMA50']:>8.2f}"
            f"{RED}{r['SL']:>8.2f}{RESET}"
            f"{GREEN}{r['Target_5pct']:>9.2f}{RESET}"
            f"  {r['Vol_Ratio']:>4.1f}x{vol_flag}"
        )

    print(f"{BOLD}{CYAN}{'─'*100}{RESET}")
    print(f"\n{BOLD}Total signals: {len(results)}{RESET}")
    print(f"{GREEN}● Golden Cross{RESET} = Fresh trend change — strongest signal")
    print(f"{YELLOW}● EMA20 Bounce{RESET} = Trend continuation — good risk/reward")
    print(f"↑ Vol ratio ≥ 1.5x = Volume confirming the move\n")


def save_to_csv(results, filename=None):
    """Save results to CSV."""
    if not results:
        return
    if filename is None:
        filename = f"ema_scan_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    df = pd.DataFrame(results)
    df.to_csv(filename, index=False)
    print(f"{GREEN}✓ Results saved to: {filename}{RESET}")


# ─────────────────────────────────────────────
#  MAIN SCANNER
# ─────────────────────────────────────────────

def run_scanner(stocks=None, save_csv=True, max_per_sector=3):
    if stocks is None:
        stocks = ALL_STOCKS

    print(f"\n{BOLD}{'='*60}")
    print(f"  INDIAN STOCK EMA 20/50 SCANNER")
    print(f"  {datetime.now().strftime('%A, %d %B %Y  %H:%M')}")
    print(f"  Scanning {len(stocks)} stocks...")
    print(f"{'='*60}{RESET}\n")

    results  = []
    errors   = []
    total    = len(stocks)

    for i, symbol in enumerate(stocks, 1):
        name = symbol.replace(".NS","")
        print(f"  [{i:>3}/{total}] Scanning {name:<15}", end="\r")

        df = fetch_data(symbol)
        signal = detect_signals(df, symbol)

        if signal:
            results.append(signal)
            print(f"  [{i:>3}/{total}] {GREEN}✓ Signal found: {name} — {signal['Signal']}{RESET}          ")

        # Polite delay to avoid rate limiting
        time.sleep(0.3)

    print(f"\n  Scan complete. {len(results)} signals found from {total} stocks.\n")

    # Apply sector cap
    results = apply_sector_cap(results, max_per_sector)
    print(f"  After sector cap (max {max_per_sector}/sector): {len(results)} stocks in watchlist.\n")

    # Print results
    print_results(results)

    # Save
    if save_csv and results:
        save_to_csv(results)

    return results


# ─────────────────────────────────────────────
#  QUICK SCAN — test specific stocks
# ─────────────────────────────────────────────

def quick_scan(symbols):
    """
    Scan just a few stocks quickly.
    Usage: quick_scan(["RELIANCE", "TCS", "HDFCBANK"])
    """
    symbols_ns = [s if s.endswith(".NS") else s + ".NS" for s in symbols]
    print(f"\n{BOLD}Quick scan: {', '.join(symbols)}{RESET}")
    results = []
    for symbol in symbols_ns:
        df = fetch_data(symbol)
        signal = detect_signals(df, symbol)
        if signal:
            results.append(signal)
    print_results(results)
    return results


# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        # Quick mode: python indian_ema_scanner.py RELIANCE TCS HDFCBANK
        stocks = sys.argv[1:]
        quick_scan(stocks)
    else:
        # Full scan mode
        run_scanner(
            stocks=ALL_STOCKS,
            save_csv=True,
            max_per_sector=3
        )