"""
============================================================
  INDIAN STOCK SCANNER
  EMA 20/50 + RSI + 7 TRENDLINE SCENARIOS
  
  SIGNALS (EMA):
    - Golden Cross
    - EMA20 Bounce

  RSI FILTER:
    - Grade A / B / C / FAIL

  TRENDLINE LAYER:
    REJECTION FILTERS (hard skip):
      T1. Downtrend Line (LH+LL)        → dead cat bounce trap
      T2. Bull Trap detected             → false breakout trap

    ENTRY SIGNALS (grade boost):
      T3. Uptrend Line (HH+HL)          → confirms genuine trend
      T4. Third Touch Bounce             → institutional confirmation
      T5. Bullish Rejection at Uptrend  → price held support
      T6. Closing Price Breakout         → confirmed breakout
      T7. Breakout Retest as Support     → safest entry point

  FINAL GRADING:
    A++ = EMA + RSI A + 2 or more trendline signals
    A+  = EMA + RSI A + 1 trendline signal
    A   = EMA + RSI A only
    B   = EMA + RSI B
    C   = RSI C (weak momentum)
    REJECTED = downtrend or bull trap detected

SETUP:
    pip install yfinance pandas pandas-ta colorama

RUN:
    python marsi_trendline.py
    python marsi_trendline.py RELIANCE TCS HDFCBANK
============================================================
"""

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


# ─────────────────────────────────────────────────────────
#  STOCK UNIVERSE
# ─────────────────────────────────────────────────────────

try:
    from nifty500 import get_nifty500_symbols
    ALL_STOCKS = get_nifty500_symbols()
