"""
============================================================
  GURU EDGE — INDIAN STOCK SCANNER
  EMA 20/50 + RSI + 7 TRENDLINES + FIBONACCI + FUNDAMENTALS

  FULL PIPELINE:
    Layer 1 — EMA signals       (ema_signals.py)
    Layer 2 — RSI filter        (rsi_filter.py)
    Layer 3 — Trendline filter  (trendline_signals.py)
    Layer 4 — Fibonacci signals (fibonacci_signals.py)
    Layer 5 — Fundamentals      (fundamental_signals.py)
    Layer 6 — LLM analysis      (llm_analysis.py)

  FINAL GRADING:
    Technical:   C → B → A → A+ → A++
    Fundamental: GREEN / YELLOW / RED

    Combined:
      A++ + GREEN  = A++  ← Trade first
      A++ + YELLOW = A+
      A++ + RED    = SKIP
      A+  + GREEN  = A+
      A+  + YELLOW = A
      A+  + RED    = SKIP
      A   + GREEN  = A
      A   + YELLOW = B
      A   + RED    = SKIP
      B   + RED    = SKIP
      C   + any    = SKIP

  RUN:
    python main_scanner.py                    (full scan with fundamentals)
    python main_scanner.py --no-fundamentals  (technical only — faster)
    python main_scanner.py RELIANCE TCS       (quick scan)

  SETUP:
    pip install yfinance pandas pandas-ta colorama requests beautifulsoup4 feedparser
============================================================
"""

import sys
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
import time
import warnings
warnings.filterwarnings("ignore")

from datetime import datetime

# ── Import all modules ───────────────────────────────────
from stock_universe    import get_all_stocks
from sector_map        import get_sector, apply_sector_cap
from utils             import (fetch_data, print_results, save_to_csv,
                                GRADE_COLOR, BOLD, DIM, RESET,
                                CYAN, GREEN, RED, YELLOW, MAGENTA)
from ema_signals       import detect_ema_signals, calculate_emas
from rsi_filter        import grade_rsi
from trendline_signals import (detect_trendline_scenarios,
                                is_trendline_rejected,
                                trendline_signal_count)
from fibonacci_signals import detect_fib_signals
from fundamental_signals import (analyse_fundamentals,
                                  apply_fundamental_to_grade,
                                  reset_fii_cache)
from llm_analysis      import llm_analyse_stock, combine_verdicts

# ── Grade ladder ─────────────────────────────────────────
GRADE_LADDER = ["C", "B", "A", "A+", "A++"]

# ── Fund grade colors ────────────────────────────────────
FUND_COLOR = {
    "GREEN":  GREEN + BOLD,
    "YELLOW": YELLOW,
    "RED":    RED + BOLD,
}


def compute_technical_grade(rsi_grade, golden_cross,
                              ema20_bounce, tl_count, fib_boost):
    """Combine EMA + RSI + Trendline + Fib into technical grade."""
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

    idx      = GRADE_LADDER.index(base) if base in GRADE_LADDER else 1
    tl_boost = min(tl_count, 2)
    idx      = min(idx + tl_boost,  len(GRADE_LADDER) - 1)
    idx      = min(idx + fib_boost, len(GRADE_LADDER) - 1)

    return GRADE_LADDER[idx]


