"""
============================================================
  FUNDAMENTAL SIGNALS MODULE
  Data Sources:
    1. yfinance       — PE, Market Cap, Beta, EPS
    2. Screener.in    — Debt/Equity, ROE, ROCE, Promoter,
                        Pledge, Revenue/Profit growth,
                        Quarterly earnings
    3. NSE Website    — FII/DII monthly activity
    4. Google News    — Latest news sentiment

  GRADING:
    GREEN  — fundamentally strong, safe to enter
    YELLOW — some concerns, reduce position size
    RED    — fundamental risk, hard skip

  HARD REJECTION (RED):
    Debt/Equity > 2.0
    Promoter pledge > 50%
    3+ consecutive quarterly losses
    Promoter holding < 25%
    Interest coverage < 1.5x

  YELLOW FLAGS:
    FII selling 3+ months
    Revenue growth negative
    PE > 80
    Debt/Equity 1.0–2.0
    Promoter pledge 25–50%

  POSITIVE BOOSTERS (GREEN):
    FII buying 2+ months
    Revenue growth > 15%
    Profit growth > 20%
    Promoter holding > 60%
    ROE > 15%
    Debt/Equity < 0.5
============================================================
"""

import time
import re
import json
import warnings
import requests
import yfinance as yf
import feedparser
warnings.filterwarnings("ignore")

from bs4 import BeautifulSoup
from datetime import datetime

# ── Request headers (look like a browser) ────────────────
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Connection": "keep-alive",
}

# ── Cache — avoid re-fetching same stock same session ─────
_cache = {}


# ─────────────────────────────────────────────────────────
#  SOURCE 1 — yfinance
#  PE, Market Cap, Beta, EPS, basic ratios
# ─────────────────────────────────────────────────────────

def fetch_yfinance_data(symbol):
    """
    Fetch basic fundamental data from yfinance.
    Symbol should include .NS suffix.
    Returns dict of available fields.
    """
    data = {
        "pe_ratio":         None,
        "market_cap":       None,
        "beta":             None,
        "eps":              None,
        "dividend_yield":   None,
        "week52_high":      None,
        "week52_low":       None,
        "debt_to_equity":   None,  # often missing for Indian stocks
        "roe":              None,  # often missing
        "revenue_growth":   None,  # often missing
    }

    try:
        ticker = yf.Ticker(symbol)
        info   = ticker.info

        data["pe_ratio"]       = info.get("trailingPE")        or info.get("forwardPE")
        data["market_cap"]     = info.get("marketCap")
        data["beta"]           = info.get("beta")
        data["eps"]            = info.get("trailingEps")
        data["dividend_yield"] = info.get("dividendYield")
        data["week52_high"]    = info.get("fiftyTwoWeekHigh")
        data["week52_low"]     = info.get("fiftyTwoWeekLow")
        data["debt_to_equity"] = info.get("debtToEquity")
        data["roe"]            = info.get("returnOnEquity")
        data["revenue_growth"] = info.get("revenueGrowth")

        # Convert ROE to percentage if decimal
        if data["roe"] and abs(data["roe"]) < 5:
            data["roe"] = round(data["roe"] * 100, 2)

        # Convert revenue growth to percentage
        if data["revenue_growth"] and abs(data["revenue_growth"]) < 5:
            data["revenue_growth"] = round(data["revenue_growth"] * 100, 2)

    except Exception:
        pass

    return data


# ─────────────────────────────────────────────────────────
#  SOURCE 2 — Screener.in
#  Debt/Equity, ROE, ROCE, Promoter holding,
#  Pledge, Revenue growth, Profit growth,
#  Quarterly earnings
# ─────────────────────────────────────────────────────────

