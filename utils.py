"""
============================================================
  UTILS
  - Color setup
  - Data fetch from Yahoo Finance
  - Print results to terminal
  - Save results to CSV
============================================================
"""

import yfinance as yf
import pandas as pd
from datetime import datetime
import warnings
warnings.filterwarnings("ignore")

# ── Colors ───────────────────────────────────────────────
try:
    from colorama import Fore, Style, init
    init(autoreset=True)
    GREEN   = Fore.GREEN
    RED     = Fore.RED
    YELLOW  = Fore.YELLOW
    CYAN    = Fore.CYAN
    MAGENTA = Fore.MAGENTA
    WHITE   = Fore.WHITE
    BOLD    = Style.BRIGHT
    DIM     = Style.DIM
    RESET   = Style.RESET_ALL
except ImportError:
    GREEN = RED = YELLOW = CYAN = MAGENTA = WHITE = BOLD = DIM = RESET = ""

GRADE_COLOR = {
    "A++": MAGENTA + BOLD,
    "A+":  GREEN   + BOLD,
    "A":   GREEN,
    "B":   YELLOW,
    "C":   RED,
}


# ── Data Fetch ───────────────────────────────────────────

def fetch_data(symbol, period="6mo"):
    """
    Download OHLCV data from Yahoo Finance for an NSE symbol.
    Returns DataFrame or None if data unavailable.
    """
    try:
        df = yf.download(symbol, period=period, auto_adjust=True, progress=False)
        if df.empty or len(df) < 55:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
        df.dropna(inplace=True)
        return df
    except Exception:
        return None


# ── Print Results ────────────────────────────────────────

def print_results(results):
    """Print final watchlist in a clean colour-coded table."""
    if not results:
        print(f"\n{RED}No signals passed all filters today.{RESET}")
        return

    aplusplus = [r for r in results if r["Grade"] == "A++"]
    aplus     = [r for r in results if r["Grade"] == "A+"]
    a         = [r for r in results if r["Grade"] == "A"]
    b         = [r for r in results if r["Grade"] == "B"]
    c         = [r for r in results if r["Grade"] == "C"]

    def print_section(title, color, stocks):
        if not stocks:
            return
        print(f"\n{color}  {title}  ({len(stocks)} stocks){RESET}")
        print(f"{DIM}  {'─'*138}{RESET}")
        print(
            f"{DIM}  {'SYMBOL':<12} {'SECTOR':<13} {'EMA':<16} {'TL':>3} "
            f"{'FIB':>4} {'RSI':>5} {'SLP':>5} {'PRICE':>9} "
            f"{'SL':>9} {'T5%':>9} {'T10%':>9} {'VOL':>5}  SIGNALS{RESET}"
        )
        print(f"{DIM}  {'─'*138}{RESET}")

        for r in stocks:
            vol_str = f"{r.get('Vol_Ratio', 0):.1f}x"
            if r.get("Suspicious_Vol"):
                vol_str = RED + vol_str + "⚠" + RESET
            elif r.get("Vol_Ratio", 0) >= 1.5:
                vol_str = YELLOW + vol_str + "↑" + RESET

            rsi_slope = r.get("RSI_Slope", 0) or 0
            slope_str = f"+{rsi_slope}" if rsi_slope > 0 else str(rsi_slope)
            rsi_str   = str(r.get("RSI_Now", "n/a"))
            tl_count  = r.get("TL_Count", 0)
            fib_level = r.get("Fib_Level", "-")
            fib_str   = fib_level if fib_level != "-" else "-"

            # Build compact signal summary
            signals = []
            if r.get("TL_Signals") and r["TL_Signals"] != "None":
                tl_short = r["TL_Signals"].split("|")[0].strip()[:25]
                signals.append(tl_short)
            if r.get("Fib_Signal") and r["Fib_Signal"] != "None":
                signals.append(r["Fib_Signal"][:30])
            signal_str = " | ".join(signals) if signals else r.get("RSI_Note","")[:35]

            print(
                f"  {color}{BOLD}{r['Symbol']:<12}{RESET}"
                f"{r.get('Sector','Other'):<13}"
                f"{r.get('EMA_Signal',''):<16}"
                f"{tl_count:>4}"
                f"{fib_str:>5}"
                f"{rsi_str:>6}"
                f"{slope_str:>6}"
                f"{r.get('Price',0):>10.2f}"
                f"{RED}{r.get('SL',0):>10.2f}{RESET}"
                f"{GREEN}{r.get('Target_5pct',0):>10.2f}{RESET}"
                f"{GREEN}{r.get('Target_10pct',0):>10.2f}{RESET}"
                f"  {vol_str:<8}"
                f"  {DIM}{signal_str}{RESET}"
            )

    print(f"\n{BOLD}{CYAN}{'═'*138}")
    print(f"  INDIAN STOCK SCANNER — EMA + RSI + TRENDLINES + FIBONACCI")
    print(f"  {datetime.now().strftime('%A, %d %B %Y  %H:%M')}")
    print(f"  Total signals: {len(results)}")
    print(f"{'═'*138}{RESET}")

    print_section("GRADE A++  —  EXCEPTIONAL   (EMA + RSI + Trendline + Fib confluence)", MAGENTA + BOLD, aplusplus)
    print_section("GRADE A+   —  STRONGEST     (EMA + RSI + strong confirmations)",       GREEN   + BOLD, aplus)
    print_section("GRADE A    —  STRONG         (Golden Cross + good RSI)",                GREEN,          a)
    print_section("GRADE B    —  MODERATE       (EMA signal + acceptable RSI)",            YELLOW,         b)
    print_section("GRADE C    —  WEAK           (RSI momentum fading — skip)",             RED,            c)

    print(f"\n{BOLD}{CYAN}{'─'*138}{RESET}")
    print(f"\n{BOLD}LEGEND:{RESET}")
    print(f"  {MAGENTA+BOLD}A++{RESET} Best possible — all 4 layers confirm")
    print(f"  {GREEN+BOLD}A+ {RESET} Strong — EMA + RSI + multiple confirmations")
    print(f"  {GREEN}A  {RESET} Good — EMA + RSI aligned")
    print(f"  {YELLOW}B  {RESET} Moderate — half position only")
    print(f"  {RED}C  {RESET} Weak — skip")
    print(f"\n  TL  = trendline signals count (T3–T7)")
    print(f"  FIB = Fibonacci level price is near (38.2 / 50.0 / 61.8 / 78.6)")
    print(f"  {YELLOW}↑{RESET}  Vol ≥ 1.5x avg = volume confirming")
    print(f"  {RED}⚠{RESET}  Vol ≥ 5.0x = suspicious — possible operator pump\n")


# ── Save to CSV ──────────────────────────────────────────

def save_to_csv(results, filename=None):
    """Save results DataFrame to CSV file."""
    if not results:
        return
    if filename is None:
        filename = f"scan_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    df_out = pd.DataFrame(results)
    cols = [
        "Grade", "Symbol", "Sector", "EMA_Signal",
        "TL_Count", "TL_Signals",
        "Fib_Level", "Fib_Signal", "Fib_Confluence",
        "RSI_Now", "RSI_Slope", "RSI_Note",
        "Price", "EMA20", "EMA50",
        "SL", "Target_5pct", "Target_10pct",
        "Risk_pct", "RR_Ratio", "Vol_Ratio",
        "Fund_Grade", "Fund_Summary", "LLM_Verdict", "LLM_Key_Risk"
    ]
    df_out = df_out[[c for c in cols if c in df_out.columns]]
    df_out.to_csv(filename, index=False)
    print(f"{GREEN}✓ Saved: {filename}{RESET}")