except ImportError:
    # Fallback if nifty500 module not available
    ALL_STOCKS = [
        "RELIANCE.NS","TCS.NS","HDFCBANK.NS","INFY.NS","ICICIBANK.NS",
        "HINDUNILVR.NS","SBIN.NS","BAJFINANCE.NS","BHARTIARTL.NS","KOTAKBANK.NS",
        "ITC.NS","LT.NS","AXISBANK.NS","ASIANPAINT.NS","MARUTI.NS",
        "TITAN.NS","SUNPHARMA.NS","ULTRACEMCO.NS","WIPRO.NS","NESTLEIND.NS",
        "POWERGRID.NS","NTPC.NS","TATAMOTORS.NS","M&M.NS","TECHM.NS",
        "HCLTECH.NS","BAJAJFINSV.NS","ONGC.NS","ADANIENT.NS","COALINDIA.NS",
        "DIVISLAB.NS","DRREDDY.NS","CIPLA.NS","EICHERMOT.NS","HEROMOTOCO.NS",
        "BPCL.NS","TATACONSUM.NS","BRITANNIA.NS","JSWSTEEL.NS","TATASTEEL.NS",
        "INDUSINDBK.NS","GRASIM.NS","HINDALCO.NS","SBILIFE.NS","HDFCLIFE.NS",
        "APOLLOHOSP.NS","BAJAJ-AUTO.NS","ADANIPORTS.NS","UPL.NS","LTIMINDTCH.NS",
        "AMBUJACEM.NS","BANKBARODA.NS","BERGEPAINT.NS","BIOCON.NS","BOSCHLTD.NS",
        "CANBK.NS","CHOLAFIN.NS","DABUR.NS","DLF.NS","GODREJCP.NS",
        "HAVELLS.NS","INDHOTEL.NS","IOC.NS","LUPIN.NS","MUTHOOTFIN.NS",
        "NAUKRI.NS","PIDILITIND.NS","PNB.NS","RECLTD.NS","SIEMENS.NS",
        "SRF.NS","TATACOMM.NS","TORNTPHARM.NS","VEDL.NS","VOLTAS.NS",
        "ZOMATO.NS","PAYTM.NS","NYKAA.NS","POLICYBZR.NS","DMART.NS",
        "ABCAPITAL.NS","APLAPOLLO.NS","ASTRAL.NS","ATUL.NS","AUBANK.NS",
        "AUROPHARMA.NS","BALKRISIND.NS","BANDHANBNK.NS","BEL.NS","BHARATFORG.NS",
        "BHEL.NS","BIKAJI.NS","BLUESTARCO.NS","CAMS.NS","CANFINHOME.NS",
        "CDSL.NS","CESC.NS","CGPOWER.NS","COFORGE.NS","COLPAL.NS",
        "CONCOR.NS","CROMPTON.NS","CUMMINSIND.NS","CYIENT.NS","DALBHARAT.NS",
        "DEEPAKNTR.NS","ELGIEQUIP.NS","EMAMILTD.NS","ENGINERSIN.NS","EXIDEIND.NS",
        "FEDERALBNK.NS","GLENMARK.NS","GMRAIRPORT.NS","GNFC.NS","GODREJPROP.NS",
        "GRANULES.NS","GSPL.NS","HFCL.NS","HONAUT.NS","IDFCFIRSTB.NS",
        "IEX.NS","INDIAMART.NS","INDIANB.NS","INDIGO.NS","JKCEMENT.NS",
        "JSWENERGY.NS","JUBLFOOD.NS","KANSAINER.NS","KARURVYSYA.NS","KEC.NS",
        "KPITTECH.NS","LALPATHLAB.NS","LAURUSLABS.NS","LICHSGFIN.NS","LTTS.NS",
        "MARICO.NS","MAXHEALTH.NS","MCX.NS","METROPOLIS.NS","MFSL.NS",
        "MGL.NS","MOTILALOFS.NS","MPHASIS.NS","MRPL.NS","NAM-INDIA.NS",
        "NATIONALUM.NS","NAVINFLUOR.NS","NBCC.NS","NCC.NS","NMDC.NS",
        "OBEROIRLTY.NS","OFSS.NS","OIL.NS","PAGEIND.NS","PATANJALI.NS",
        "PERSISTENT.NS","PETRONET.NS","PFIZER.NS","PHOENIXLTD.NS","PVRINOX.NS",
        "RADICO.NS","RAILTEL.NS","RAMCOCEM.NS","RITES.NS","SAIL.NS",
        "SCHAEFFLER.NS","SHREECEM.NS","SKFINDIA.NS","SOBHA.NS","SONACOMS.NS",
        "STARHEALTH.NS","SUNTV.NS","SUPREMEIND.NS","SYNGENE.NS","TATACHEM.NS",
        "TATAELXSI.NS","TATAPOWER.NS","TTML.NS","THYROCARE.NS","TIINDIA.NS",
        "TIMKEN.NS","TORNTPOWER.NS","TRENT.NS","TRIDENT.NS","TRITURBINE.NS",
        "TVSHLTD.NS","TVSMOTOR.NS","UBL.NS","UJJIVANSFB.NS","UNIONBANK.NS",
        "UNOMINDA.NS","UCOBANK.NS","VAIBHAVGBL.NS","VBL.NS","VINATIORGA.NS",
        "WELCORP.NS","WHIRLPOOL.NS","YESBANK.NS","ZEEL.NS","ZENSARTECH.NS",
    ]
    ALL_STOCKS = list(set(ALL_STOCKS))


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
#  SWING POINT DETECTION
#  Used by all trendline scenarios
# ─────────────────────────────────────────────────────────

def find_swing_points(df, n=3):
    """
    Find swing highs and swing lows.
    A swing high = high greater than n candles on each side.
    A swing low  = low less than n candles on each side.
    Returns list of (index, price, type) tuples.
    """
    highs = []
    lows  = []
    length = len(df)

    for i in range(n, length - n):
        high_i = float(df["High"].iloc[i])
        low_i  = float(df["Low"].iloc[i])

        # Check swing high
        is_swing_high = all(
            high_i > float(df["High"].iloc[i - j]) and
            high_i > float(df["High"].iloc[i + j])
            for j in range(1, n + 1)
        )
        # Check swing low
        is_swing_low = all(
            low_i < float(df["Low"].iloc[i - j]) and
            low_i < float(df["Low"].iloc[i + j])
            for j in range(1, n + 1)
        )

        if is_swing_high:
            highs.append((i, high_i))
        if is_swing_low:
            lows.append((i, low_i))

    return highs, lows