def fetch_screener_data(symbol):
    """
    Scrape fundamental data from Screener.in.
    Symbol without .NS suffix (e.g. RELIANCE not RELIANCE.NS).
    Returns dict of fundamental metrics.
    """
    data = {
        "debt_to_equity":      None,
        "roe":                 None,
        "roce":                None,
        "promoter_holding":    None,
        "promoter_pledge":     None,
        "revenue_growth_3yr":  None,
        "profit_growth_3yr":   None,
        "interest_coverage":   None,
        "pe_ratio":            None,
        "current_ratio":       None,
        "quarterly_profits":   [],  # last 4 quarters
        "quarterly_sales":     [],  # last 4 quarters
        "screener_ok":         False,
    }

    clean_symbol = symbol.replace(".NS", "").replace(".BO", "").upper()
    url = f"https://www.screener.in/company/{clean_symbol}/consolidated/"

    try:
        session = requests.Session()
        resp    = session.get(url, headers=HEADERS, timeout=12)

        # Try standalone if consolidated not found
        if resp.status_code == 404:
            url  = f"https://www.screener.in/company/{clean_symbol}/"
            resp = session.get(url, headers=HEADERS, timeout=12)

        if resp.status_code != 200:
            return data

        soup = BeautifulSoup(resp.text, "html.parser")
        data["screener_ok"] = True

        # ── Key Ratios ──────────────────────────────────
        # Screener shows ratios in a #top-ratios section
        ratios_section = soup.find("div", id="top-ratios")
        if ratios_section:
            ratio_items = ratios_section.find_all("li")
            for item in ratio_items:
                name_tag  = item.find("span", class_="name")
                value_tag = item.find("span", class_="value")
                if not name_tag or not value_tag:
                    continue
                name  = name_tag.get_text(strip=True).lower()
                value = value_tag.get_text(strip=True)
                value = re.sub(r"[,%]", "", value).strip()

                try:
                    val = float(value)
                    if "debt" in name and "equity" in name:
                        data["debt_to_equity"] = val
                    elif "return on equity" in name or "roe" in name:
                        data["roe"] = val
                    elif "roce" in name or "return on capital" in name:
                        data["roce"] = val
                    elif "p/e" in name or "price to earning" in name:
                        data["pe_ratio"] = val
                    elif "current ratio" in name:
                        data["current_ratio"] = val
                    elif "interest coverage" in name:
                        data["interest_coverage"] = val
                except ValueError:
                    pass

        # ── Shareholding — Promoter holding + Pledge ────
        shareholding = soup.find("section", id="shareholding")
        if shareholding:
            tables = shareholding.find_all("table")
            for table in tables:
                rows = table.find_all("tr")
                for row in rows:
                    cols = row.find_all("td")
                    if len(cols) >= 2:
                        label = cols[0].get_text(strip=True).lower()
                        value = cols[-1].get_text(strip=True)
                        value = re.sub(r"[,%]", "", value).strip()
                        try:
                            val = float(value)
                            if "promoter" in label and "pledge" not in label:
                                data["promoter_holding"] = val
                            elif "pledge" in label:
                                data["promoter_pledge"] = val
                        except ValueError:
                            pass

        # ── Quarterly Results ────────────────────────────
        quarterly = soup.find("section", id="quarters")
        if quarterly:
            table = quarterly.find("table")
            if table:
                rows = table.find_all("tr")
                for row in rows:
                    cols = row.find_all("td")
                    label_th = row.find("th")
                    if not label_th:
                        continue
                    label = label_th.get_text(strip=True).lower()
                    values = []
                    for col in cols[:5]:  # last 4-5 quarters
                        txt = col.get_text(strip=True)
                        txt = re.sub(r"[,%]", "", txt).strip()
                        try:
                            values.append(float(txt))
                        except ValueError:
                            values.append(None)

                    if "net profit" in label or "profit after" in label:
                        data["quarterly_profits"] = values[:4]
                    elif "sales" in label or "revenue" in label:
                        data["quarterly_sales"] = values[:4]

        # ── Growth Rates from P&L section ───────────────
        pl_section = soup.find("section", id="profit-loss")
        if pl_section:
            rows = pl_section.find_all("tr")
            for row in rows:
                th = row.find("th")
                if not th:
                    continue
                label = th.get_text(strip=True).lower()
                cols  = row.find_all("td")
                if len(cols) >= 3:
                    # Use last 3 years to compute growth
                    vals = []
                    for col in cols[-4:]:
                        txt = col.get_text(strip=True)
                        txt = re.sub(r"[,%]", "", txt).strip()
                        try:
                            vals.append(float(txt))
                        except ValueError:
                            pass
                    if len(vals) >= 2 and vals[0] != 0:
                        growth = ((vals[-1] - vals[0]) / abs(vals[0])) * 100
                        if "sales" in label or "revenue" in label:
                            data["revenue_growth_3yr"] = round(growth, 1)
                        elif "net profit" in label or "profit after" in label:
                            data["profit_growth_3yr"] = round(growth, 1)

        time.sleep(2)  # polite delay — avoid rate limiting

    except Exception:
        pass

    return data


