"""
============================================================
  FIBONACCI RETRACEMENT MODULE
  All rules from the Fibonacci framework for swing trading.

  KEY LEVELS:
    23.6% — shallow pullback
    38.2% — first strong support
    50.0% — mid support
    61.8% — golden ratio  ← strongest
    78.6% — last defence before trend fails

  GOLDEN ZONE: 61.8% to 78.6% — highest probability reversal

  RULES IMPLEMENTED:
    Rule 1  — Find valid swing for Fib drawing (min 8% move)
    Rule 2  — Calculate all 5 Fib levels
    Rule 3  — Golden zone detection (61.8–78.6%)
    Rule 4  — Confluence with EMA (Fib + EMA at same level)
    Rule 5  — Entry confirmation (volume + candle quality)
    Rule 6  — Stop loss placement (just below Fib level)
    Rule 7  — Target calculation from entry level
    Rule 8  — Fib extension targets (post breakout)
    Rule 9  — Failure detection (close below 78.6%)
    Rule 10 — Candlestick confirmation at Fib level
    Rule 11 — Use recent swing (last 3 months max)
    Rule 12 — Multi-timeframe note (flag for manual check)
============================================================
"""
# Fibonacci levels used
FIB_LEVELS = {
    "23.6": 0.236,
    "38.2": 0.382,
    "50.0": 0.500,
    "61.8": 0.618,
    "78.6": 0.786,
}

# Fib extension levels (for post-breakout targets)
FIB_EXTENSIONS = {
    "127.2": 1.272,
    "138.2": 1.382,
    "161.8": 1.618,
    "200.0": 2.000,
}

# How close price must be to a Fib level to count as "at the level" (%)
FIB_TOLERANCE_PCT = 1.5


def find_fib_swing(df, lookback=65):
    """
    Rule 11 — Find the most recent valid swing for Fib drawing.
    Valid = minimum 8% move from swing low to swing high.
    Lookback = last N candles (approx 3 months on daily).

    Returns:
        swing_low  : float
        swing_high : float
        move_pct   : float
        valid      : bool
    """
    if df is None or len(df) < 20:
        return None, None, 0, False

    recent = df.tail(lookback)
    swing_low  = float(recent["Low"].min())
    swing_high = float(recent["High"].max())

    low_idx  = recent["Low"].idxmin()
    high_idx = recent["High"].idxmax()

    # Rule 11 — Low must come BEFORE high for a valid uptrend Fib
    # (drawing from low to high = retracement levels are supports)
    try:
        low_pos  = recent.index.get_loc(low_idx)
        high_pos = recent.index.get_loc(high_idx)
        if low_pos >= high_pos:
            return swing_low, swing_high, 0, False
    except Exception:
        return swing_low, swing_high, 0, False

    move_pct = ((swing_high - swing_low) / swing_low) * 100

    # Rule 11 — minimum 8% move for valid Fib
    valid = move_pct >= 8.0

    return swing_low, swing_high, round(move_pct, 1), valid


def calculate_fib_levels(swing_low, swing_high):
    """
    Rule 2 — Calculate all Fib retracement levels.
    Drawing from swing_low to swing_high (uptrend).

    Returns dict of level_name → price
    """
    move = swing_high - swing_low
    levels = {}
    for name, ratio in FIB_LEVELS.items():
        levels[name] = round(swing_high - (move * ratio), 2)
    return levels


def calculate_fib_extensions(swing_low, swing_high):
    """
    Rule 8 — Calculate Fib extension targets post-breakout.

    Returns dict of level_name → price
    """
    move = swing_high - swing_low
    extensions = {}
    for name, ratio in FIB_EXTENSIONS.items():
        extensions[name] = round(swing_low + (move * ratio), 2)
    return extensions


def price_near_fib(price, fib_price, tolerance_pct=FIB_TOLERANCE_PCT):
    """Check if price is within tolerance% of a Fib level."""
    if fib_price <= 0:
        return False
    diff_pct = abs(price - fib_price) / fib_price * 100
    return diff_pct <= tolerance_pct


