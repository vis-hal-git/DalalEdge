

import yfinance as yf
import pandas as pd
import pandas_ta as ta
from datetime import datetime
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
    MAGENTA= Fore.MAGENTA
    WHITE  = Fore.WHITE
    BOLD   = Style.BRIGHT
    DIM    = Style.DIM
    RESET  = Style.RESET_ALL
except ImportError:
    GREEN = RED = YELLOW = CYAN = MAGENTA = WHITE = BOLD = DIM = RESET = ""


# ─────────────────────────────────────────────────────────
#  STOCK UNIVERSE  —  Nifty 100 + Midcap 150 (fixed symbols)
# ─────────────────────────────────────────────────────────

from nifty500 import get_nifty500_symbols

ALL_STOCKS = get_nifty500_symbols()


# ─────────────────────────────────────────────────────────
#  SECTOR MAP
# ─────────────────────────────────────────────────────────

SECTOR_MAP = {
    "Banking":     ["HDFCBANK.NS","ICICIBANK.NS","KOTAKBANK.NS","AXISBANK.NS","SBIN.NS",
                    "INDUSINDBK.NS","BANDHANBNK.NS","FEDERALBNK.NS","IDFCFIRSTB.NS",
                    "AUBANK.NS","KARURVYSYA.NS","PNB.NS","BANKBARODA.NS","CANBK.NS",
                    "INDIANB.NS","YESBANK.NS","UNIONBANK.NS","UCOBANK.NS"],
    "IT":          ["TCS.NS","INFY.NS","WIPRO.NS","HCLTECH.NS","TECHM.NS","LTIM.NS",
                    "LTIMINDTCH.NS","MPHASIS.NS","COFORGE.NS","PERSISTENT.NS",
                    "KPITTECH.NS","TATAELXSI.NS","LTTS.NS","CYIENT.NS","ZENSARTECH.NS","OFSS.NS"],
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
                    "PETRONET.NS","OIL.NS","GSPL.NS","MRPL.NS","TORNTPOWER.NS","CESC.NS","MGL.NS"],
    "Metals":      ["TATASTEEL.NS","JSWSTEEL.NS","HINDALCO.NS","VEDL.NS","SAIL.NS",
                    "NATIONALUM.NS","NMDC.NS","WELCORP.NS","APLAPOLLO.NS"],
    "Infra":       ["LT.NS","ADANIPORTS.NS","ADANIENT.NS","GMRAIRPORT.NS","NCC.NS",
                    "KEC.NS","ENGINERSIN.NS","NBCC.NS","RITES.NS","RAILTEL.NS",
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
                    "VINATIORGA.NS","NAVINFLUOR.NS"],
    "Telecom":     ["BHARTIARTL.NS","TATACOMM.NS","HFCL.NS","RAILTEL.NS","TTML.NS"],
    "Diversified": ["SIEMENS.NS","BOSCHLTD.NS","HONAUT.NS","SCHAEFFLER.NS",
                    "TIMKEN.NS","SKFINDIA.NS","ELGIEQUIP.NS","CUMMINSIND.NS"],
}

def get_sector(symbol):
    for sector, stocks in SECTOR_MAP.items():
        if symbol in stocks:
            return sector
    return "Other"


# ─────────────────────────────────────────────────────────
#  RSI GRADING ENGINE
#  Returns: grade (A/B/C/FAIL), rsi_now, rsi_3d_ago,
#           rsi_slope, rsi_note
# ─────────────────────────────────────────────────────────