def detect_technical_signals(df, symbol):
    """
    Run technical layers 1-4 on one stock.
    Returns partial signal dict or None.
    """
    if df is None or len(df) < 55:
        return None

    # Layer 1 — EMA
    ema = detect_ema_signals(df)
    if not ema["golden_cross"] and not ema["ema20_bounce"]:
        return None
    if ema["suspicious_vol"] and True:
        pass  # RSI will handle this below

    df_ema = calculate_emas(df)

    # Layer 2 — RSI
    rsi_grade, rsi_now, rsi_3d, rsi_slope, rsi_note = grade_rsi(df)
    if rsi_grade == "FAIL":
        return None
    if ema["suspicious_vol"] and rsi_now and rsi_now > 65:
        return None

    # Layer 3 — Trendlines
    tl = detect_trendline_scenarios(df)
    if is_trendline_rejected(tl):
        return None
    tl_signals = tl["trendline_signals"]
    tl_count   = trendline_signal_count(tl)

    # Layer 4 — Fibonacci
    fib = detect_fib_signals(df, ema20=ema["ema20"], ema50=ema["ema50"])
    if fib.get("fib_fail"):
        return None
    fib_boost = fib.get("fib_grade_boost", 0)

    # Technical grade
    tech_grade = compute_technical_grade(
        rsi_grade    = rsi_grade,
        golden_cross = ema["golden_cross"],
        ema20_bounce = ema["ema20_bounce"],
        tl_count     = tl_count,
        fib_boost    = fib_boost,
    )

    # Trade levels
    price = round(float(df["Close"].iloc[-1]), 2)
    ema20 = ema["ema20"]
    ema50 = ema["ema50"]
    sl    = fib["fib_sl"] if fib["fib_sl"] > 0 else round(ema50 * 0.985, 2)
    tgt1  = fib["fib_target1"] if fib["fib_target1"] > price else round(price * 1.05, 2)
    tgt2  = fib["fib_target2"] if fib["fib_target2"] > tgt1  else round(price * 1.10, 2)
    risk  = round(((price - sl) / price) * 100, 2) if price > sl else 0
    rr    = round((tgt1 - price) / (price - sl), 2) if price > sl else 0

    return {
        "tech_grade":      tech_grade,
        "Symbol":          symbol.replace(".NS", ""),
        "Sector":          get_sector(symbol),
        "EMA_Signal":      ema["ema_signal"],
        "EMA20":           ema20,
        "EMA50":           ema50,
        "RSI_Now":         rsi_now,
        "RSI_Slope":       rsi_slope,
        "RSI_Note":        rsi_note,
        "TL_Count":        tl_count,
        "TL_Signals":      " | ".join(tl_signals) if tl_signals else "None",
        "Fib_Level":       fib.get("fib_level", "-"),
        "Fib_Signal":      fib.get("fib_signal", "None"),
        "Fib_Confluence":  fib.get("fib_confluence", False),
        "Fib_Golden_Zone": fib.get("fib_golden_zone", False),
        "Price":           price,
        "SL":              sl,
        "Target_5pct":     tgt1,
        "Target_10pct":    tgt2,
        "Risk_pct":        risk,
        "RR_Ratio":        rr,
        "Vol_Ratio":       ema["vol_ratio"],
        "Suspicious_Vol":  ema["suspicious_vol"],
    }


