"""
============================================================
  TRENDLINE SIGNALS MODULE
  7 Trendline Scenarios for swing trading

  REJECTION FILTERS (stock removed from watchlist):
    T1. Downtrend Line (LH+LL)         → dead cat bounce trap
    T2. Bull Trap (false breakout)     → fake breakout trap

  ENTRY SIGNALS (boost stock grade):
    T3. Uptrend Line (HH+HL)           → genuine trend confirmed
    T4. Third Touch Bounce             → institutional reaction point
    T5. Bullish Rejection at Uptrend   → price held support, bouncing
    T6. Closing Price Breakout         → strong confirmed breakout
    T7. Breakout Retest as Support     → safest entry after breakout
============================================================
"""


def find_swing_points(df, n=3):
    """
    Detect swing highs and swing lows.
    Swing high: high greater than n candles on both sides.
    Swing low : low less than n candles on both sides.

    Returns:
        highs : list of (index, price)
        lows  : list of (index, price)
    """
    highs  = []
    lows   = []
    length = len(df)

    for i in range(n, length - n):
        high_i = float(df["High"].iloc[i])
        low_i  = float(df["Low"].iloc[i])

        is_swing_high = all(
            high_i > float(df["High"].iloc[i - j]) and
            high_i > float(df["High"].iloc[i + j])
            for j in range(1, n + 1)
        )
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