# ─────────────────────────────────────────────────────────
#  7 TRENDLINE SCENARIO DETECTORS
# ─────────────────────────────────────────────────────────

def detect_trendline_scenarios(df):
    """
    Runs all 7 trendline scenarios.
    Returns dict with results for each scenario.
    """
    results = {
        # Rejection filters
        "T1_downtrend":          False,   # LH+LL — reject
        "T2_bull_trap":          False,   # False breakout — reject

        # Entry signals / grade boosters
        "T3_uptrend":            False,   # HH+HL confirmed
        "T4_third_touch":        False,   # 3rd touch on uptrend line
        "T5_bullish_rejection":  False,   # Price bounced off uptrend support
        "T6_closing_breakout":   False,   # Close above downtrend resistance
        "T7_breakout_retest":    False,   # Breakout then retest as support

        "trendline_notes":       [],
        "trendline_signals":     [],
        "trendline_rejections":  [],
    }

    if df is None or len(df) < 30:
        return results

    try:
        highs, lows = find_swing_points(df, n=3)

        # Need at least 3 swing points for pattern detection
        if len(highs) < 2 or len(lows) < 2:
            return results

        # ── Recent swing points (last 60 candles) ───────────
        recent_cutoff = len(df) - 60
        recent_highs  = [(i, p) for i, p in highs if i >= recent_cutoff]
        recent_lows   = [(i, p) for i, p in lows  if i >= recent_cutoff]

        latest_close  = float(df["Close"].iloc[-1])
        latest_high   = float(df["High"].iloc[-1])
        latest_low    = float(df["Low"].iloc[-1])
        prev_close    = float(df["Close"].iloc[-2])

        # ════════════════════════════════════════════════════
        # T1 — DOWNTREND LINE (LH + LL) — REJECTION FILTER
        # Detect if stock is making lower highs AND lower lows
        # ════════════════════════════════════════════════════
        if len(recent_highs) >= 3 and len(recent_lows) >= 3:
            last3_highs = [p for _, p in recent_highs[-3:]]
            last3_lows  = [p for _, p in recent_lows[-3:]]
            # Lower Highs: each high lower than previous
            lh = last3_highs[0] > last3_highs[1] > last3_highs[2]
            # Lower Lows: each low lower than previous
            ll = last3_lows[0]  > last3_lows[1]  > last3_lows[2]
            if lh and ll:
                results["T1_downtrend"] = True
                results["trendline_rejections"].append("T1: Downtrend (LH+LL) — dead cat bounce risk")

        # ════════════════════════════════════════════════════
        # T2 — BULL TRAP (False Breakout) — REJECTION FILTER
        # Price broke above recent high BUT closed back below it
        # Check last 5 candles
        # ════════════════════════════════════════════════════
        if len(recent_highs) >= 2:
            prev_swing_high = recent_highs[-1][1]  # most recent swing high price
            bull_trap_found = False
            for i in range(2, min(6, len(df))):
                candle      = df.iloc[-i]
                candle_high = float(candle["High"])
                candle_close= float(candle["Close"])
                # Candle broke above swing high but closed below it
                if candle_high > prev_swing_high and candle_close < prev_swing_high:
                    # And current price is still below that level
                    if latest_close < prev_swing_high:
                        bull_trap_found = True
                        break
            if bull_trap_found:
                results["T2_bull_trap"] = True
                results["trendline_rejections"].append("T2: Bull Trap — false breakout detected")

        # ════════════════════════════════════════════════════
        # T3 — UPTREND LINE (HH + HL) — GRADE BOOSTER
        # Stock making higher highs AND higher lows
        # ════════════════════════════════════════════════════
        if len(recent_highs) >= 3 and len(recent_lows) >= 3:
            last3_highs = [p for _, p in recent_highs[-3:]]
            last3_lows  = [p for _, p in recent_lows[-3:]]
            hh = last3_highs[2] > last3_highs[1] > last3_highs[0]
            hl = last3_lows[2]  > last3_lows[1]  > last3_lows[0]
            if hh and hl:
                results["T3_uptrend"] = True
                results["trendline_signals"].append("T3: Uptrend (HH+HL) confirmed ✓")

        # ════════════════════════════════════════════════════
        # T4 — THIRD TOUCH BOUNCE — GRADE BOOSTER
        # Price has touched the uptrend support line 3+ times
        # and is currently bouncing up from it
        # Detect: 3 swing lows roughly on same upward slope
        # ════════════════════════════════════════════════════
        if len(recent_lows) >= 3 and results["T3_uptrend"]:
            l1_idx, l1_p = recent_lows[-3]
            l2_idx, l2_p = recent_lows[-2]
            l3_idx, l3_p = recent_lows[-1]

            # Calculate expected trendline value at l3 position
            if l2_idx != l1_idx:
                slope         = (l2_p - l1_p) / (l2_idx - l1_idx)
                expected_l3   = l1_p + slope * (l3_idx - l1_idx)
                deviation_pct = abs(l3_p - expected_l3) / expected_l3 * 100

                # l3 is within 2% of trendline = third touch
                if deviation_pct <= 2.0 and latest_close > l3_p:
                    results["T4_third_touch"] = True
                    results["trendline_signals"].append("T4: 3rd touch bounce on uptrend line ✓")

        # ════════════════════════════════════════════════════
        # T5 — BULLISH REJECTION AT UPTREND LINE — GRADE BOOSTER
        # Price dipped to uptrend support and bounced back up
        # Current close above recent low, showing rejection
        # ════════════════════════════════════════════════════
        if results["T3_uptrend"] and len(recent_lows) >= 1:
            last_low_idx, last_low_p = recent_lows[-1]
            candles_since_low = len(df) - 1 - last_low_idx

            # Low was within last 5 candles and price has since recovered
            if candles_since_low <= 5:
                recovery_pct = (latest_close - last_low_p) / last_low_p * 100
                # Price recovered at least 1% from the low
                if recovery_pct >= 1.0 and latest_close > prev_close:
                    results["T5_bullish_rejection"] = True
                    results["trendline_signals"].append("T5: Bullish rejection — bounced off uptrend support ✓")

        # ════════════════════════════════════════════════════
        # T6 — CLOSING PRICE BREAKOUT — GRADE BOOSTER
        # Price closes above a prior swing high (resistance)
        # with a strong close (close in upper 30% of candle range)
        # ════════════════════════════════════════════════════
        if len(recent_highs) >= 2:
            # Use second-to-last swing high as resistance level
            resistance_idx, resistance_p = recent_highs[-2]
            # Make sure it's not too old (within last 40 candles)
            if len(df) - 1 - resistance_idx <= 40:
                if latest_close > resistance_p:
                    # Check candle quality: close in upper 30% of range
                    candle_range  = latest_high - latest_low
                    close_position= (latest_close - latest_low) / candle_range if candle_range > 0 else 0
                    if close_position >= 0.70:
                        results["T6_closing_breakout"] = True
                        results["trendline_signals"].append(f"T6: Closing breakout above ₹{resistance_p:.1f} ✓")

        # ════════════════════════════════════════════════════
        # T7 — BREAKOUT RETEST AS SUPPORT — GRADE BOOSTER
        # Price broke out above resistance, pulled back to test it,
        # and is now holding above it (resistance became support)
        # ════════════════════════════════════════════════════
        if len(recent_highs) >= 2:
            resistance_idx, resistance_p = recent_highs[-2]
            if len(df) - 1 - resistance_idx <= 40:
                # Check if price broke out earlier (was above resistance)
                breakout_confirmed = False
                retest_confirmed   = False

                # Look back up to 15 candles for breakout → pullback → hold pattern
                prices_after = [float(df["Close"].iloc[-j]) for j in range(1, min(16, len(df)))]
                was_above    = any(p > resistance_p * 1.02 for p in prices_after[2:])  # was 2%+ above
                came_back    = any(abs(p - resistance_p) / resistance_p < 0.015 for p in prices_after[:5])  # came back within 1.5%
                holding_now  = latest_close > resistance_p  # currently holding above

                if was_above and came_back and holding_now:
                    results["T7_breakout_retest"] = True
                    results["trendline_signals"].append(f"T7: Breakout retest held at ₹{resistance_p:.1f} ✓")

    except Exception:
        pass  # If any trendline detection fails, skip silently

    return results