# ─────────────────────────────────────────────────────────
#  SOURCE 3 — NSE Website
#  FII / DII monthly buying and selling activity
# ─────────────────────────────────────────────────────────

def fetch_nse_fii_data():
    """
    Fetch FII/DII monthly activity from NSE.
    Returns dict with fii_trend: 'buying' | 'selling' | 'neutral'
    and last 3 months net values.
    """
    data = {
        "fii_trend":        "neutral",
        "fii_last_3months": [],  # net values — positive=buying, negative=selling
        "dii_trend":        "neutral",
        "dii_last_3months": [],
        "nse_ok":           False,
    }

    try:
        url  = "https://www.nseindia.com/api/fiidiiTradeReact"
        session = requests.Session()

        # NSE requires a cookie — get it first
        session.get("https://www.nseindia.com", headers=HEADERS, timeout=10)
        time.sleep(1)

        resp = session.get(url, headers=HEADERS, timeout=10)
        if resp.status_code != 200:
            return data

        raw = resp.json()
        if not raw:
            return data

        data["nse_ok"] = True

        # Last 3 months FII net
        fii_nets = []
        dii_nets = []

        for entry in raw[:3]:  # most recent 3 entries
            try:
                fii_net = float(str(entry.get("disposalBuySell", "0")).replace(",", ""))
                dii_net = float(str(entry.get("diiBuySell", "0")).replace(",", ""))
                fii_nets.append(fii_net)
                dii_nets.append(dii_net)
            except Exception:
                pass

        data["fii_last_3months"] = fii_nets
        data["dii_last_3months"] = dii_nets

        # Determine trend
        if len(fii_nets) >= 2:
            buying_months  = sum(1 for v in fii_nets if v > 0)
            selling_months = sum(1 for v in fii_nets if v < 0)
            if selling_months >= 2:
                data["fii_trend"] = "selling"
            elif buying_months >= 2:
                data["fii_trend"] = "buying"

        if len(dii_nets) >= 2:
            buying_months  = sum(1 for v in dii_nets if v > 0)
            selling_months = sum(1 for v in dii_nets if v < 0)
            if selling_months >= 2:
                data["dii_trend"] = "selling"
            elif buying_months >= 2:
                data["dii_trend"] = "buying"

    except Exception:
        pass

    return data


# ─────────────────────────────────────────────────────────
#  SOURCE 4 — Google News RSS
#  Latest news headlines for sentiment
# ─────────────────────────────────────────────────────────

def fetch_news_sentiment(symbol):
    """
    Fetch latest news for a stock from Google News RSS.
    Returns list of recent headlines and a basic sentiment flag.
    """
    data = {
        "headlines":        [],
        "news_risk":        False,
        "news_flag":        "none",  # none / caution / danger
        "news_ok":          False,
    }

    clean   = symbol.replace(".NS", "").replace(".BO", "")
    query   = f"{clean} NSE stock India"
    rss_url = f"https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"

    # Risk keywords that flag danger
    danger_keywords = [
        "sebi", "fraud", "scam", "fir", "arrested", "ed raid",
        "default", "bankruptcy", "insolvency", "nclt", "ban",
        "manipulation", "fake", "ponzi", "money laundering",
        "promoter sell", "promoter sold", "pledged shares sold",
        "downgrade", "rating cut", "debt restructure",
    ]

    caution_keywords = [
        "loss", "quarterly loss", "revenue decline", "profit fall",
        "management change", "ceo resign", "merger uncertainty",
        "investigation", "notice", "penalty", "fine",
        "disappointing", "miss", "below estimate", "weak quarter",
    ]

    try:
        feed = feedparser.parse(rss_url)
        data["news_ok"] = True

        headlines = []
        for entry in feed.entries[:8]:  # last 8 news items
            title = entry.get("title", "").strip()
            if title:
                headlines.append(title)

        data["headlines"] = headlines

        # Check for risk keywords
        all_text = " ".join(headlines).lower()

        danger_found  = any(kw in all_text for kw in danger_keywords)
        caution_found = any(kw in all_text for kw in caution_keywords)

        if danger_found:
            data["news_risk"] = True
            data["news_flag"] = "danger"
        elif caution_found:
            data["news_flag"] = "caution"

        time.sleep(1)

    except Exception:
        pass

    return data


# ─────────────────────────────────────────────────────────
#  FUNDAMENTAL GRADING ENGINE
#  Combines all 4 sources into GREEN / YELLOW / RED
# ─────────────────────────────────────────────────────────

