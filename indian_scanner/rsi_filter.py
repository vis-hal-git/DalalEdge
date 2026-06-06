"""
============================================================
  RSI FILTER MODULE
  Grades each stock A / B / C / FAIL based on RSI rules
  designed specifically for swing trading (5-10% profit).

  GRADE A  — Perfect entry zone
    A1: RSI 50–65 AND rising           → sweet spot, room to grow
    A2: RSI was below 40 recently
        AND now above 45 rising        → oversold recovery

  GRADE B  — Acceptable — reduce position size
    B1: RSI 40–50 AND rising           → early recovery
    B2: RSI 65–70 AND rising           → strong but near overbought
    B3: RSI 50–65 AND flat/falling     → in range but losing steam

  GRADE C  — Weak — skip or tiny position
    C1: RSI 70–75                      → approaching overbought
    C2: RSI falling regardless         → momentum weakening

  FAIL  — Hard skip
    F1: RSI above 75                   → overbought, move likely done
    F2: RSI below 40 AND still falling → falling knife
============================================================
"""

import pandas_ta as ta


def grade_rsi(df):
    """
    Analyse RSI and return grade + details.

    Returns:
        grade     : "A" | "B" | "C" | "FAIL"
        rsi_now   : float
        rsi_3d    : float
        rsi_slope : float  (positive = rising)
        rsi_note  : str
    """
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

        # Was RSI oversold recently? (last 5 days)
        recent_oversold = any(
            float(rsi_series.iloc[-i]) < 40
            for i in range(1, min(6, len(rsi_series)))
        )

        # ── FAIL rules ─────────────────────────────────
        if rsi_now > 75:
            return "FAIL", rsi_now, rsi_3d, rsi_slope, f"RSI {rsi_now} — overbought, skip"
        if rsi_now < 40 and falling:
            return "FAIL", rsi_now, rsi_3d, rsi_slope, f"RSI {rsi_now} — falling knife, skip"

        # ── GRADE A rules ───────────────────────────────
        if 50 <= rsi_now <= 65 and rising:
            return "A", rsi_now, rsi_3d, rsi_slope, f"RSI {rsi_now} rising — sweet spot ✓"
        if recent_oversold and rsi_now >= 45 and rising:
            return "A", rsi_now, rsi_3d, rsi_slope, f"RSI {rsi_now} recovering from oversold ✓"

        # ── GRADE B rules ───────────────────────────────
        if 40 <= rsi_now < 50 and rising:
            return "B", rsi_now, rsi_3d, rsi_slope, f"RSI {rsi_now} — early recovery, watch"
        if 65 < rsi_now <= 70 and rising:
            return "B", rsi_now, rsi_3d, rsi_slope, f"RSI {rsi_now} — strong but near overbought"
        if 50 <= rsi_now <= 65 and not rising:
            return "B", rsi_now, rsi_3d, rsi_slope, f"RSI {rsi_now} — in range but flat/falling"

        # ── GRADE C rules ───────────────────────────────
        if 70 < rsi_now <= 75:
            return "C", rsi_now, rsi_3d, rsi_slope, f"RSI {rsi_now} — approaching overbought"
        if falling:
            return "C", rsi_now, rsi_3d, rsi_slope, f"RSI {rsi_now} — momentum weakening"

        return "B", rsi_now, rsi_3d, rsi_slope, f"RSI {rsi_now} — neutral"

    except Exception:
        return "B", None, None, 0, "RSI error"