# ─────────────────────────────────────────────────────────
#  RSI GRADING ENGINE
# ─────────────────────────────────────────────────────────

def grade_rsi(df):
    try:
        close      = df["Close"].copy()
        rsi_series = ta.rsi(close, length=14)
        if rsi_series is None or rsi_series.dropna().empty:
            return "B", None, None, 0, "RSI unavailable"

        rsi_series = rsi_series.dropna()
        if len(rsi_series) < 6:
            return "B", None, None, 0, "Insufficient RSI data"

        rsi_now   = round(float(rsi_series.iloc[-1]), 1)
        rsi_3d    = round(float(rsi_series.iloc[-4]), 1)
        rsi_slope = round(rsi_now - rsi_3d, 1)
        rising    = rsi_slope > 0
        falling   = rsi_slope < 0

        recent_oversold = any(
            float(rsi_series.iloc[-i]) < 40
            for i in range(1, min(6, len(rsi_series)))
        )

        if rsi_now > 75:
            return "FAIL", rsi_now, rsi_3d, rsi_slope, f"RSI {rsi_now} — overbought, skip"
        if rsi_now < 40 and falling:
            return "FAIL", rsi_now, rsi_3d, rsi_slope, f"RSI {rsi_now} — falling knife, skip"

        if 50 <= rsi_now <= 65 and rising:
            return "A", rsi_now, rsi_3d, rsi_slope, f"RSI {rsi_now} rising — sweet spot ✓"
        if recent_oversold and rsi_now >= 45 and rising:
            return "A", rsi_now, rsi_3d, rsi_slope, f"RSI {rsi_now} recovering from oversold ✓"

        if 40 <= rsi_now < 50 and rising:
            return "B", rsi_now, rsi_3d, rsi_slope, f"RSI {rsi_now} — early recovery, watch"
        if 65 < rsi_now <= 70 and rising:
            return "B", rsi_now, rsi_3d, rsi_slope, f"RSI {rsi_now} — strong but near overbought"
        if 50 <= rsi_now <= 65 and not rising:
            return "B", rsi_now, rsi_3d, rsi_slope, f"RSI {rsi_now} — in range but flat/falling"

        if 70 < rsi_now <= 75:
            return "C", rsi_now, rsi_3d, rsi_slope, f"RSI {rsi_now} — approaching overbought"
        if falling:
            return "C", rsi_now, rsi_3d, rsi_slope, f"RSI {rsi_now} — momentum weakening"

        return "B", rsi_now, rsi_3d, rsi_slope, f"RSI {rsi_now} — neutral"

    except Exception:
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
#  MASTER SIGNAL DETECTION  —  EMA + RSI + TRENDLINES
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

    # ── EMA: Golden Cross ───────────────────────
    golden_cross   = False
    cross_days_ago = None
    for i in range(1, 6):
        if len(df) > i + 1:
            curr_row = df.iloc[-i]
            prev_row = df.iloc[-(i+1)]
            if (float(prev_row["EMA20"]) <= float(prev_row["EMA50"]) and
                float(curr_row["EMA20"]) >  float(curr_row["EMA50"])):
                golden_cross   = True
                cross_days_ago = i
                break

    # ── EMA: EMA20 Bounce ───────────────────────
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

    # No EMA signal — skip immediately
    if not golden_cross and not ema20_bounce:
        return None

    # ── RSI Grading ─────────────────────────────
    rsi_grade, rsi_now, rsi_3d, rsi_slope, rsi_note = grade_rsi(df)
    if rsi_grade == "FAIL":
        return None

    # ── Suspicious volume check ─────────────────
    suspicious_vol = vol_ratio >= 5.0
    if suspicious_vol and rsi_now and rsi_now > 65:
        return None

    # ── Trendline Scenarios ─────────────────────
    tl = detect_trendline_scenarios(df)

    # REJECTION: Downtrend detected → hard skip
    if tl["T1_downtrend"]:
        return None

    # REJECTION: Bull trap detected → hard skip
    if tl["T2_bull_trap"]:
        return None

    # ── Count trendline boosters ────────────────
    tl_signals = tl["trendline_signals"]
    tl_count   = len(tl_signals)

    # ── Trade Levels ────────────────────────────
    sl   = round(ema50 * 0.985, 2)
    tgt1 = round(price * 1.05, 2)
    tgt2 = round(price * 1.10, 2)
    risk = round(((price - sl) / price) * 100, 2)
    rr   = round((tgt1 - price) / (price - sl), 2) if price > sl else 0

    # ── EMA Signal Label ────────────────────────
    ema_parts = []
    if golden_cross:
        ema_parts.append(f"GoldenX({cross_days_ago}d)")
    if ema20_bounce:
        ema_parts.append("EMA20 Bounce")
    ema_signal = " + ".join(ema_parts)

    # ── Final Combined Grade ────────────────────
    #
    # Base grade from EMA + RSI:
    #   Golden Cross + RSI A = A
    #   Golden Cross + RSI B = B+
    #   EMA Bounce   + RSI A = B+
    #   EMA Bounce   + RSI B = B
    #   Any          + RSI C = C
    #
    # Trendline boosters on top:
    #   +2 or more trendline signals = upgrade one level
    #   +1 trendline signal          = smaller boost
    #
    # Final scale: A++ > A+ > A > B > C

    if rsi_grade == "C":
        base_grade = "C"
    elif golden_cross and rsi_grade == "A":
        base_grade = "A"
    elif golden_cross and rsi_grade == "B":
        base_grade = "B"
    elif ema20_bounce and rsi_grade == "A":
        base_grade = "B"
    else:
        base_grade = "B"

    # Apply trendline boosts
    grade_ladder = ["C", "B", "A", "A+", "A++"]
    idx = grade_ladder.index(base_grade) if base_grade in grade_ladder else 1

    if tl_count >= 2:
        idx = min(idx + 2, len(grade_ladder) - 1)  # +2 levels for 2+ trendline signals
    elif tl_count == 1:
        idx = min(idx + 1, len(grade_ladder) - 1)  # +1 level for 1 trendline signal

    final_grade = grade_ladder[idx]

    return {
        "Grade":             final_grade,
        "Symbol":            symbol.replace(".NS",""),
        "Sector":            get_sector(symbol),
        "EMA_Signal":        ema_signal,
        "TL_Signals":        " | ".join(tl_signals) if tl_signals else "None",
        "TL_Count":          tl_count,
        "RSI_Now":           rsi_now,
        "RSI_Slope":         rsi_slope,
        "RSI_Note":          rsi_note,
        "Price":             price,
        "EMA20":             ema20,
        "EMA50":             ema50,
        "Vol_Ratio":         vol_ratio,
        "Suspicious_Vol":    suspicious_vol,
        "SL":                sl,
        "Target_5pct":       tgt1,
        "Target_10pct":      tgt2,
        "Risk_pct":          risk,
        "RR_Ratio":          rr,
    }