def grade_fundamentals(yf_data, screener_data, fii_data, news_data):
    """
    Apply all fundamental rules and return a grade.

    Returns:
        grade        : "GREEN" | "YELLOW" | "RED"
        red_flags    : list of hard rejection reasons
        yellow_flags : list of caution reasons
        green_flags  : list of positive confirmations
        summary      : short summary string
        score        : int (-10 to +10)
    """
    red_flags    = []
    yellow_flags = []
    green_flags  = []
    score        = 0

    # ══════════════════════════════════════════════════════
    # HARD REJECTION RULES  →  RED
    # ══════════════════════════════════════════════════════

    # Rule 1 — Debt/Equity > 2.0
    de = screener_data.get("debt_to_equity") or yf_data.get("debt_to_equity")
    if de is not None:
        if de > 2.0:
            red_flags.append(f"Debt/Equity {de:.1f} — dangerously high")
            score -= 3
        elif de > 1.0:
            yellow_flags.append(f"Debt/Equity {de:.1f} — moderate concern")
            score -= 1
        elif de < 0.5:
            green_flags.append(f"Debt/Equity {de:.1f} — clean balance sheet ✓")
            score += 2

    # Rule 2 — Promoter pledge > 50%
    pledge = screener_data.get("promoter_pledge")
    if pledge is not None:
        if pledge > 50:
            red_flags.append(f"Promoter pledge {pledge:.1f}% — crash risk")
            score -= 3
        elif pledge > 25:
            yellow_flags.append(f"Promoter pledge {pledge:.1f}% — moderate risk")
            score -= 1
        elif pledge == 0:
            green_flags.append("No promoter pledge ✓")
            score += 1

    # Rule 3 — Consecutive quarterly losses
    q_profits = screener_data.get("quarterly_profits", [])
    if len(q_profits) >= 3:
        losses = sum(1 for p in q_profits[:3] if p is not None and p < 0)
        if losses >= 3:
            red_flags.append("3 consecutive quarterly losses — business deteriorating")
            score -= 3
        elif losses >= 2:
            yellow_flags.append("2 recent quarterly losses — watch carefully")
            score -= 2
        elif all(p is not None and p > 0 for p in q_profits[:3]):
            green_flags.append("3 consecutive profitable quarters ✓")
            score += 2

    # Rule 4 — Promoter holding < 25%
    promoter = screener_data.get("promoter_holding")
    if promoter is not None:
        if promoter < 25:
            red_flags.append(f"Promoter holding only {promoter:.1f}% — very low conviction")
            score -= 2
        elif promoter > 60:
            green_flags.append(f"Promoter holding {promoter:.1f}% — high conviction ✓")
            score += 2
        elif promoter > 45:
            green_flags.append(f"Promoter holding {promoter:.1f}% — good ✓")
            score += 1

    # Rule 5 — Interest coverage < 1.5x
    ic = screener_data.get("interest_coverage")
    if ic is not None:
        if ic < 1.5:
            red_flags.append(f"Interest coverage {ic:.1f}x — cannot service debt")
            score -= 2
        elif ic > 5:
            green_flags.append(f"Interest coverage {ic:.1f}x — strong ✓")
            score += 1

    # Rule 6 — News danger flag
    if news_data.get("news_flag") == "danger":
        red_flags.append("Danger news detected — SEBI/fraud/default risk")
        score -= 3

    # ══════════════════════════════════════════════════════
    # YELLOW FLAG RULES
    # ══════════════════════════════════════════════════════

    # Rule 7 — FII selling 3+ months
    fii_trend = fii_data.get("fii_trend", "neutral")
    if fii_trend == "selling":
        yellow_flags.append("FII selling for 2+ months — smart money exiting")
        score -= 2
    elif fii_trend == "buying":
        green_flags.append("FII buying for 2+ months ✓")
        score += 2

    # Rule 8 — Revenue growth negative
    rev_growth = screener_data.get("revenue_growth_3yr") or yf_data.get("revenue_growth")
    if rev_growth is not None:
        if rev_growth < 0:
            yellow_flags.append(f"Revenue growth {rev_growth:.1f}% — business shrinking")
            score -= 2
        elif rev_growth > 15:
            green_flags.append(f"Revenue growth {rev_growth:.1f}% — strong ✓")
            score += 2
        elif rev_growth > 8:
            green_flags.append(f"Revenue growth {rev_growth:.1f}% — decent ✓")
            score += 1

    # Rule 9 — PE > 80 (overvalued)
    pe = screener_data.get("pe_ratio") or yf_data.get("pe_ratio")
    if pe is not None and pe > 0:
        if pe > 80:
            yellow_flags.append(f"PE {pe:.1f} — heavily overvalued, limited upside")
            score -= 1
        elif pe > 50:
            yellow_flags.append(f"PE {pe:.1f} — expensive, growth must justify")
            score -= 0
        elif pe < 15:
            green_flags.append(f"PE {pe:.1f} — attractively valued ✓")
            score += 1

    # Rule 10 — News caution flag
    if news_data.get("news_flag") == "caution":
        yellow_flags.append("Caution news — losses/management change/penalty")
        score -= 1

    # ══════════════════════════════════════════════════════
    # POSITIVE CONFIRMATION RULES
    # ══════════════════════════════════════════════════════

    # Rule 11 — ROE > 15%
    roe = screener_data.get("roe") or yf_data.get("roe")
    if roe is not None:
        if roe > 20:
            green_flags.append(f"ROE {roe:.1f}% — highly efficient business ✓")
            score += 2
        elif roe > 15:
            green_flags.append(f"ROE {roe:.1f}% — good return on equity ✓")
            score += 1
        elif roe < 5:
            yellow_flags.append(f"ROE {roe:.1f}% — poor capital efficiency")
            score -= 1

    # Rule 12 — Profit growth > 20%
    profit_growth = screener_data.get("profit_growth_3yr")
    if profit_growth is not None:
        if profit_growth > 20:
            green_flags.append(f"Profit growth {profit_growth:.1f}% — strong earnings ✓")
            score += 2
        elif profit_growth > 10:
            green_flags.append(f"Profit growth {profit_growth:.1f}% — decent ✓")
            score += 1
        elif profit_growth < 0:
            yellow_flags.append(f"Profit growth {profit_growth:.1f}% — earnings declining")
            score -= 1

    # Rule 13 — ROCE > 15%
    roce = screener_data.get("roce")
    if roce is not None:
        if roce > 20:
            green_flags.append(f"ROCE {roce:.1f}% — excellent capital efficiency ✓")
            score += 1

    # Rule 14 — DII buying (additional confirmation)
    dii_trend = fii_data.get("dii_trend", "neutral")
    if dii_trend == "buying" and fii_trend == "buying":
        green_flags.append("Both FII + DII buying — strong institutional interest ✓")
        score += 1

    # ══════════════════════════════════════════════════════
    # FINAL GRADE
    # ══════════════════════════════════════════════════════

    # Hard rejection — any red flag = RED
    if red_flags:
        grade = "RED"
    elif score >= 4:
        grade = "GREEN"
    elif score >= 0:
        grade = "YELLOW" if yellow_flags else "GREEN"
    else:
        grade = "YELLOW"

    # Build summary
    if grade == "RED":
        summary = f"RED — {red_flags[0]}" if red_flags else "RED — fundamental risk"
    elif grade == "GREEN":
        summary = f"GREEN — {green_flags[0]}" if green_flags else "GREEN — fundamentally sound"
    else:
        summary = f"YELLOW — {yellow_flags[0]}" if yellow_flags else "YELLOW — some concerns"

    return {
        "grade":        grade,
        "score":        score,
        "red_flags":    red_flags,
        "yellow_flags": yellow_flags,
        "green_flags":  green_flags,
        "summary":      summary,
    }


