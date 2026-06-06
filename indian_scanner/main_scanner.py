"""
============================================================
  INDIAN STOCK SCANNER — MAIN
  EMA 20/50 + RSI + 7 TRENDLINES + FIBONACCI

  PIPELINE:
    1. Fetch OHLCV data (utils)
    2. EMA signals — Golden Cross / EMA20 Bounce (ema_signals)
    3. RSI filter — Grade A/B/C/FAIL (rsi_filter)
    4. Trendline rejection — T1 downtrend / T2 bull trap (trendline_signals)
    5. Trendline signals — T3–T7 grade boosters (trendline_signals)
    6. Fibonacci signals — level detection + confluence (fibonacci_signals)
    7. Combined grading — A++ / A+ / A / B / C
    8. Sector cap — max 3 per sector (sector_map)
    9. Output — terminal + CSV (utils)

  GRADING SYSTEM:
    Base (EMA + RSI):
      Golden Cross + RSI A  = A
      Golden Cross + RSI B  = B
      EMA Bounce   + RSI A  = B
      EMA Bounce   + RSI B  = B
      Any          + RSI C  = C

    Trendline boosts (+1 per signal, max +2):
      T3 Uptrend HH+HL      → +1
      T4 Third touch        → +1
      T5 Bullish rejection  → +1
      T6 Closing breakout   → +1
      T7 Breakout retest    → +1

    Fibonacci boosts (max +2):
      At Fib level          → +1
      Golden zone 61.8–78.6 → +1 extra
      EMA confluence        → +1 extra

    Grade ladder: C → B → A → A+ → A++

  RUN:
    python main_scanner.py               (full scan)
    python main_scanner.py RELIANCE TCS  (quick scan)

  SETUP:
    pip install yfinance pandas pandas-ta colorama
============================================================
"""

import sys
import time
import warnings
warnings.filterwarnings("ignore")

from datetime import datetime

# ── Import all modules ───────────────────────────────────
from stock_universe   import get_all_stocks
from sector_map       import get_sector, apply_sector_cap
from utils            import fetch_data, print_results, save_to_csv, GRADE_COLOR, BOLD, DIM, RESET, CYAN, GREEN, RED, YELLOW, MAGENTA
from ema_signals      import detect_ema_signals, calculate_emas
from rsi_filter       import grade_rsi
from trendline_signals import detect_trendline_scenarios, is_trendline_rejected, trendline_signal_count
from fibonacci_signals import detect_fib_signals


# ── Grade ladder ─────────────────────────────────────────
GRADE_LADDER = ["C", "B", "A", "A+", "A++"]


def compute_final_grade(rsi_grade, golden_cross, ema20_bounce,
                        tl_count, fib_boost):
    """
    Combine EMA + RSI + Trendline + Fibonacci into one final grade.
    """
    # Base grade from EMA + RSI
    if rsi_grade == "C":
        base = "C"
    elif golden_cross and rsi_grade == "A":
        base = "A"
    elif golden_cross and rsi_grade == "B":
        base = "B"
    elif ema20_bounce and rsi_grade == "A":
        base = "B"
    else:
        base = "B"

    idx = GRADE_LADDER.index(base) if base in GRADE_LADDER else 1

    # Trendline boosts — cap at +2 from trendlines
    tl_boost = min(tl_count, 2)
    idx = min(idx + tl_boost, len(GRADE_LADDER) - 1)

    # Fibonacci boosts — cap at +2 from Fibonacci
    idx = min(idx + fib_boost, len(GRADE_LADDER) - 1)

    return GRADE_LADDER[idx]


def detect_signals(df, symbol):
    """
    Master signal detection — runs all 4 layers on one stock.
    Returns signal dict or None if no valid signal.
    """
    if df is None or len(df) < 55:
        return None

    # ── Layer 1: EMA signals ─────────────────────────────
    ema = detect_ema_signals(df)

    # No EMA signal = skip immediately
    if not ema["golden_cross"] and not ema["ema20_bounce"]:
        return None

    # Suspicious volume + high RSI = operator pump, skip
    if ema["suspicious_vol"]:
        pass  # RSI check below will handle this

    # Need EMA data in df for Fibonacci confluence check
    df_ema = calculate_emas(df)

    # ── Layer 2: RSI filter ──────────────────────────────
    rsi_grade, rsi_now, rsi_3d, rsi_slope, rsi_note = grade_rsi(df)

    if rsi_grade == "FAIL":
        return None

    # Suspicious volume + high RSI = skip
    if ema["suspicious_vol"] and rsi_now and rsi_now > 65:
        return None

    # ── Layer 3: Trendline scenarios ─────────────────────
    tl = detect_trendline_scenarios(df)

    # Hard rejection — downtrend or bull trap
    if is_trendline_rejected(tl):
        return None

    tl_signals = tl["trendline_signals"]
    tl_count   = trendline_signal_count(tl)

    # ── Layer 4: Fibonacci signals ───────────────────────
    fib = detect_fib_signals(df, ema20=ema["ema20"], ema50=ema["ema50"])

    # If Fibonacci detects a trend failure — hard skip
    if fib.get("fib_fail"):
        return None

    fib_boost = fib.get("fib_grade_boost", 0)

    # ── Combined grade ───────────────────────────────────
    final_grade = compute_final_grade(
        rsi_grade    = rsi_grade,
        golden_cross = ema["golden_cross"],
        ema20_bounce = ema["ema20_bounce"],
        tl_count     = tl_count,
        fib_boost    = fib_boost,
    )

    # ── Trade levels ─────────────────────────────────────
    price = round(float(df["Close"].iloc[-1]), 2)
    ema20 = ema["ema20"]
    ema50 = ema["ema50"]

    # SL: use Fib SL if available, else EMA50-based
    sl = fib["fib_sl"] if fib["fib_sl"] > 0 else round(ema50 * 0.985, 2)

    # Targets: use Fib targets if available, else % based
    tgt1 = fib["fib_target1"] if fib["fib_target1"] > price else round(price * 1.05, 2)
    tgt2 = fib["fib_target2"] if fib["fib_target2"] > tgt1  else round(price * 1.10, 2)

    risk = round(((price - sl) / price) * 100, 2) if price > sl else 0
    rr   = round((tgt1 - price) / (price - sl), 2) if price > sl else 0

    return {
        # Identity
        "Grade":           final_grade,
        "Symbol":          symbol.replace(".NS", ""),
        "Sector":          get_sector(symbol),

        # EMA
        "EMA_Signal":      ema["ema_signal"],
        "EMA20":           ema20,
        "EMA50":           ema50,

        # RSI
        "RSI_Now":         rsi_now,
        "RSI_Slope":       rsi_slope,
        "RSI_Note":        rsi_note,

        # Trendlines
        "TL_Count":        tl_count,
        "TL_Signals":      " | ".join(tl_signals) if tl_signals else "None",

        # Fibonacci
        "Fib_Level":       fib.get("fib_level", "-"),
        "Fib_Signal":      fib.get("fib_signal", "None"),
        "Fib_Confluence":  fib.get("fib_confluence", False),
        "Fib_Golden_Zone": fib.get("fib_golden_zone", False),
        "Fib_SL":          fib.get("fib_sl", 0),
        "Fib_Target1":     fib.get("fib_target1", 0),
        "Fib_Ext_161":     fib.get("fib_ext_161", 0),

        # Levels
        "Price":           price,
        "SL":              sl,
        "Target_5pct":     tgt1,
        "Target_10pct":    tgt2,
        "Risk_pct":        risk,
        "RR_Ratio":        rr,

        # Volume
        "Vol_Ratio":       ema["vol_ratio"],
        "Suspicious_Vol":  ema["suspicious_vol"],
    }