def detect_fib_signals(df, ema20=None, ema50=None):
    """
    Run all Fibonacci rules on the price data.

    Returns dict:
        fib_valid        : bool   — valid swing found
        fib_level        : str    — level price is near ("61.8", "50.0" etc) or "-"
        fib_price        : float  — price of that level
        fib_signal       : str    — human readable signal
        fib_confluence   : bool   — Fib level aligns with EMA
        fib_golden_zone  : bool   — price in 61.8–78.6% zone
        fib_fail         : bool   — price closed below 78.6% (rule 9)
        fib_sl           : float  — stop loss below the Fib level
        fib_target1      : float  — target 1 (next Fib up)
        fib_target2      : float  — target 2 (swing high)
        fib_ext_161      : float  — extension 161.8% target
        fib_grade_boost  : int    — 0/1/2 boost to apply to grade
        swing_low        : float
        swing_high       : float
        move_pct         : float
    """
    result = {
        "fib_valid":       False,
        "fib_level":       "-",
        "fib_price":       0.0,
        "fib_signal":      "None",
        "fib_confluence":  False,
        "fib_golden_zone": False,
        "fib_fail":        False,
        "fib_sl":          0.0,
        "fib_target1":     0.0,
        "fib_target2":     0.0,
        "fib_ext_161":     0.0,
        "fib_grade_boost": 0,
        "swing_low":       0.0,
        "swing_high":      0.0,
        "move_pct":        0.0,
    }

    if df is None or len(df) < 20:
        return result

    try:
        latest_close = float(df["Close"].iloc[-1])
        latest_low   = float(df["Low"].iloc[-1])
        latest_high  = float(df["High"].iloc[-1])
        prev_close   = float(df["Close"].iloc[-2])
        vol_today    = float(df["Volume"].iloc[-1])
        vol_avg20    = float(df["Volume"].tail(20).mean())
        vol_ratio    = vol_today / vol_avg20 if vol_avg20 > 0 else 1.0

        # ── Rule 1 + 11: Find valid swing ──────────────
        swing_low, swing_high, move_pct, valid = find_fib_swing(df, lookback=65)
        if not valid:
            return result

        result["fib_valid"]   = True
        result["swing_low"]   = round(swing_low, 2)
        result["swing_high"]  = round(swing_high, 2)
        result["move_pct"]    = move_pct

        # ── Rule 2: Calculate all levels ───────────────
        fib_prices = calculate_fib_levels(swing_low, swing_high)
        fib_ext    = calculate_fib_extensions(swing_low, swing_high)

        result["fib_ext_161"] = fib_prices.get("161.8", 0)

        # ── Rule 9: Failure check ───────────────────────
        # If price closed below 78.6% level → trend failed
        level_786 = fib_prices.get("78.6", 0)
        if latest_close < level_786:
            result["fib_fail"] = True
            result["fib_signal"] = f"FAIL: Below 78.6% (₹{level_786:.1f}) — trend broken"
            return result

        # ── Rule 3 + Find nearest Fib level ────────────
        nearest_level = None
        nearest_price = None
        nearest_diff  = float("inf")

        priority_levels = ["61.8", "50.0", "38.2", "78.6", "23.6"]
        for level_name in priority_levels:
            fib_p = fib_prices[level_name]
            if price_near_fib(latest_close, fib_p):
                diff = abs(latest_close - fib_p) / fib_p
                if diff < nearest_diff:
                    nearest_diff  = diff
                    nearest_level = level_name
                    nearest_price = fib_p

        if nearest_level is None:
            # Price not near any Fib level
            return result

        result["fib_level"] = nearest_level
        result["fib_price"] = nearest_price

        # ── Rule 3: Golden zone check ───────────────────
        if nearest_level in ["61.8", "78.6"]:
            result["fib_golden_zone"] = True

        # ── Rule 4: Confluence with EMA ─────────────────
        # Fib level aligns with EMA20 or EMA50 (within 1.5%)
        confluence = False
        if ema20 and price_near_fib(nearest_price, ema20, tolerance_pct=2.0):
            confluence = True
        if ema50 and price_near_fib(nearest_price, ema50, tolerance_pct=2.0):
            confluence = True
        result["fib_confluence"] = confluence

        # ── Rule 5: Entry confirmation ──────────────────
        # Volume lower during pullback (good) — vol_ratio < 1.0
        # Candle closing above Fib level
        # Price recovering (close > prev close)
        vol_declining    = vol_ratio < 1.0
        price_recovering = latest_close > prev_close
        candle_range     = latest_high - latest_low
        close_position   = (
            (latest_close - latest_low) / candle_range
            if candle_range > 0 else 0.5
        )
        strong_close = close_position >= 0.60  # closing in upper 40%

        # ── Rule 6: Stop loss ───────────────────────────
        # 1.5% below the Fib level (avoid stop hunts at exact level)
        fib_sl = round(nearest_price * 0.985, 2)
        result["fib_sl"] = fib_sl

        # ── Rule 7: Targets ─────────────────────────────
        # Target 1 = next Fib level up
        # Target 2 = swing high
        level_order  = ["78.6", "61.8", "50.0", "38.2", "23.6"]
        current_idx  = level_order.index(nearest_level) if nearest_level in level_order else -1
        fib_target1  = swing_high  # default to swing high
        if current_idx > 0:
            next_level  = level_order[current_idx - 1]
            fib_target1 = fib_prices[next_level]

        result["fib_target1"] = round(fib_target1, 2)
        result["fib_target2"] = round(swing_high, 2)
        result["fib_ext_161"] = round(fib_ext.get("161.8", swing_high * 1.1), 2)

        # ── Rule 10: Candlestick confirmation ───────────
        # Check for hammer: lower wick > 2x body, small upper wick
        body         = abs(latest_close - float(df["Open"].iloc[-1]))
        lower_wick   = float(df["Open"].iloc[-1]) - latest_low if latest_close > float(df["Open"].iloc[-1]) else latest_close - latest_low
        upper_wick   = latest_high - max(latest_close, float(df["Open"].iloc[-1]))
        hammer_shape = (lower_wick > 2 * body) and (upper_wick < body) if body > 0 else False
        bullish_candle = latest_close > float(df["Open"].iloc[-1])

        # ── Build signal string ─────────────────────────
        signal_parts = [f"Fib {nearest_level}% (₹{nearest_price:.1f})"]
        if result["fib_golden_zone"]:
            signal_parts.append("GOLDEN ZONE ✓")
        if confluence:
            signal_parts.append("EMA confluence ✓")
        if vol_declining:
            signal_parts.append("vol declining ✓")
        if strong_close and price_recovering:
            signal_parts.append("confirmed bounce ✓")
        if hammer_shape:
            signal_parts.append("hammer ✓")

        result["fib_signal"] = " | ".join(signal_parts)

        # ── Rule 12: Multi-timeframe note ───────────────
        # Flag that user should check weekly chart manually
        # (Cannot automate 2-timeframe check reliably in code)

        # ── Grade boost calculation ─────────────────────
        boost = 0

        # At any valid Fib level = +1
        boost += 1

        # Golden zone = additional +1
        if result["fib_golden_zone"]:
            boost += 1

        # Confluence with EMA = additional +1
        if confluence:
            boost += 1

        # Cap boost at 2 to avoid over-inflating grades
        result["fib_grade_boost"] = min(boost, 2)

    except Exception:
        pass

    return result