# ─────────────────────────────────────────────────────────
#  MASTER FUNDAMENTAL ANALYSER
#  Call this for each stock that passed technical filter
# ─────────────────────────────────────────────────────────

# Cache FII data — same for all stocks, fetch once per session
_fii_cache = None

def analyse_fundamentals(symbol, verbose=False):
    """
    Run complete fundamental analysis on one stock.

    Args:
        symbol  : NSE symbol with .NS (e.g. "RELIANCE.NS")
        verbose : print data fetching progress

    Returns dict with:
        fund_grade      : "GREEN" | "YELLOW" | "RED"
        fund_score      : int
        fund_summary    : str
        red_flags       : list
        yellow_flags    : list
        green_flags     : list
        headlines       : list of news headlines
        pe_ratio        : float
        debt_to_equity  : float
        promoter        : float
        pledge          : float
        roe             : float
        fii_trend       : str
        data_quality    : "full" | "partial" | "minimal"
    """
    global _fii_cache

    clean = symbol.replace(".NS", "").replace(".BO", "")

    # Check cache
    if clean in _cache:
        return _cache[clean]

    if verbose:
        print(f"    Fetching fundamentals for {clean}...")

    result = {
        "fund_grade":     "YELLOW",  # default if data unavailable
        "fund_score":     0,
        "fund_summary":   "Data unavailable — defaulting to YELLOW",
        "red_flags":      [],
        "yellow_flags":   [],
        "green_flags":    [],
        "headlines":      [],
        "pe_ratio":       None,
        "debt_to_equity": None,
        "promoter":       None,
        "pledge":         None,
        "roe":            None,
        "fii_trend":      "neutral",
        "data_quality":   "minimal",
    }

    # ── Fetch from all 4 sources ──────────────────────────
    yf_data       = fetch_yfinance_data(symbol)
    screener_data = fetch_screener_data(clean)
    news_data     = fetch_news_sentiment(clean)

    # FII data — fetch once, reuse for all stocks
    if _fii_cache is None:
        if verbose:
            print("    Fetching FII/DII data from NSE...")
        _fii_cache = fetch_nse_fii_data()
    fii_data = _fii_cache

    # ── Assess data quality ───────────────────────────────
    fields_available = sum([
        screener_data.get("debt_to_equity") is not None,
        screener_data.get("promoter_holding") is not None,
        screener_data.get("roe") is not None,
        len(screener_data.get("quarterly_profits", [])) > 0,
        fii_data.get("nse_ok", False),
    ])

    if fields_available >= 4:
        data_quality = "full"
    elif fields_available >= 2:
        data_quality = "partial"
    else:
        data_quality = "minimal"

    result["data_quality"] = data_quality

    # ── Grade fundamentals ────────────────────────────────
    grading = grade_fundamentals(yf_data, screener_data, fii_data, news_data)

    # ── Populate result ───────────────────────────────────
    result["fund_grade"]     = grading["grade"]
    result["fund_score"]     = grading["score"]
    result["fund_summary"]   = grading["summary"]
    result["red_flags"]      = grading["red_flags"]
    result["yellow_flags"]   = grading["yellow_flags"]
    result["green_flags"]    = grading["green_flags"]
    result["headlines"]      = news_data.get("headlines", [])
    result["fii_trend"]      = fii_data.get("fii_trend", "neutral")

    # Key metrics for display
    result["pe_ratio"]       = (
        screener_data.get("pe_ratio") or yf_data.get("pe_ratio")
    )
    result["debt_to_equity"] = (
        screener_data.get("debt_to_equity") or yf_data.get("debt_to_equity")
    )
    result["promoter"]       = screener_data.get("promoter_holding")
    result["pledge"]         = screener_data.get("promoter_pledge")
    result["roe"]            = (
        screener_data.get("roe") or yf_data.get("roe")
    )

    # Cache result
    _cache[clean] = result

    return result


