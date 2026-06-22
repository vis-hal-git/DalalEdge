# Guru Edge — Indian Stock Scanner 📈

Guru Edge is an AI-powered Indian stock market scanner designed for NSE/BSE swing traders. It combines technical indicators (EMA, RSI, Fibonacci, Trendlines) with automated fundamental screening and LLM-based analysis to shortlist the best large and mid-cap stocks for 5–10% swing trades.

## ✨ Features

The scanner filters stocks through a 6-layer intelligent pipeline:
1. **EMA Signal:** Detects Golden Crosses (50/200) and EMA 20 bounces.
2. **RSI Filter:** Grades momentum based on RSI zone, slope, and oversold recovery.
3. **Trendlines:** Automatically detects scenarios like Higher Highs/Higher Lows, breakout retests, and filters out bull traps.
4. **Fibonacci:** Identifies stocks sitting at key retracement levels (38.2%, 50%, 61.8%) with EMA confluence.
5. **Fundamentals:** Screens out stocks with high promoter pledge, continuous losses, or dangerous debt levels using live data.
6. **LLM Analysis:** Uses OpenAI (`gpt-4o-mini`) to provide an intelligent summary of the fundamental data with Indian sector context (e.g., higher D/E is normal for Banks/NBFCs).

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.9+
- A valid OpenAI API Key (optional, but required for the LLM analysis layer).

### 2. Installation
Clone the repository and install the required dependencies:
```bash
git clone https://github.com/vis-hal-git/DalalEdge.git
cd DalalEdge
pip install -r r.txt
```

### 3. Setup API Key (Optional)
To enable the AI fundamental analysis, add your OpenAI API key as an environment variable:
- **Windows:** `set OPENAI_API_KEY=sk-...`
- **Linux/Mac:** `export OPENAI_API_KEY=sk-...`

Alternatively, you can hardcode it in `llm_analysis.py` under the `OPENAI_API_KEY` variable (not recommended for security).

## 💻 How to Run

### Option 1: Web Dashboard (Recommended)
Guru Edge comes with a beautiful, responsive web UI.
1. Start the Flask server:
   ```bash
   python app.py
   ```
2. Open your browser and navigate to `http://localhost:5000`.
3. Click **Run Scan** in the top navigation bar to trigger a live scan.

### Option 2: Terminal Scanner
You can run the scanner directly from the terminal if you prefer a CLI interface:
```bash
# Run a full scan (Technical + Fundamentals)
python main_scanner.py

# Run a faster scan (Technical analysis only)
python main_scanner.py --no-fundamentals

# Run a quick scan on specific stocks
python main_scanner.py RELIANCE TCS INFY
```

## ⚠️ Disclaimer
Guru Edge is a research and screening tool for educational purposes only. It does not constitute financial advice or a recommendation to buy or sell any security. Stock trading involves substantial risk of loss. Always consult a SEBI-registered financial advisor before making investment decisions.