# ─────────────────────────────────────────────────────────
#  SECTOR CAP
# ─────────────────────────────────────────────────────────

GRADE_ORDER = {"A++": 0, "A+": 1, "A": 2, "B": 3, "C": 4}

def apply_sector_cap(results, max_per_sector=3):
    sector_count   = {}
    final          = []
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
    "A++": MAGENTA + BOLD,
    "A+":  GREEN   + BOLD,
    "A":   GREEN,
    "B":   YELLOW,
    "C":   RED,
}

def print_results(results):
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
        print(f"{DIM}  {'─'*120}{RESET}")
        print(f"{DIM}  {'SYMBOL':<12} {'SECTOR':<13} {'EMA':<18} {'TL':>3} {'RSI':>5} {'SLP':>5} {'PRICE':>9} {'SL':>9} {'T5%':>9} {'T10%':>9} {'VOL':>5}  TRENDLINE SIGNALS{RESET}")
        print(f"{DIM}  {'─'*120}{RESET}")
        for r in stocks:
            vol_str = f"{r['Vol_Ratio']:.1f}x"
            if r["Suspicious_Vol"]:
                vol_str = RED + vol_str + "⚠" + RESET
            elif r["Vol_Ratio"] >= 1.5:
                vol_str = YELLOW + vol_str + "↑" + RESET

            slope_str = f"+{r['RSI_Slope']}" if r['RSI_Slope'] and r['RSI_Slope'] > 0 else str(r['RSI_Slope'] or "n/a")
            rsi_str   = str(r['RSI_Now']) if r['RSI_Now'] else "n/a"
            tl_str    = r["TL_Signals"][:55] + "…" if len(r["TL_Signals"]) > 55 else r["TL_Signals"]

            print(
                f"  {color}{BOLD}{r['Symbol']:<12}{RESET}"
                f"{r['Sector']:<13}"
                f"{r['EMA_Signal']:<18}"
                f"{r['TL_Count']:>4}"
                f"{rsi_str:>6}"
                f"{slope_str:>6}"
                f"{r['Price']:>10.2f}"
                f"{RED}{r['SL']:>10.2f}{RESET}"
                f"{GREEN}{r['Target_5pct']:>10.2f}{RESET}"
                f"{GREEN}{r['Target_10pct']:>10.2f}{RESET}"
                f"  {vol_str:<8}"
                f"  {DIM}{tl_str}{RESET}"
            )

    print(f"\n{BOLD}{CYAN}{'═'*120}")
    print(f"  SCAN RESULTS — EMA + RSI + 7 TRENDLINE SCENARIOS")
    print(f"  {datetime.now().strftime('%A, %d %B %Y  %H:%M')}")
    print(f"  Total signals: {len(results)}")
    print(f"{'═'*120}{RESET}")

    print_section("GRADE A++  —  EXCEPTIONAL  (EMA + RSI + 2+ trendline confirmations)", MAGENTA + BOLD, aplusplus)
    print_section("GRADE A+   —  STRONGEST    (EMA + RSI + 1 trendline confirmation)",   GREEN   + BOLD, aplus)
    print_section("GRADE A    —  STRONG        (Golden Cross + good RSI)",                GREEN,          a)
    print_section("GRADE B    —  MODERATE      (EMA signal + acceptable RSI)",            YELLOW,         b)
    print_section("GRADE C    —  WEAK          (RSI momentum fading — skip)",             RED,            c)

    print(f"\n{BOLD}{CYAN}{'─'*120}{RESET}")
    print(f"\n{BOLD}LEGEND:{RESET}")
    print(f"  {MAGENTA+BOLD}A++{RESET} EMA + RSI sweet spot + 2+ trendline signals — best possible setup this week")
    print(f"  {GREEN+BOLD}A+ {RESET} EMA + RSI + 1 trendline signal — strong entry, full position")
    print(f"  {GREEN}A  {RESET} Golden Cross + good RSI — solid entry, full position")
    print(f"  {YELLOW}B  {RESET} EMA signal + acceptable RSI — half position only")
    print(f"  {RED}C  {RESET} Weak RSI momentum — skip")
    print(f"\n  TL = number of trendline signals confirmed (T3–T7)")
    print(f"  {YELLOW}↑{RESET} Vol ≥ 1.5x = volume confirming move")
    print(f"  {RED}⚠{RESET} Vol ≥ 5.0x = suspicious — possible operator pump\n")
    print(f"  REJECTION FILTERS APPLIED (not shown in output):")
    print(f"  T1: Downtrend (LH+LL) detected → hard skip")
    print(f"  T2: Bull Trap (false breakout) detected → hard skip\n")
    print(f"  TRENDLINE SIGNALS (T column):")
    print(f"  T3: Uptrend HH+HL confirmed")
    print(f"  T4: Third touch bounce on uptrend line")
    print(f"  T5: Bullish rejection — bounced off uptrend support")
    print(f"  T6: Closing price breakout above resistance")
    print(f"  T7: Breakout retest held as support\n")


