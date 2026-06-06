"""
============================================================
  EMA SIGNALS MODULE
  EMA 20 / EMA 50 — Two signals:
    1. Golden Cross  — EMA20 crosses above EMA50 (last 5 days)
    2. EMA20 Bounce  — Price bounced off EMA20 while EMA20 > EMA50
============================================================
"""

import pandas_ta as ta


def calculate_emas(df):
    """Add EMA20 and EMA50 columns to dataframe."""
    df = df.copy()
    df["EMA20"] = ta.ema(df["Close"], length=20)
    df["EMA50"] = ta.ema(df["Close"], length=50)
    return df.dropna()


def detect_ema_signals(df):
    """
    Detect Golden Cross and EMA20 Bounce signals.

    Returns dict:
        golden_cross    : bool
        cross_days_ago  : int or None
        ema20_bounce    : bool
        ema20           : float
        ema50           : float
        ema_signal      : str  (label for output)
        vol_ratio       : float
        suspicious_vol  : bool
    """
    result = {
        "golden_cross":   False,
        "cross_days_ago": None,
        "ema20_bounce":   False,
        "ema20":          0.0,
        "ema50":          0.0,
        "ema_signal":     "",
        "vol_ratio":      0.0,
        "suspicious_vol": False,
    }

    if df is None or len(df) < 55:
        return result

    df = calculate_emas(df)
    if len(df) < 10:
        return result

    latest    = df.iloc[-1]
    price     = float(latest["Close"])
    ema20     = round(float(latest["EMA20"]), 2)
    ema50     = round(float(latest["EMA50"]), 2)
    vol_today = float(latest["Volume"])
    vol_avg20 = float(df["Volume"].tail(20).mean())
    vol_ratio = round(vol_today / vol_avg20, 2) if vol_avg20 > 0 else 0

    result["ema20"]      = ema20
    result["ema50"]      = ema50
    result["vol_ratio"]  = vol_ratio
    result["suspicious_vol"] = vol_ratio >= 5.0

    # ── Signal 1: Golden Cross ──────────────────────────
    # EMA20 crossed above EMA50 in last 5 candles
    for i in range(1, 6):
        if len(df) > i + 1:
            curr = df.iloc[-i]
            prev = df.iloc[-(i + 1)]
            if (float(prev["EMA20"]) <= float(prev["EMA50"]) and
                    float(curr["EMA20"]) > float(curr["EMA50"])):
                result["golden_cross"]   = True
                result["cross_days_ago"] = i
                break

    # ── Signal 2: EMA20 Bounce ──────────────────────────
    # EMA20 > EMA50 (uptrend) + price dipped near EMA20 and bounced
    if ema20 > ema50 and price > ema20:
        for i in range(2, 5):
            if len(df) > i:
                past       = df.iloc[-i]
                past_low   = float(past["Low"])
                past_ema20 = float(past["EMA20"])
                touch_pct  = abs(past_low - past_ema20) / past_ema20 * 100
                if touch_pct <= 1.5:
                    result["ema20_bounce"] = True
                    break

    # ── Signal label ────────────────────────────────────
    parts = []
    if result["golden_cross"]:
        parts.append(f"GoldenX({result['cross_days_ago']}d)")
    if result["ema20_bounce"]:
        parts.append("EMA20 Bounce")
    result["ema_signal"] = " + ".join(parts)

    return result