def grade_rsi(df):
    """
    RSI Rules for swing trading (5-10% profit target):

    GRADE A  — Perfect entry zone
      Rule A1: RSI 50–65 AND rising           → momentum building, room to grow
      Rule A2: RSI was below 40 in last 5d
               AND RSI now above 45 rising    → oversold recovery, early entry

    GRADE B  — Acceptable, reduce position size
      Rule B1: RSI 40–50 AND rising           → early recovery, needs confirmation
      Rule B2: RSI 65–70 AND rising           → momentum strong but watch closely

    GRADE C  — Weak, skip or very small position
      Rule C1: RSI 70–75                      → approaching overbought
      Rule C2: RSI any value but FALLING      → momentum weakening

    FAIL  — Hard skip
      Rule F1: RSI above 75                   → overbought, move likely done
      Rule F2: RSI below 40 AND still falling → falling knife, avoid
      Rule F3: Extreme volume + RSI > 75      → operator pump, dangerous
    """
    try:
        close = df["Close"].copy()
        rsi_series = ta.rsi(close, length=14)
        if rsi_series is None or rsi_series.dropna().empty:
            return "B", None, None, 0, "RSI unavailable"

        rsi_series = rsi_series.dropna()
        if len(rsi_series) < 6:
            return "B", None, None, 0, "Insufficient RSI data"

        rsi_now    = round(float(rsi_series.iloc[-1]), 1)
        rsi_1d     = round(float(rsi_series.iloc[-2]), 1)
        rsi_3d     = round(float(rsi_series.iloc[-4]), 1)
        rsi_5d     = round(float(rsi_series.iloc[-6]), 1)

        # Slope: difference over last 3 days
        rsi_slope  = round(rsi_now - rsi_3d, 1)
        rising     = rsi_slope > 0
        falling    = rsi_slope < 0

        # Check if RSI was oversold recently (last 5 days)
        recent_oversold = any(
            float(rsi_series.iloc[-i]) < 40
            for i in range(1, min(6, len(rsi_series)))
        )

        # ── FAIL rules (hard skip) ──────────────────
        if rsi_now > 75:
            return "FAIL", rsi_now, rsi_3d, rsi_slope, f"RSI {rsi_now} — overbought, skip"
        if rsi_now < 40 and falling:
            return "FAIL", rsi_now, rsi_3d, rsi_slope, f"RSI {rsi_now} — falling knife, skip"

        # ── GRADE A rules ───────────────────────────
        if 50 <= rsi_now <= 65 and rising:
            return "A", rsi_now, rsi_3d, rsi_slope, f"RSI {rsi_now} rising — sweet spot ✓"
        if recent_oversold and rsi_now >= 45 and rising:
            return "A", rsi_now, rsi_3d, rsi_slope, f"RSI {rsi_now} recovering from oversold ✓"

        # ── GRADE B rules ───────────────────────────
        if 40 <= rsi_now < 50 and rising:
            return "B", rsi_now, rsi_3d, rsi_slope, f"RSI {rsi_now} — early recovery, watch"
        if 65 < rsi_now <= 70 and rising:
            return "B", rsi_now, rsi_3d, rsi_slope, f"RSI {rsi_now} — strong but near overbought"
        if 50 <= rsi_now <= 65 and not rising:
            return "B", rsi_now, rsi_3d, rsi_slope, f"RSI {rsi_now} — in range but flat/falling"

        # ── GRADE C rules ───────────────────────────
        if 70 < rsi_now <= 75:
            return "C", rsi_now, rsi_3d, rsi_slope, f"RSI {rsi_now} — approaching overbought"
        if falling:
            return "C", rsi_now, rsi_3d, rsi_slope, f"RSI {rsi_now} — momentum weakening"

        # Default
        return "B", rsi_now, rsi_3d, rsi_slope, f"RSI {rsi_now} — neutral"

    except Exception as e:
        return "B", None, None, 0, "RSI error"


# ─────────────────────────────────────────────────────────
#  DATA FETCH
# ─────────────────────────────────────────────────────────

def fetch_data(symbol, period="6mo"):
    try:
        df = yf.download(symbol, period=period, auto_adjust=True, progress=False)
        if df.empty or len(df) < 55:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df[["Open","High","Low","Close","Volume"]].copy()
        df.dropna(inplace=True)
        return df
    except Exception:
        return None


# ─────────────────────────────────────────────────────────
#  EMA + RSI SIGNAL DETECTION
# ─────────────────────────────────────────────────────────