def detect_trendline_scenarios(df):
    """
    Run all 7 trendline scenarios on price data.

    Returns dict:
        T1_downtrend         : bool  (rejection)
        T2_bull_trap         : bool  (rejection)
        T3_uptrend           : bool  (booster)
        T4_third_touch       : bool  (booster)
        T5_bullish_rejection : bool  (booster)
        T6_closing_breakout  : bool  (booster)
        T7_breakout_retest   : bool  (booster)
        trendline_signals    : list of signal descriptions
        trendline_rejections : list of rejection descriptions
    """
    results = {
        "T1_downtrend":          False,
        "T2_bull_trap":          False,
        "T3_uptrend":            False,
        "T4_third_touch":        False,
        "T5_bullish_rejection":  False,
        "T6_closing_breakout":   False,
        "T7_breakout_retest":    False,
        "trendline_signals":     [],
        "trendline_rejections":  [],
    }

    if df is None or len(df) < 30:
        return results

    try:
        highs, lows = find_swing_points(df, n=3)

        if len(highs) < 2 or len(lows) < 2:
            return results

        # Only look at recent 60 candles for relevance
        recent_cutoff = len(df) - 60
        recent_highs  = [(i, p) for i, p in highs if i >= recent_cutoff]
        recent_lows   = [(i, p) for i, p in lows  if i >= recent_cutoff]

        latest_close = float(df["Close"].iloc[-1])
        latest_high  = float(df["High"].iloc[-1])
        latest_low   = float(df["Low"].iloc[-1])
        prev_close   = float(df["Close"].iloc[-2])

        # ════════════════════════════════════════════════
        # T1 — DOWNTREND (LH + LL) — REJECTION FILTER
        # ════════════════════════════════════════════════
        if len(recent_highs) >= 3 and len(recent_lows) >= 3:
            last3h = [p for _, p in recent_highs[-3:]]
            last3l = [p for _, p in recent_lows[-3:]]
            lh     = last3h[0] > last3h[1] > last3h[2]
            ll     = last3l[0] > last3l[1] > last3l[2]
            if lh and ll:
                results["T1_downtrend"] = True
                results["trendline_rejections"].append(
                    "T1: Downtrend (LH+LL) — dead cat bounce risk"
                )

        # ════════════════════════════════════════════════
        # T2 — BULL TRAP — REJECTION FILTER
        # Broke above swing high but closed back below it
        # ════════════════════════════════════════════════
        if len(recent_highs) >= 2:
            prev_swing_high = recent_highs[-1][1]
            for i in range(2, min(6, len(df))):
                candle = df.iloc[-i]
                c_high = float(candle["High"])
                c_close= float(candle["Close"])
                if c_high > prev_swing_high and c_close < prev_swing_high:
                    if latest_close < prev_swing_high:
                        results["T2_bull_trap"] = True
                        results["trendline_rejections"].append(
                            "T2: Bull Trap — false breakout detected"
                        )
                        break

        # ════════════════════════════════════════════════
        # T3 — UPTREND (HH + HL) — GRADE BOOSTER
        # ════════════════════════════════════════════════
        if len(recent_highs) >= 3 and len(recent_lows) >= 3:
            last3h = [p for _, p in recent_highs[-3:]]
            last3l = [p for _, p in recent_lows[-3:]]
            hh = last3h[2] > last3h[1] > last3h[0]
            hl = last3l[2] > last3l[1] > last3l[0]
            if hh and hl:
                results["T3_uptrend"] = True
                results["trendline_signals"].append("T3: Uptrend (HH+HL) confirmed ✓")

        # ════════════════════════════════════════════════
        # T4 — THIRD TOUCH BOUNCE — GRADE BOOSTER
        # 3 swing lows on the same upward trendline slope
        # ════════════════════════════════════════════════
        if len(recent_lows) >= 3 and results["T3_uptrend"]:
            l1_idx, l1_p = recent_lows[-3]
            l2_idx, l2_p = recent_lows[-2]
            l3_idx, l3_p = recent_lows[-1]
            if l2_idx != l1_idx:
                slope       = (l2_p - l1_p) / (l2_idx - l1_idx)
                expected_l3 = l1_p + slope * (l3_idx - l1_idx)
                deviation   = abs(l3_p - expected_l3) / expected_l3 * 100
                if deviation <= 2.0 and latest_close > l3_p:
                    results["T4_third_touch"] = True
                    results["trendline_signals"].append(
                        "T4: 3rd touch bounce on uptrend line ✓"
                    )

        # ════════════════════════════════════════════════
        # T5 — BULLISH REJECTION AT UPTREND — GRADE BOOSTER
        # Price dipped to support and bounced back up
        # ════════════════════════════════════════════════
        if results["T3_uptrend"] and len(recent_lows) >= 1:
            last_low_idx, last_low_p = recent_lows[-1]
            candles_since_low = len(df) - 1 - last_low_idx
            if candles_since_low <= 5:
                recovery_pct = (latest_close - last_low_p) / last_low_p * 100
                if recovery_pct >= 1.0 and latest_close > prev_close:
                    results["T5_bullish_rejection"] = True
                    results["trendline_signals"].append(
                        "T5: Bullish rejection at uptrend support ✓"
                    )

        # ════════════════════════════════════════════════
        # T6 — CLOSING PRICE BREAKOUT — GRADE BOOSTER
        # Close above prior resistance, strong candle close
        # ════════════════════════════════════════════════
        if len(recent_highs) >= 2:
            res_idx, res_p = recent_highs[-2]
            if len(df) - 1 - res_idx <= 40:
                if latest_close > res_p:
                    candle_range   = latest_high - latest_low
                    close_position = (
                        (latest_close - latest_low) / candle_range
                        if candle_range > 0 else 0
                    )
                    if close_position >= 0.70:
                        results["T6_closing_breakout"] = True
                        results["trendline_signals"].append(
                            f"T6: Closing breakout above ₹{res_p:.1f} ✓"
                        )

        # ════════════════════════════════════════════════
        # T7 — BREAKOUT RETEST AS SUPPORT — GRADE BOOSTER
        # Broke out → pulled back → holding above resistance
        # ════════════════════════════════════════════════
        if len(recent_highs) >= 2:
            res_idx, res_p = recent_highs[-2]
            if len(df) - 1 - res_idx <= 40:
                prices_after = [
                    float(df["Close"].iloc[-j])
                    for j in range(1, min(16, len(df)))
                ]
                was_above   = any(p > res_p * 1.02 for p in prices_after[2:])
                came_back   = any(
                    abs(p - res_p) / res_p < 0.015
                    for p in prices_after[:5]
                )
                holding_now = latest_close > res_p
                if was_above and came_back and holding_now:
                    results["T7_breakout_retest"] = True
                    results["trendline_signals"].append(
                        f"T7: Breakout retest held at ₹{res_p:.1f} ✓"
                    )

    except Exception:
        pass

    return results


def trendline_signal_count(tl_result):
    """Return number of confirmed trendline booster signals."""
    return len(tl_result.get("trendline_signals", []))


def is_trendline_rejected(tl_result):
    """Return True if stock should be hard-skipped due to T1 or T2."""
    return tl_result.get("T1_downtrend", False) or tl_result.get("T2_bull_trap", False)
