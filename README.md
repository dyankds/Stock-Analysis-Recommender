# 🌙 HalalStock Analyser
**Daily halal stock recommendations for 5–10 year investors · Built for Estonia 🇪🇪**

Adapted from [ZhuLinsen/daily_stock_analysis](https://github.com/ZhuLinsen/daily_stock_analysis) with global markets, Sharia screening, Sukuk support, and mobile PWA alerts.

---

## 🚀 Quick Start (3 minutes)

```bash
# 1. Clone
git clone https://github.com/YOUR_USERNAME/halalstock-analyser
cd halalstock-analyser

# 2. Install
pip install -r requirements.txt

# 3. Run Streamlit dashboard
streamlit run app.py

# 4. Run once to send Telegram alert
python scheduler.py
```

---

## 📱 Mobile App (PWA)

Open `mobile_app.html` in any browser and tap **Add to Home Screen**:
- **Android (Chrome):** Menu → Add to Home Screen
- **iPhone (Safari):** Share → Add to Home Screen

You now have a native-feeling app icon on your phone! Enable Telegram alerts in the Alerts tab for push notifications every weekday.

---

## 🔔 Telegram Alerts Setup

1. Open Telegram → message `@BotFather` → `/newbot`
2. Copy your **Bot Token**
3. Message your bot once
4. Visit: `https://api.telegram.org/bot<TOKEN>/getUpdates`
5. Copy your **Chat ID** (the number next to `"id":`)
6. Add to `.env`:

```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

Test: `python scheduler.py` — you'll get a message like this:

```
🌙 HalalStock Daily Report – 24 Mar 2026
📊 Screened 15 halal stocks | 🟢 BUY signals: 5

🟢 BUY *SP500 Sharia ETF* (SPUS)
  Score: 78/100 | RSI: 42.1 | PE: N/A
  Entry: $56.20 | Stop: $50.58 | 5yr Target: $81.49
```

---

## ⏰ Free Automated Scheduling (GitHub Actions)

```yaml
# .github/workflows/daily.yml
name: Daily HalalStock Analysis
on:
  schedule:
    - cron: '0 15 * * 1-5'   # 18:00 EET (UTC+3) every weekday
  workflow_dispatch:

jobs:
  analyse:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: '3.11'}
      - run: pip install -r requirements.txt
      - run: python scheduler.py
        env:
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          TELEGRAM_CHAT_ID:   ${{ secrets.TELEGRAM_CHAT_ID }}
          EMAIL_SENDER:       ${{ secrets.EMAIL_SENDER }}
          EMAIL_PASSWORD:     ${{ secrets.EMAIL_PASSWORD }}
```

Push to GitHub → Settings → Secrets → add your tokens. **Completely free.**

---

## 🌙 Halal Screening Methodology

Based on **AAOIFI standards** (same as MSCI Islamic, FTSE Shariah):

### Business Activity Screens (Excluded)
- Alcohol production/distribution
- Gambling & casinos
- Tobacco products
- Conventional interest-based banking
- Weapons & defence (primary)
- Pork-related products
- Adult entertainment

### Financial Ratio Screens
| Ratio | Threshold |
|-------|-----------|
| Total Debt / Total Assets | < 33% |
| Interest Income / Revenue | < 5% |
| Accounts Receivable / Assets | < 49% |

---

## 🏦 Sukuk & Islamic ETFs

| Ticker   | Name                        | Exchange | TER   | Type              |
|----------|-----------------------------|----------|-------|-------------------|
| SPUS     | SP500 Sharia ETF            | NYSE     | 0.49% | Islamic Equity    |
| HLAL     | Wahed FTSE Shariah ETF      | NASDAQ   | 0.50% | Islamic Equity    |
| ISDU     | iShares MSCI World Islamic  | NASDAQ   | 0.60% | Islamic Equity    |
| SUKUK.L  | iShares Global Sukuk UCITS  | LSE      | 0.45% | Sukuk (Bond-like) |
| ISEM.L   | Amundi MSCI EM Islamic      | LSE      | 0.45% | EM Islamic        |

---

## 🛒 Where to Buy from Estonia

| Broker              | Rating | Halal ETFs | Sukuk | Best for             |
|---------------------|--------|------------|-------|----------------------|
| Interactive Brokers | ⭐⭐⭐⭐⭐ | ✅         | ✅    | Everything           |
| Lightyear 🇪🇪       | ⭐⭐⭐⭐  | ✅         | ❌    | Baltic-first UX      |
| Trading 212         | ⭐⭐⭐⭐  | ✅         | ❌    | Beginners, fractional|
| Degiro              | ⭐⭐⭐⭐  | ✅         | ✅    | LSE Sukuk access     |
| Saxo Bank           | ⭐⭐⭐⭐  | ✅         | ✅    | Active traders       |

💡 **Estonian Tax Tip:** Use an **Investeerimiskonto** (Investment Account) — all gains are tax-deferred until withdrawal. Perfect for 5–10 year halal compounding.

---

## 📊 Scoring System (0–100)

| Score | Verdict     | Action            |
|-------|-------------|-------------------|
| ≥ 70  | 🟢 BUY      | Consider entering |
| 50–69 | 🟡 WATCH    | Watchlist it      |
| < 50  | 🔴 AVOID    | Skip              |

Score weights:
- 40% Fundamentals (PE, PB, ROE, FCF yield, revenue growth)
- 25% Sharia ratios (debt purity)
- 20% Dividend sustainability
- 15% Technical trend (200 MA, RSI)

---

## ⚠️ Disclaimer

This tool is for educational purposes only. It is not a Sharia ruling (fatwa) and not financial advice. Always consult a qualified Islamic finance scholar or certified platform (Zoya, Islamicly) for formal compliance. Past performance does not guarantee future results.

---

**MIT License · Built on ZhuLinsen/daily_stock_analysis architecture**