def detect_signals(df, symbol):
    if df is None or len(df) < 55:
        return None

    df = df.copy()
    df["EMA20"] = ta.ema(df["Close"], length=20)
    df["EMA50"] = ta.ema(df["Close"], length=50)
    df = df.dropna()

    if len(df) < 10:
        return None

    latest    = df.iloc[-1]
    price     = round(float(latest["Close"]), 2)
    ema20     = round(float(latest["EMA20"]), 2)
    ema50     = round(float(latest["EMA50"]), 2)
    vol_today = float(latest["Volume"])
    vol_avg20 = float(df["Volume"].tail(20).mean())
    vol_ratio = round(vol_today / vol_avg20, 2) if vol_avg20 > 0 else 0

    # ── Golden Cross detection ──────────────────
    golden_cross    = False
    cross_days_ago  = None
    for i in range(1, 6):
        if len(df) > i + 1:
            curr_row = df.iloc[-i]
            prev_row = df.iloc[-(i+1)]
            if (float(prev_row["EMA20"]) <= float(prev_row["EMA50"]) and
                float(curr_row["EMA20"]) >  float(curr_row["EMA50"])):
                golden_cross   = True
                cross_days_ago = i
                break

    # ── EMA20 Bounce detection ──────────────────
    ema20_bounce = False
    if ema20 > ema50 and price > ema20:
        for i in range(2, 5):
            if len(df) > i:
                past      = df.iloc[-i]
                past_low  = float(past["Low"])
                past_ema20= float(past["EMA20"])
                touch_pct = abs(past_low - past_ema20) / past_ema20 * 100
                if touch_pct <= 1.5:
                    ema20_bounce = True
                    break

    if not golden_cross and not ema20_bounce:
        return None

    # ── RSI grading ────────────────────────────
    rsi_grade, rsi_now, rsi_3d, rsi_slope, rsi_note = grade_rsi(df)

    # Hard skip if RSI fails
    if rsi_grade == "FAIL":
        return None

    # Extreme volume suspicion flag (>5x = possible operator pump)
    suspicious_vol = vol_ratio >= 5.0

    # If suspicious volume AND RSI already high → skip
    if suspicious_vol and rsi_now and rsi_now > 65:
        return None

    # ── Levels ─────────────────────────────────
    sl   = round(ema50 * 0.985, 2)
    tgt1 = round(price * 1.05, 2)
    tgt2 = round(price * 1.10, 2)
    risk = round(((price - sl) / price) * 100, 2)
    rr   = round((tgt1 - price) / (price - sl), 2) if price > sl else 0

    signal_type = []
    if golden_cross:
        signal_type.append(f"Golden Cross ({cross_days_ago}d ago)")
    if ema20_bounce:
        signal_type.append("EMA20 Bounce")

    # ── Combined grade (EMA signal + RSI grade) ─
    # Golden Cross + Grade A = A+
    # Golden Cross + Grade B = A
    # EMA Bounce  + Grade A = A
    # EMA Bounce  + Grade B = B
    # Any         + Grade C = C
    if rsi_grade == "C":
        combined_grade = "C"
    elif golden_cross and rsi_grade == "A":
        combined_grade = "A+"
    elif golden_cross and rsi_grade == "B":
        combined_grade = "A"
    elif ema20_bounce and rsi_grade == "A":
        combined_grade = "A"
    else:
        combined_grade = "B"

    return {
        "Grade":          combined_grade,
        "Symbol":         symbol.replace(".NS",""),
        "Sector":         get_sector(symbol),
        "EMA_Signal":     " + ".join(signal_type),
        "RSI_Now":        rsi_now,
        "RSI_3d_Ago":     rsi_3d,
        "RSI_Slope":      rsi_slope,
        "RSI_Note":       rsi_note,
        "Price":          price,
        "EMA20":          ema20,
        "EMA50":          ema50,
        "Vol_Ratio":      vol_ratio,
        "Suspicious_Vol": suspicious_vol,
        "SL":             sl,
        "Target_5pct":    tgt1,
        "Target_10pct":   tgt2,
        "Risk_pct":       risk,
        "RR_Ratio":       rr,
    }


# ─────────────────────────────────────────────────────────
#  SECTOR CAP  —  max 3 per sector, best grade first
# ─────────────────────────────────────────────────────────

GRADE_ORDER = {"A+": 0, "A": 1, "B": 2, "C": 3}

def apply_sector_cap(results, max_per_sector=3):
    sector_count = {}
    final = []
    sorted_results = sorted(
        results,
        key=lambda x: (GRADE_ORDER.get(x["Grade"], 9), -x["RR_Ratio"])
    )
    for r in sorted_results:
        sec   = r["Sector"]
        count = sector_count.get(sec, 0)
        if count < max_per_sector:
            final.append(r)
            sector_count[sec] = count + 1
    return final


