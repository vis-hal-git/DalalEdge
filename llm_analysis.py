"""
============================================================
  LLM ANALYSIS MODULE — OpenAI GPT
  Uses OpenAI API to interpret fundamental data
  and give a final GREEN / YELLOW / RED verdict
  with reasoning specific to Indian markets.

  MODEL USED: gpt-4o-mini (fast + cheap + accurate)
  Fallback  : gpt-3.5-turbo if 4o-mini unavailable

  SETUP:
    pip install openai
    Set your API key in one of two ways:
      Option 1 — Environment variable (recommended):
        Windows : set OPENAI_API_KEY=sk-...
        Linux   : export OPENAI_API_KEY=sk-...
      Option 2 — Direct in config.py (see below)

  COST ESTIMATE:
    gpt-4o-mini : ~$0.0002 per stock analysis
    25 stocks   : ~$0.005 per full scan = less than 1 rupee
============================================================
"""

import os
import json
import warnings
import sys
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
warnings.filterwarnings("ignore")

# ── OpenAI import ─────────────────────────────────────────
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("  [WARNING] openai not installed. Run: pip install openai")


# ─────────────────────────────────────────────────────────
#  CONFIGURATION
#  Set your OpenAI API key here OR use environment variable
# ─────────────────────────────────────────────────────────

# Option 1 — Paste your key directly here (less secure)
OPENAI_API_KEY = ""

# Option 2 — Use environment variable (recommended)
# Set in terminal: set OPENAI_API_KEY=sk-...
# The code below will automatically pick it up

# Model to use
OPENAI_MODEL   = "gpt-4o-mini"   # fast, cheap, accurate
FALLBACK_MODEL = "gpt-3.5-turbo" # fallback if 4o-mini unavailable


def get_api_key():
    """
    Get API key from environment variable first,
    then fall back to hardcoded key above.
    """
    env_key = os.environ.get("OPENAI_API_KEY", "")
    if env_key and env_key != "your-openai-api-key-here":
        return env_key
    if OPENAI_API_KEY != "your-openai-api-key-here":
        return OPENAI_API_KEY
    return None


def get_openai_client():
    """Create and return OpenAI client."""
    if not OPENAI_AVAILABLE:
        return None
    api_key = get_api_key()
    if not api_key:
        print("  [ERROR] OpenAI API key not set.")
        print("  Set it in llm_analysis.py or run:")
        print("  Windows: set OPENAI_API_KEY=sk-...")
        print("  Linux  : export OPENAI_API_KEY=sk-...")
        return None
    return OpenAI(api_key=api_key)


# ─────────────────────────────────────────────────────────
#  CALL OPENAI API
# ─────────────────────────────────────────────────────────

def call_openai_api(prompt, max_tokens=600):
    """
    Call OpenAI API.
    Returns response text or None on failure.
    Tries gpt-4o-mini first, falls back to gpt-3.5-turbo.
    """
    client = get_openai_client()
    if not client:
        return None

    for model in [OPENAI_MODEL, FALLBACK_MODEL]:
        try:
            response = client.chat.completions.create(
                model      = model,
                max_tokens = max_tokens,
                temperature= 0.1,  # low temperature = consistent, factual output
                messages   = [
                    {
                        "role":    "system",
                        "content": (
                            "You are an expert Indian stock market analyst "
                            "specialising in NSE/BSE fundamental analysis. "
                            "You always respond in valid JSON only — "
                            "no markdown, no extra text."
                        ),
                    },
                    {
                        "role":    "user",
                        "content": prompt,
                    },
                ],
            )
            return response.choices[0].message.content.strip()

        except Exception as e:
            err = str(e).lower()
            # If model not found, try fallback
            if "model" in err or "not found" in err:
                continue
            # Other errors — log and return None
            break

    return None


# ─────────────────────────────────────────────────────────
#  BUILD PROMPT
# ─────────────────────────────────────────────────────────