def run_scanner(stocks=None, use_fundamentals=True,
                use_llm=True, save_csv=True, max_per_sector=3):
    """
    Full scanner pipeline.

    Args:
        stocks           : list of symbols (None = all stocks)
        use_fundamentals : run fundamental layer (slower but safer)
        use_llm          : run LLM analysis (requires API)
        save_csv         : save results to CSV
        max_per_sector   : max stocks per sector in watchlist
    """
    if stocks is None:
        stocks = get_all_stocks()

    reset_fii_cache()

    print(f"\n{BOLD}{'='*70}")
    print(f"  GURU EDGE — INDIAN STOCK SCANNER")
    print(f"  {datetime.now().strftime('%A, %d %B %Y  %H:%M')}")
    print(f"  Universe     : {len(stocks)} stocks")
    print(f"  Layers       : EMA → RSI → Trendlines → Fibonacci")
    if use_fundamentals:
        print(f"               + Fundamentals → {'LLM' if use_llm else 'Rule-based'}")
    print(f"{'='*70}{RESET}\n")

    # ── Phase 1: Technical scan ───────────────────────────
    print(f"{BOLD}  PHASE 1 — TECHNICAL SCAN{RESET}")
    print(f"{DIM}  {'─'*50}{RESET}\n")

    tech_signals = []
    total        = len(stocks)

    for i, symbol in enumerate(stocks, 1):
        name = symbol.replace(".NS", "")
        print(f"  [{i:>3}/{total}] Scanning {name:<15}", end="\r")

        df     = fetch_data(symbol)
        signal = detect_technical_signals(df, symbol)

        if signal:
            tech_signals.append(signal)
            gc = GRADE_COLOR.get(signal["tech_grade"], "")
            print(
                f"  [{i:>3}/{total}] {gc}{signal['tech_grade']:<4}{RESET} "
                f"{name:<12} {signal['EMA_Signal']:<20} "
                f"RSI:{signal['RSI_Now']}  "
                f"{CYAN}TL:{signal['TL_Count']} FIB:{signal['Fib_Level']}{RESET}   "
            )

        time.sleep(0.3)

    print(f"\n\n  Technical scan complete.")
    print(f"  Signals found    : {len(tech_signals)}")

    # Sector cap on technical signals
    tech_final = apply_sector_cap(tech_signals, max_per_sector)
    print(f"  After sector cap : {len(tech_final)} stocks\n")

    if not use_fundamentals:
        # Technical only mode
        for s in tech_final:
            s["Grade"]        = s["tech_grade"]
            s["Fund_Grade"]   = "N/A"
            s["Fund_Summary"] = "Fundamental check skipped"
            s["LLM_Verdict"]  = "N/A"
        print_results(tech_final)
        if save_csv:
            save_to_csv(tech_final)
        return tech_final

    # ── Phase 2: Fundamental analysis ─────────────────────
    print(f"{BOLD}  PHASE 2 — FUNDAMENTAL ANALYSIS{RESET}")
    print(f"{DIM}  {'─'*50}{RESET}\n")
    print(f"  Analysing {len(tech_final)} stocks from technical shortlist...\n")

    final_results = []

    for i, signal in enumerate(tech_final, 1):
        symbol_ns = signal["Symbol"] + ".NS"
        name      = signal["Symbol"]
        sector    = signal["Sector"]

        print(f"  [{i:>2}/{len(tech_final)}] {name:<12}", end=" ")

        # Fetch fundamental data
        fund = analyse_fundamentals(symbol_ns, verbose=False)

        # LLM analysis
        llm = {"llm_verdict": fund["fund_grade"],
               "llm_key_risk": "N/A",
               "llm_key_strength": "N/A",
               "llm_reasoning": "LLM skipped",
               "llm_ok": False}

        if use_llm:
            llm = llm_analyse_stock(name, sector, fund)
            time.sleep(0.5)  # rate limit courtesy

        # Combine rule-based + LLM verdict
        final_fund_grade = combine_verdicts(
            rule_grade     = fund["fund_grade"],
            llm_verdict    = llm["llm_verdict"],
            llm_confidence = llm.get("llm_confidence", "low"),
        )

        # Apply fundamental to technical grade
        final_grade = apply_fundamental_to_grade(
            signal["tech_grade"], final_fund_grade
        )

        fc = FUND_COLOR.get(final_fund_grade, "")
        gc = GRADE_COLOR.get(final_grade, "")

        if final_grade == "SKIP":
            print(
                f"{RED}SKIP{RESET}  "
                f"Fund:{fc}{final_fund_grade}{RESET}  "
                f"{DIM}{fund['fund_summary'][:50]}{RESET}"
            )
            continue

        print(
            f"{gc}{final_grade:<4}{RESET}  "
            f"Fund:{fc}{final_fund_grade}{RESET}  "
            f"{DIM}{fund['fund_summary'][:55]}{RESET}"
        )

        # Build complete result
        complete = {**signal}
        complete.update({
            "Grade":           final_grade,
            "Tech_Grade":      signal["tech_grade"],
            "Fund_Grade":      final_fund_grade,
            "Fund_Score":      fund["fund_score"],
            "Fund_Summary":    fund["fund_summary"],
            "Fund_Red_Flags":  "; ".join(fund["red_flags"])   if fund["red_flags"]   else "None",
            "Fund_Yellow":     "; ".join(fund["yellow_flags"]) if fund["yellow_flags"] else "None",
            "Fund_Green":      "; ".join(fund["green_flags"])  if fund["green_flags"]  else "None",
            "PE_Ratio":        fund["pe_ratio"],
            "Debt_Equity":     fund["debt_to_equity"],
            "Promoter_Pct":    fund["promoter"],
            "Pledge_Pct":      fund["pledge"],
            "ROE":             fund["roe"],
            "FII_Trend":       fund["fii_trend"],
            "LLM_Verdict":     llm["llm_verdict"],
            "LLM_Key_Risk":    llm["llm_key_risk"],
            "LLM_Strength":    llm["llm_key_strength"],
            "LLM_Reasoning":   llm["llm_reasoning"],
            "LLM_OK":          llm["llm_ok"],
            "News_Headlines":  " | ".join(fund["headlines"][:3]) if fund["headlines"] else "None",
        })
        final_results.append(complete)

    # Final sort by grade
    final_results = sorted(
        final_results,
        key=lambda x: (
            ["A++","A+","A","B","C"].index(x["Grade"])
            if x["Grade"] in ["A++","A+","A","B","C"] else 9
        )
    )

    print(f"\n  Fundamental analysis complete.")
    print(f"  Final watchlist  : {len(final_results)} stocks\n")

    # Print results
    print_results(final_results)

    # Print detailed fundamental summary
    print_fundamental_summary(final_results)

    if save_csv and final_results:
        save_to_csv(final_results)

    # Grade summary
    grades = {"A++": 0, "A+": 0, "A": 0, "B": 0, "C": 0}
    for r in final_results:
        grades[r["Grade"]] = grades.get(r["Grade"], 0) + 1

    print(f"\n{BOLD}  FINAL GRADE SUMMARY:{RESET}")
    print(f"  {MAGENTA+BOLD}A++ : {grades['A++']} stocks{RESET}  ← Trade first")
    print(f"  {GREEN+BOLD}A+  : {grades['A+']} stocks{RESET}  ← Strong entries")
    print(f"  {GREEN}A   : {grades['A']} stocks{RESET}  ← Good entries")
    print(f"  {YELLOW}B   : {grades['B']} stocks{RESET}  ← Half position")
    print(f"  {RED}C   : {grades['C']} stocks{RESET}  ← Skip\n")

    return final_results