# ─────────────────────────────────────────────────────────
#  PRINT RESULTS
# ─────────────────────────────────────────────────────────

GRADE_COLOR = {
    "A+": GREEN  + BOLD,
    "A":  GREEN,
    "B":  YELLOW,
    "C":  RED,
}

def print_results(results):
    if not results:
        print(f"\n{RED}No signals passed all filters today.{RESET}")
        return

    # Split by grade
    aplus  = [r for r in results if r["Grade"] == "A+"]
    a      = [r for r in results if r["Grade"] == "A"]
    b      = [r for r in results if r["Grade"] == "B"]
    c      = [r for r in results if r["Grade"] == "C"]

    def print_section(title, color, stocks):
        if not stocks:
            return
        print(f"\n{color}{BOLD}  {title}  ({len(stocks)} stocks){RESET}")
        print(f"{DIM}  {'─'*108}{RESET}")
        print(f"{DIM}  {'SYMBOL':<12} {'SECTOR':<13} {'EMA SIGNAL':<30} {'RSI':>5} {'SLOPE':>6} {'PRICE':>9} {'SL':>9} {'TGT5%':>9} {'TGT10%':>9} {'VOL':>6}  RSI NOTE{RESET}")
        print(f"{DIM}  {'─'*108}{RESET}")
        for r in stocks:
            vol_str = f"{r['Vol_Ratio']:.1f}x"
            if r["Suspicious_Vol"]:
                vol_str = RED + vol_str + "⚠" + RESET
            elif r["Vol_Ratio"] >= 1.5:
                vol_str = YELLOW + vol_str + "↑" + RESET
            slope_str = f"+{r['RSI_Slope']}" if r['RSI_Slope'] and r['RSI_Slope'] > 0 else str(r['RSI_Slope'] or "n/a")
            rsi_str   = str(r['RSI_Now']) if r['RSI_Now'] else "n/a"
            print(
                f"  {color}{BOLD}{r['Symbol']:<12}{RESET}"
                f"{r['Sector']:<13}"
                f"{r['EMA_Signal']:<30}"
                f"{rsi_str:>5}"
                f"{slope_str:>7}"
                f"{r['Price']:>10.2f}"
                f"{RED}{r['SL']:>10.2f}{RESET}"
                f"{GREEN}{r['Target_5pct']:>10.2f}{RESET}"
                f"{GREEN}{r['Target_10pct']:>10.2f}{RESET}"
                f"  {vol_str:<8}"
                f"  {DIM}{r['RSI_Note']}{RESET}"
            )

    print(f"\n{BOLD}{CYAN}{'═'*110}")
    print(f"  SCAN RESULTS — {datetime.now().strftime('%A, %d %B %Y  %H:%M')}")
    print(f"  Total signals after all filters: {len(results)}")
    print(f"{'═'*110}{RESET}")

    print_section("GRADE A+  —  STRONGEST (Golden Cross + RSI sweet spot)", GREEN + BOLD, aplus)
    print_section("GRADE A   —  STRONG (Golden Cross or EMA Bounce + good RSI)", GREEN, a)
    print_section("GRADE B   —  MODERATE (EMA signal + early/near RSI zone)", YELLOW, b)
    print_section("GRADE C   —  WEAK (RSI momentum fading — small position only)", RED, c)

    print(f"\n{BOLD}{CYAN}{'─'*110}{RESET}")
    print(f"\n{BOLD}LEGEND:{RESET}")
    print(f"  {GREEN+BOLD}A+{RESET} Golden Cross happened + RSI 50–65 rising — best possible setup")
    print(f"  {GREEN}A {RESET} Strong EMA signal + RSI in good zone — full position")
    print(f"  {YELLOW}B {RESET} EMA signal valid + RSI acceptable — half position")
    print(f"  {RED}C {RESET} EMA signal exists but RSI weak — skip or very small position")
    print(f"\n  RSI Slope = RSI change over last 3 days (+ve = rising, -ve = falling)")
    print(f"  {YELLOW}↑{RESET} Vol ≥ 1.5x avg = volume confirming   {RED}⚠{RESET} Vol ≥ 5x = suspicious, caution\n")