def save_to_csv(results, filename=None):
    if not results:
        return
    if filename is None:
        filename = f"scan_ema_rsi_trendline_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    df_out = pd.DataFrame(results)
    cols = ["Grade","Symbol","Sector","EMA_Signal","TL_Count","TL_Signals",
            "RSI_Now","RSI_Slope","RSI_Note","Price","EMA20","EMA50",
            "SL","Target_5pct","Target_10pct","Risk_pct","RR_Ratio","Vol_Ratio"]
    df_out = df_out[[c for c in cols if c in df_out.columns]]
    df_out.to_csv(filename, index=False)
    print(f"{GREEN}✓ Saved: {filename}{RESET}")


# ─────────────────────────────────────────────────────────
#  MAIN SCANNER
# ─────────────────────────────────────────────────────────

def run_scanner(stocks=None, save_csv=True, max_per_sector=3):
    if stocks is None:
        stocks = ALL_STOCKS

    print(f"\n{BOLD}{'='*65}")
    print(f"  INDIAN STOCK SCANNER — EMA + RSI + 7 TRENDLINE SCENARIOS")
    print(f"  {datetime.now().strftime('%A, %d %B %Y  %H:%M')}")
    print(f"  Universe : {len(stocks)} stocks")
    print(f"  Filters  : EMA → RSI → Trendline rejection → Trendline signals")
    print(f"{'='*65}{RESET}\n")

    raw_signals = []
    rejected_t1 = 0
    rejected_t2 = 0
    total       = len(stocks)

    for i, symbol in enumerate(stocks, 1):
        name = symbol.replace(".NS","")
        print(f"  [{i:>3}/{total}] Scanning {name:<15}", end="\r")

        df     = fetch_data(symbol)
        signal = detect_signals(df, symbol)

        if signal:
            raw_signals.append(signal)
            gc = GRADE_COLOR.get(signal["Grade"], "")
            tl_info = f"TL:{signal['TL_Count']}" if signal['TL_Count'] > 0 else ""
            print(f"  [{i:>3}/{total}] {gc}{signal['Grade']:<4}{RESET} "
                  f"{name:<12} {signal['EMA_Signal']:<20} "
                  f"RSI:{signal['RSI_Now']}  {CYAN}{tl_info}{RESET}   ")

        time.sleep(0.3)

    print(f"\n\n  Scan complete.")
    print(f"  Raw EMA+RSI signals : {len(raw_signals)}")

    final = apply_sector_cap(raw_signals, max_per_sector)
    print(f"  After sector cap    : {len(final)} stocks\n")

    print_results(final)

    if save_csv and final:
        save_to_csv(final)

    grades = {"A++":0,"A+":0,"A":0,"B":0,"C":0}
    for r in final:
        grades[r["Grade"]] = grades.get(r["Grade"],0) + 1

    print(f"\n{BOLD}  GRADE SUMMARY:{RESET}")
    print(f"  {MAGENTA+BOLD}A++ : {grades['A++']} stocks{RESET}  ← Trade these first")
    print(f"  {GREEN+BOLD}A+  : {grades['A+']} stocks{RESET}  ← Strong entries")
    print(f"  {GREEN}A   : {grades['A']} stocks{RESET}  ← Good entries")
    print(f"  {YELLOW}B   : {grades['B']} stocks{RESET}  ← Half position")
    print(f"  {RED}C   : {grades['C']} stocks{RESET}  ← Skip\n")

    return final


# ─────────────────────────────────────────────────────────
#  QUICK SCAN
# ─────────────────────────────────────────────────────────

def quick_scan(symbols):
    symbols_ns = [s if s.endswith(".NS") else s + ".NS" for s in symbols]
    print(f"\n{BOLD}Quick scan: {', '.join(symbols)}{RESET}\n")
    results = []
    for symbol in symbols_ns:
        df     = fetch_data(symbol)
        signal = detect_signals(df, symbol)
        if signal:
            results.append(signal)
        else:
            name = symbol.replace(".NS","")
            print(f"  {RED}✗ {name} — no signal or filtered out{RESET}")
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
