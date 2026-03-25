"""
scheduler.py – Daily background job
Runs analysis and sends alerts via Telegram / Email.
Run via: python scheduler.py
Or triggered automatically by GitHub Actions.
"""

import os, json, time, logging
from datetime import datetime
import yfinance as yf
import pandas as np_pandas  # noqa – just for type hints

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ── Config from environment ──────────────────────────────────────────────────
TELEGRAM_TOKEN  = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT   = os.getenv("TELEGRAM_CHAT_ID", "")
EMAIL_SENDER    = os.getenv("EMAIL_SENDER", "")
EMAIL_PASSWORD  = os.getenv("EMAIL_PASSWORD", "")
EMAIL_RECEIVERS = os.getenv("EMAIL_RECEIVERS", EMAIL_SENDER)

HALAL_TICKERS = [
    "AAPL","MSFT","NVDA","GOOGL","TSM","ASML",  # Tech
    "JNJ","NVO",                                   # Healthcare
    "PG",                                          # Consumer
    "FSLR","ENPH",                                 # Clean Energy
    "SPUS","HLAL","ISDU",                          # Islamic ETFs
]


def analyse_stock(ticker: str) -> dict | None:
    try:
        tkr  = yf.Ticker(ticker)
        hist = tkr.history(period="1y")
        info = tkr.info or {}
        if hist.empty:
            return None
        close  = hist["Close"]
        ma200  = close.rolling(200).mean()
        ma50   = close.rolling(50).mean()
        delta  = close.diff()
        gain   = delta.clip(lower=0).rolling(14).mean()
        loss   = (-delta.clip(upper=0)).rolling(14).mean()
        rs     = gain / loss.replace(0, float('nan'))
        rsi    = float((100 - 100 / (1 + rs)).iloc[-1] or 50)
        price  = float(close.iloc[-1])
        trend  = price > float(ma200.iloc[-1] or 0)
        pe     = info.get("trailingPE") or info.get("forwardPE") or 99
        roe    = (info.get("returnOnEquity") or 0) * 100
        dy     = (info.get("dividendYield") or 0) * 100
        de     = (info.get("debtToEquity") or 0) / 100

        score = 50
        if pe < 25:     score += 10
        if roe > 15:    score += 10
        if trend:       score += 10
        if rsi < 45:    score += 10
        if de < 0.33:   score += 10
        score = min(100, score)

        verdict = "🟢 BUY" if score >= 70 else ("🟡 WATCH" if score >= 50 else "🔴 AVOID")

        return {
            "ticker":  ticker,
            "name":    info.get("shortName", ticker),
            "price":   price,
            "score":   score,
            "verdict": verdict,
            "rsi":     round(rsi, 1),
            "pe":      round(pe, 1) if pe < 999 else "N/A",
            "trend":   "Above 200MA ✅" if trend else "Below 200MA ❌",
            "stop":    round(price * 0.90, 2),
            "target":  round(price * 1.45, 2),
        }
    except Exception as e:
        log.error(f"Error analysing {ticker}: {e}")
        return None


def build_message(results: list[dict]) -> str:
    today = datetime.now().strftime("%d %b %Y")
    buys  = [r for r in results if "BUY" in r["verdict"]]
    lines = [
        f"🌙 *HalalStock Daily Report – {today}*",
        f"📊 Screened {len(results)} halal stocks | 🟢 BUY signals: {len(buys)}",
        "",
    ]
    top = sorted(results, key=lambda x: x["score"], reverse=True)[:5]
    for r in top:
        lines.append(
            f"{r['verdict']} *{r['name']}* ({r['ticker']})\n"
            f"  Score: {r['score']}/100 | RSI: {r['rsi']} | PE: {r['pe']}\n"
            f"  📌 {r['trend']}\n"
            f"  Entry: ${r['price']:.2f} | Stop: ${r['stop']} | 5yr Target: ${r['target']}\n"
        )
    lines.append("_HalalStock Analyser · Not financial advice_")
    return "\n".join(lines)


def send_telegram(message: str) -> bool:
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT:
        log.warning("Telegram credentials not set.")
        return False
    import urllib.request, urllib.parse
    url     = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = urllib.parse.urlencode({
        "chat_id":    TELEGRAM_CHAT,
        "text":       message,
        "parse_mode": "Markdown",
    }).encode()
    try:
        urllib.request.urlopen(url, payload, timeout=15)
        log.info("Telegram alert sent.")
        return True
    except Exception as e:
        log.error(f"Telegram failed: {e}")
        return False


def send_email(message: str) -> bool:
    if not EMAIL_SENDER or not EMAIL_PASSWORD:
        log.warning("Email credentials not set.")
        return False
    import smtplib
    from email.mime.text import MIMEText
    msg            = MIMEText(message)
    msg["Subject"] = f"🌙 HalalStock Daily – {datetime.now().strftime('%d %b %Y')}"
    msg["From"]    = EMAIL_SENDER
    msg["To"]      = EMAIL_RECEIVERS
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
            s.login(EMAIL_SENDER, EMAIL_PASSWORD)
            s.sendmail(EMAIL_SENDER, EMAIL_RECEIVERS.split(","), msg.as_string())
        log.info("Email sent.")
        return True
    except Exception as e:
        log.error(f"Email failed: {e}")
        return False


def run_daily():
    log.info("Starting daily HalalStock analysis…")
    results = []
    for ticker in HALAL_TICKERS:
        log.info(f"  Analysing {ticker}…")
        r = analyse_stock(ticker)
        if r:
            results.append(r)
        time.sleep(0.3)  # rate-limit yfinance

    msg = build_message(results)
    log.info("\n" + msg)

    sent = send_telegram(msg)
    if not sent:
        send_email(msg)

    # Save JSON for Streamlit dashboard to read
    os.makedirs("data", exist_ok=True)
    with open("data/latest_results.json", "w") as f:
        json.dump({"date": datetime.now().isoformat(), "results": results}, f, indent=2)
    log.info("Results saved to data/latest_results.json")


if __name__ == "__main__":
    run_daily()