def build_fundamental_prompt(symbol, sector, fund_data):
    """
    Build structured prompt for OpenAI to analyse
    fundamental data of an Indian stock.
    """
    pe        = fund_data.get("pe_ratio")
    de        = fund_data.get("debt_to_equity")
    roe       = fund_data.get("roe")
    promoter  = fund_data.get("promoter")
    pledge    = fund_data.get("pledge")
    fii       = fund_data.get("fii_trend", "neutral")
    red       = fund_data.get("red_flags",    [])
    yellow    = fund_data.get("yellow_flags", [])
    green     = fund_data.get("green_flags",  [])
    headlines = fund_data.get("headlines",    [])[:5]
    score     = fund_data.get("fund_score",   0)

    metrics = f"""
Stock    : {symbol} | Sector: {sector}
PE Ratio : {pe       if pe       else 'N/A'}
Debt/Eq  : {de       if de       else 'N/A'}
ROE      : {roe      if roe      else 'N/A'}%
Promoter : {promoter if promoter else 'N/A'}%
Pledge   : {pledge   if pledge   else 'N/A'}%
FII Trend: {fii}
Score    : {score} (rule-based pre-analysis)

Red Flags    : {'; '.join(red)    if red    else 'None'}
Yellow Flags : {'; '.join(yellow) if yellow else 'None'}
Green Flags  : {'; '.join(green)  if green  else 'None'}

Recent News Headlines:
{chr(10).join(f'  - {h}' for h in headlines) if headlines else '  No headlines available'}
"""

    prompt = f"""Analyse this Indian stock for a swing trader targeting 5-10% profit in 1-3 weeks.

{metrics}

Respond in EXACTLY this JSON format — no other text:
{{
  "verdict": "GREEN" or "YELLOW" or "RED",
  "confidence": "high" or "medium" or "low",
  "sector_context": "one sentence — is debt/PE normal for this sector?",
  "key_risk": "single biggest fundamental risk in one sentence",
  "key_strength": "single biggest fundamental strength in one sentence",
  "swing_suitability": "suitable" or "caution" or "avoid",
  "reasoning": "2-3 sentences — overall assessment for swing trading"
}}

Verdict rules:
GREEN  = fundamentally safe, supports price move, swing trade recommended
YELLOW = some concerns, reduce position size, proceed with caution
RED    = do not trade — fundamental risk too high

Important — use Indian market context:
- Banks/NBFCs naturally have high Debt/Equity (2-8 is normal)
- FMCG/Consumer stocks naturally have high PE (40-80 is normal)
- IT stocks: ROE > 20% is excellent
- Pledge > 50% in any sector = serious risk
- FII selling + weak fundamentals = avoid
- FII buying + strong fundamentals = strong GREEN"""

    return prompt


# ─────────────────────────────────────────────────────────
#  PARSE LLM RESPONSE
# ─────────────────────────────────────────────────────────

def parse_llm_response(response_text):
    """
    Parse OpenAI JSON response safely.
    Returns dict with verdict and analysis fields.
    """
    default = {
        "verdict":           "YELLOW",
        "confidence":        "low",
        "sector_context":    "Unable to assess",
        "key_risk":          "Data insufficient for analysis",
        "key_strength":      "Data insufficient for analysis",
        "swing_suitability": "caution",
        "reasoning":         "LLM analysis unavailable — using rule-based grade",
        "llm_ok":            False,
    }

    if not response_text:
        return default

    try:
        clean = response_text.strip()
        # Remove markdown code fences if present
        clean = clean.replace("```json", "").replace("```", "").strip()

        # Extract JSON block
        start = clean.find("{")
        end   = clean.rfind("}") + 1
        if start == -1 or end == 0:
            return default

        parsed           = json.loads(clean[start:end])
        parsed["llm_ok"] = True

        # Validate verdict is one of expected values
        if parsed.get("verdict") not in ["GREEN", "YELLOW", "RED"]:
            parsed["verdict"] = "YELLOW"

        return parsed

    except Exception:
        return default