def save_to_csv(results, filename=None):
    if not results:
        return
    if filename is None:
        filename = f"ema_rsi_scan_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    df = pd.DataFrame(results)
    cols = ["Grade","Symbol","Sector","EMA_Signal","RSI_Now","RSI_Slope",
            "RSI_Note","Price","EMA20","EMA50","SL","Target_5pct","Target_10pct",
            "Risk_pct","RR_Ratio","Vol_Ratio"]
    df = df[[c for c in cols if c in df.columns]]
    df.to_csv(filename, index=False)
    print(f"{GREEN}✓ Results saved to: {filename}{RESET}")


# ─────────────────────────────────────────────────────────
#  MAIN SCANNER
# ─────────────────────────────────────────────────────────

def run_scanner(stocks=None, save_csv=True, max_per_sector=3):
    if stocks is None:
        stocks = ALL_STOCKS

    print(f"\n{BOLD}{'='*60}")
    print(f"  INDIAN STOCK EMA 20/50 + RSI SCANNER")
    print(f"  {datetime.now().strftime('%A, %d %B %Y  %H:%M')}")
    print(f"  Scanning {len(stocks)} stocks...")
    print(f"  Filters: EMA Golden Cross / EMA20 Bounce + RSI Grade")
    print(f"{'='*60}{RESET}\n")

    raw_signals  = []
    rsi_filtered = 0
    total        = len(stocks)

    for i, symbol in enumerate(stocks, 1):
        name = symbol.replace(".NS","")
        print(f"  [{i:>3}/{total}] Scanning {name:<15}", end="\r")

        df     = fetch_data(symbol)
        signal = detect_signals(df, symbol)

        if signal:
            raw_signals.append(signal)
            gc = GRADE_COLOR.get(signal['Grade'], '')
            print(f"  [{i:>3}/{total}] {gc}{signal['Grade']}{RESET} {name:<12} "
                  f"{signal['EMA_Signal']:<30} RSI:{signal['RSI_Now']}  {DIM}{signal['RSI_Note']}{RESET}   ")

        time.sleep(0.3)

    print(f"\n\n  Scan complete.")
    print(f"  EMA signals found    : {len(raw_signals)}")
    print(f"  RSI FAIL filtered out: {rsi_filtered}")

    # Sector cap
    final = apply_sector_cap(raw_signals, max_per_sector)
    print(f"  After sector cap     : {len(final)} stocks in final watchlist\n")

    print_results(final)

    if save_csv and final:
        save_to_csv(final)

    # Summary counts
    grades = {"A+":0,"A":0,"B":0,"C":0}
    for r in final:
        grades[r["Grade"]] = grades.get(r["Grade"],0) + 1
    print(f"\n{BOLD}  GRADE SUMMARY:{RESET}")
    print(f"  {GREEN+BOLD}A+ : {grades['A+']} stocks{RESET}  ← Priority entries this week")
    print(f"  {GREEN}A  : {grades['A']} stocks{RESET}  ← Strong entries")
    print(f"  {YELLOW}B  : {grades['B']} stocks{RESET}  ← Half position")
    print(f"  {RED}C  : {grades['C']} stocks{RESET}  ← Skip\n")

    return final


# ─────────────────────────────────────────────────────────
#  QUICK SCAN
# ─────────────────────────────────────────────────────────

def quick_scan(symbols):
    symbols_ns = [s if s.endswith(".NS") else s + ".NS" for s in symbols]
    print(f"\n{BOLD}Quick scan: {', '.join(symbols)}{RESET}\n")
    results = []
    for symbol in symbols_ns:
        df = fetch_data(symbol)
        signal = detect_signals(df, symbol)
        if signal:
            results.append(signal)
        else:
            name = symbol.replace(".NS","")
            print(f"  {RED}✗ {name} — no signal (EMA not set up or RSI filtered){RESET}")
        time.sleep(0.3)
    print_results(results)
    return results


# ─────────────────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        quick_scan(sys.argv[1:])
    else:
        run_scanner(stocks=ALL_STOCKS, save_csv=True, max_per_sector=3)