# ── Full Scanner ─────────────────────────────────────────

def run_scanner(stocks=None, save_csv=True, max_per_sector=3):
    if stocks is None:
        stocks = get_all_stocks()

    print(f"\n{BOLD}{'='*70}")
    print(f"  INDIAN STOCK SCANNER")
    print(f"  EMA 20/50 + RSI + 7 TRENDLINES + FIBONACCI")
    print(f"  {datetime.now().strftime('%A, %d %B %Y  %H:%M')}")
    print(f"  Universe : {len(stocks)} stocks")
    print(f"  Pipeline : EMA → RSI → Trendlines → Fibonacci → Grade")
    print(f"{'='*70}{RESET}\n")

    raw_signals = []
    total       = len(stocks)

    for i, symbol in enumerate(stocks, 1):
        name = symbol.replace(".NS", "")
        print(f"  [{i:>3}/{total}] Scanning {name:<15}", end="\r")

        df     = fetch_data(symbol)
        signal = detect_signals(df, symbol)

        if signal:
            raw_signals.append(signal)
            gc      = GRADE_COLOR.get(signal["Grade"], "")
            tl_info = f"TL:{signal['TL_Count']}" if signal["TL_Count"] > 0 else ""
            fib_info= f"FIB:{signal['Fib_Level']}" if signal["Fib_Level"] != "-" else ""
            extras  = "  ".join(filter(None, [tl_info, fib_info]))
            print(
                f"  [{i:>3}/{total}] {gc}{signal['Grade']:<4}{RESET} "
                f"{name:<12} {signal['EMA_Signal']:<20} "
                f"RSI:{signal['RSI_Now']}  {CYAN}{extras}{RESET}   "
            )

        time.sleep(0.3)

    print(f"\n\n  Scan complete.")
    print(f"  Signals found    : {len(raw_signals)}")

    final = apply_sector_cap(raw_signals, max_per_sector)
    print(f"  After sector cap : {len(final)} stocks\n")

    print_results(final)

    if save_csv and final:
        save_to_csv(final)

    # Grade summary
    grades = {"A++": 0, "A+": 0, "A": 0, "B": 0, "C": 0}
    for r in final:
        grades[r["Grade"]] = grades.get(r["Grade"], 0) + 1

    print(f"\n{BOLD}  GRADE SUMMARY:{RESET}")
    print(f"  {MAGENTA+BOLD}A++ : {grades['A++']} stocks{RESET}  ← Trade first — all 4 layers confirmed")
    print(f"  {GREEN+BOLD}A+  : {grades['A+']} stocks{RESET}  ← Strong entries")
    print(f"  {GREEN}A   : {grades['A']} stocks{RESET}  ← Good entries")
    print(f"  {YELLOW}B   : {grades['B']} stocks{RESET}  ← Half position only")
    print(f"  {RED}C   : {grades['C']} stocks{RESET}  ← Skip\n")

    return final


# ── Quick Scan ───────────────────────────────────────────

def quick_scan(symbols):
    """Scan a specific list of stocks quickly."""
    symbols_ns = [s if s.endswith(".NS") else s + ".NS" for s in symbols]
    print(f"\n{BOLD}Quick scan: {', '.join(symbols)}{RESET}\n")
    results = []
    for symbol in symbols_ns:
        df     = fetch_data(symbol)
        signal = detect_signals(df, symbol)
        if signal:
            results.append(signal)
        else:
            name = symbol.replace(".NS", "")
            print(f"  {RED}✗ {name} — no signal or filtered out{RESET}")
        time.sleep(0.3)
    print_results(results)
    return results


# ── Entry Point ──────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) > 1:
        quick_scan(sys.argv[1:])
    else:
        run_scanner(save_csv=True, max_per_sector=3)