# ─────────────────────────────────────────────────────────
#  MASTER LLM ANALYSIS FUNCTION
# ─────────────────────────────────────────────────────────

def llm_analyse_stock(symbol, sector, fund_data):
    """
    Send fundamental data to OpenAI GPT for interpretation.

    Args:
        symbol    : stock symbol (e.g. "RELIANCE")
        sector    : sector name (e.g. "Energy")
        fund_data : dict from fundamental_signals.analyse_fundamentals()

    Returns dict:
        llm_verdict      : "GREEN" | "YELLOW" | "RED"
        llm_confidence   : "high" | "medium" | "low"
        llm_key_risk     : str
        llm_key_strength : str
        llm_reasoning    : str
        llm_suitability  : str
        llm_ok           : bool
    """
    result = {
        "llm_verdict":      "YELLOW",
        "llm_confidence":   "low",
        "llm_key_risk":     "Analysis unavailable",
        "llm_key_strength": "Analysis unavailable",
        "llm_reasoning":    "LLM analysis skipped or failed",
        "llm_suitability":  "caution",
        "llm_ok":           False,
    }

    # Build prompt and call API
    prompt   = build_fundamental_prompt(symbol, sector, fund_data)
    response = call_openai_api(prompt, max_tokens=600)
    parsed   = parse_llm_response(response)

    # Map parsed fields to result
    result["llm_verdict"]      = parsed.get("verdict",           "YELLOW")
    result["llm_confidence"]   = parsed.get("confidence",        "low")
    result["llm_key_risk"]     = parsed.get("key_risk",          "N/A")
    result["llm_key_strength"] = parsed.get("key_strength",      "N/A")
    result["llm_reasoning"]    = parsed.get("reasoning",         "N/A")
    result["llm_suitability"]  = parsed.get("swing_suitability", "caution")
    result["llm_ok"]           = parsed.get("llm_ok",            False)

    return result


# ─────────────────────────────────────────────────────────
#  COMBINE RULE-BASED + LLM VERDICT
# ─────────────────────────────────────────────────────────

def combine_verdicts(rule_grade, llm_verdict, llm_confidence):
    """
    Combine rule-based fundamental grade with LLM verdict.

    Logic:
      RED   from either source         = final RED  (safety first)
      Both  GREEN                      = final GREEN
      Low   confidence LLM             = trust rule-based
      One   YELLOW + one GREEN         = YELLOW
      Both  YELLOW                     = YELLOW
    """
    # Safety first — RED from either = RED
    if rule_grade == "RED" or llm_verdict == "RED":
        return "RED"

    # Both GREEN = GREEN
    if rule_grade == "GREEN" and llm_verdict == "GREEN":
        return "GREEN"

    # Low confidence LLM = trust rule-based grade
    if llm_confidence == "low":
        return rule_grade

    # Any YELLOW = YELLOW
    if "YELLOW" in [rule_grade, llm_verdict]:
        return "YELLOW"

    return "GREEN"


# ─────────────────────────────────────────────────────────
#  API KEY TEST UTILITY
# ─────────────────────────────────────────────────────────

def test_api_key():
    """
    Test if OpenAI API key is working.
    Run this first to verify your setup.
    Usage: python llm_analysis.py
    """
    print("\n  Testing OpenAI API connection...")
    api_key = get_api_key()

    if not api_key:
        print("  ✗ No API key found.")
        print("  Set OPENAI_API_KEY in llm_analysis.py or as environment variable.")
        return False

    print(f"  Key found: {api_key[:8]}...{api_key[-4:]}")

    response = call_openai_api(
        'Return only this JSON: {"status": "ok", "message": "API working"}',
        max_tokens=50
    )

    if response and "ok" in response:
        print(f"  ✓ OpenAI API connected successfully — model: {OPENAI_MODEL}")
        return True
    else:
        print(f"  ✗ API call failed. Check your key and internet connection.")
        return False


if __name__ == "__main__":
    test_api_key()