def print_fundamental_summary(results):
    """Print detailed fundamental breakdown for each stock."""
    if not results:
        return

    print(f"\n{BOLD}{CYAN}{'═'*80}")
    print(f"  FUNDAMENTAL DETAILS")
    print(f"{'═'*80}{RESET}\n")

    for r in results:
        gc = GRADE_COLOR.get(r["Grade"], "")
        fc = FUND_COLOR.get(r.get("Fund_Grade", "YELLOW"), "")

        print(f"  {gc}{BOLD}{r['Symbol']:<12}{RESET} "
              f"Grade:{gc}{r['Grade']}{RESET}  "
              f"Fund:{fc}{r.get('Fund_Grade','?')}{RESET}  "
              f"PE:{r.get('PE_Ratio','N/A')}  "
              f"D/E:{r.get('Debt_Equity','N/A')}  "
              f"ROE:{r.get('ROE','N/A')}%  "
              f"Promoter:{r.get('Promoter_Pct','N/A')}%  "
              f"Pledge:{r.get('Pledge_Pct','N/A')}%  "
              f"FII:{r.get('FII_Trend','?')}")

        if r.get("Fund_Red_Flags") and r["Fund_Red_Flags"] != "None":
            print(f"    {RED}⚠ {r['Fund_Red_Flags']}{RESET}")

        if r.get("LLM_Reasoning") and r.get("LLM_OK"):
            print(f"    {DIM}LLM: {r['LLM_Reasoning'][:80]}{RESET}")

        print()


# ── Quick Scan ───────────────────────────────────────────

def quick_scan(symbols, use_fundamentals=True, use_llm=True):
    """Scan a specific list of stocks."""
    symbols_ns = [s if s.endswith(".NS") else s + ".NS" for s in symbols]
    print(f"\n{BOLD}GURU EDGE — Quick Scan: {', '.join(symbols)}{RESET}\n")
    return run_scanner(
        stocks           = symbols_ns,
        use_fundamentals = use_fundamentals,
        use_llm          = use_llm,
        save_csv         = True,
        max_per_sector   = 3,
    )


# ── Entry Point ──────────────────────────────────────────

if __name__ == "__main__":
    args = sys.argv[1:]

    # Flag check
    no_fundamentals = "--no-fundamentals" in args
    no_llm          = "--no-llm" in args
    args            = [a for a in args if not a.startswith("--")]

    use_fund = not no_fundamentals
    use_llm  = not no_llm and use_fund

    if args:
        quick_scan(args, use_fundamentals=use_fund, use_llm=use_llm)
    else:
        run_scanner(
            use_fundamentals = use_fund,
            use_llm          = use_llm,
            save_csv         = True,
            max_per_sector   = 3,
        )