# ─────────────────────────────────────────────────────────
#  APPLY FUNDAMENTAL GRADE TO TECHNICAL GRADE
# ─────────────────────────────────────────────────────────

def apply_fundamental_to_grade(tech_grade, fund_grade):
    """
    Combine technical grade with fundamental grade.

    Rules:
        Tech A++ + Fund GREEN  = A++  (unchanged)
        Tech A++ + Fund YELLOW = A+   (downgrade one)
        Tech A++ + Fund RED    = SKIP
        Tech A+  + Fund GREEN  = A+
        Tech A+  + Fund YELLOW = A
        Tech A+  + Fund RED    = SKIP
        Tech A   + Fund GREEN  = A
        Tech A   + Fund YELLOW = B
        Tech A   + Fund RED    = SKIP
        Tech B   + Fund GREEN  = B
        Tech B   + Fund YELLOW = B    (no change)
        Tech B   + Fund RED    = SKIP
        Tech C   + any         = SKIP (already weak)
    """
    if fund_grade == "RED":
        return "SKIP"

    if tech_grade == "C":
        return "SKIP"

    grade_ladder = ["B", "A", "A+", "A++"]

    if fund_grade == "YELLOW":
        # Downgrade by one level
        idx = grade_ladder.index(tech_grade) if tech_grade in grade_ladder else 0
        return grade_ladder[max(0, idx - 1)]

    # GREEN — keep technical grade
    return tech_grade


def reset_fii_cache():
    """Reset FII cache — call at start of each new scan session."""
    global _fii_cache
    _fii_cache = None
    _cache.clear()
