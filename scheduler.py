"""
scheduler.py – Daily background job
Runs analysis and sends alerts via Telegram / Email.
Run via: python scheduler.py
Or triggered automatically by GitHub Actions.

Features:
  • Grouped by market region (US, EU, CN, MY, SA, GLOBAL ETF)
  • Multi-year price targets: 1yr, 2yr, 3yr, 5yr, 10yr
  • CAGR-based projections using fundamental growth estimates
  • Halal / Sharia screening scores
"""

import os, json, time, logging
from datetime import datetime
import yfinance as yf

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
TELEGRAM_TOKEN  = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT   = os.getenv("TELEGRAM_CHAT_ID", "")
EMAIL_SENDER    = os.getenv("EMAIL_SENDER", "")
EMAIL_PASSWORD  = os.getenv("EMAIL_PASSWORD", "")
EMAIL_RECEIVERS = os.getenv("EMAIL_RECEIVERS", EMAIL_SENDER)

# ── Stock universe grouped by region ─────────────────────────────────────────
MARKET_UNIVERSE = {

    "🇺🇸 US Market": {
        "tickers": ["AAPL", "MSFT", "NVDA", "GOOGL", "META", "JNJ", "PG", "FSLR", "ENPH"],
        "note": "NYSE / NASDAQ — buy via IBKR, Lightyear, Trading 212",
    },

    "🇪🇺 EU Market": {
        "tickers": ["ASML", "SAP", "NVO", "ROG.SW", "NESN.SW"],
        "note": "Euronext / SIX — buy via IBKR, Degiro, Saxo",
    },

    "🇨🇳 CN Market": {
        "tickers": ["BABA", "BIDU", "JD", "PDD"],
        "note": "US-listed ADRs — extra Sharia due diligence required",
    },

    "🇲🇾 MY Market": {
        "tickers": ["1155.KL", "5347.KL", "5183.KL", "1082.KL"],
        "note": "Bursa Malaysia — buy via IBKR or Saxo",
    },

    "🌍 Global Islamic ETFs & Sukuk": {
        "tickers": ["SPUS", "HLAL", "ISDU", "SUKUK.L"],
        "note": "Sharia-certified — SPUS/HLAL/ISDU on NASDAQ, SUKUK.L on LSE",
    },
}

# ── CAGR assumptions per ticker (base, bull, bear) ────────────────────────────
CAGR_PROFILES = {
    "AAPL":    (0.10, 0.14, 0.06),
    "MSFT":    (0.12, 0.16, 0.07),
    "NVDA":    (0.18, 0.28, 0.05),
    "GOOGL":   (0.12, 0.17, 0.06),
    "META":    (0.14, 0.20, 0.04),
    "JNJ":     (0.07, 0.10, 0.04),
    "PG":      (0.07, 0.09, 0.04),
    "FSLR":    (0.15, 0.22, 0.05),
    "ENPH":    (0.16, 0.25, 0.03),
    "ASML":    (0.14, 0.20, 0.07),
    "SAP":     (0.10, 0.14, 0.05),
    "NVO":     (0.14, 0.20, 0.07),
    "ROG.SW":  (0.07, 0.10, 0.03),
    "NESN.SW": (0.06, 0.08, 0.03),
    "BABA":    (0.10, 0.18, 0.01),
    "BIDU":    (0.08, 0.14, 0.01),
    "JD":      (0.09, 0.15, 0.02),
    "PDD":     (0.12, 0.20, 0.02),
    "1155.KL": (0.08, 0.12, 0.04),
    "5347.KL": (0.07, 0.10, 0.03),
    "5183.KL": (0.07, 0.10, 0.03),
    "1082.KL": (0.08, 0.12, 0.04),
    "SPUS":    (0.09, 0.12, 0.05),
    "HLAL":    (0.09, 0.12, 0.05),
    "ISDU":    (0.08, 0.11, 0.04),
    "SUKUK.L": (0.04, 0.06, 0.02),
}
DEFAULT_CAGR = (0.09, 0.13, 0.04)


def project_targets(price: float, ticker: str) -> dict:
    """Project multi-year price targets using CAGR compounding."""
    base, bull, bear = CAGR_PROFILES.get(ticker, DEFAULT_CAGR)
    targets = {}
    for yr in [1, 2, 3, 5, 10]:
        targets[f"{yr}yr_base"] = round(price * (1 + base) ** yr, 2)
        targets[f"{yr}yr_bull"] = round(price * (1 + bull) ** yr, 2)
        targets[f"{yr}yr_bear"] = round(price * (1 + bear) ** yr, 2)
    return targets


def analyse_stock(ticker: str) -> dict | None:
    try:
        tkr  = yf.Ticker(ticker)
        hist = tkr.history(period="1y")
        info = tkr.info or {}
        if hist.empty:
            return None

        close = hist["Close"]
        ma200 = close.rolling(min(200, len(close))).mean()
        delta = close.diff()
        gain  = delta.clip(lower=0).rolling(14).mean()
        loss  = (-delta.clip(upper=0)).rolling(14).mean()
        rs    = gain / loss.replace(0, float("nan"))
        rsi   = float((100 - 100 / (1 + rs)).iloc[-1] or 50)
        price = float(close.iloc[-1])
        trend = price > float(ma200.iloc[-1] or 0)

        pe    = info.get("trailingPE") or info.get("forwardPE") or 99
        roe   = (info.get("returnOnEquity") or 0) * 100
        de    = (info.get("debtToEquity") or 0) / 100
        rev_g = (info.get("revenueGrowth") or 0) * 100

        score = 50
        if pe < 15:    score += 15
        elif pe < 25:  score += 8
        elif pe > 40:  score -= 10
        if roe > 20:   score += 12
        elif roe > 10: score += 6
        if trend:      score += 8
        if rsi < 40:   score += 10
        elif rsi > 75: score -= 8
        if de < 0.33:  score += 8
        elif de > 1.0: score -= 8
        if rev_g > 15: score += 7
        score = max(0, min(100, score))

        verdict = "🟢 BUY" if score >= 70 else ("🟡 WATCH" if score >= 50 else "🔴 AVOID")
        targets = project_targets(price, ticker)

        return {
            "ticker":  ticker,
            "name":    info.get("shortName", ticker),
            "price":   price,
            "score":   score,
            "verdict": verdict,
            "rsi":     round(rsi, 1),
            "pe":      round(pe, 1) if pe < 999 else "N/A",
            "roe":     round(roe, 1),
            "de":      round(de, 2),
            "rev_g":   round(rev_g, 1),
            "trend":   "Above 200MA ✅" if trend else "Below 200MA ❌",
            "stop":    round(price * 0.90, 2),
            **targets,
        }
    except Exception as e:
        log.error(f"Error analysing {ticker}: {e}")
        return None


def format_targets(r: dict) -> str:
    lines = []
    for yr in [1, 2, 3, 5, 10]:
        base = r.get(f"{yr}yr_base", "?")
        bull = r.get(f"{yr}yr_bull", "?")
        bear = r.get(f"{yr}yr_bear", "?")
        lines.append(f"    {yr:>2}yr │ Base ${base:<9} Bull ${bull:<9} Bear ${bear}")
    return "\n".join(lines)


def build_messages(results_by_region: dict) -> list:
    today    = datetime.now().strftime("%d %b %Y")
    all_r    = [r for rs in results_by_region.values() for r in rs]
    total_b  = sum(1 for r in all_r if "BUY" in r["verdict"])
    messages = []

    # Header
    messages.append(
        f"🌙 *HalalStock Daily Report – {today}*\n"
        f"📊 {len(all_r)} stocks · {len(results_by_region)} markets\n"
        f"🟢 BUY: {total_b} · "
        f"🟡 WATCH: {sum(1 for r in all_r if 'WATCH' in r['verdict'])} · "
        f"🔴 AVOID: {sum(1 for r in all_r if 'AVOID' in r['verdict'])}\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )

    # One message per region
    for region_name, results in results_by_region.items():
        if not results:
            continue
        meta  = MARKET_UNIVERSE.get(region_name, {})
        lines = [f"\n*{region_name}*", f"_{meta.get('note', '')}_\n"]

        for r in sorted(results, key=lambda x: x["score"], reverse=True):
            lines.append(
                f"{r['verdict']} *{r['name']}* `({r['ticker']})`\n"
                f"  Score: *{r['score']}/100* │ Price: ${r['price']:.2f}\n"
                f"  RSI: {r['rsi']} │ PE: {r['pe']} │ ROE: {r['roe']}% │ D/E: {r['de']}\n"
                f"  📌 {r['trend']}\n"
                f"  🛑 Stop: ${r['stop']}\n"
                f"  📈 *Targets (base │ bull │ bear)*\n"
                f"{format_targets(r)}\n"
            )
        messages.append("\n".join(lines))

    # Footer
    messages.append(
        "━━━━━━━━━━━━━━━━━━━━\n"
        "⚠️ _Targets are CAGR estimates, not guarantees._\n"
        "_Verify Sharia compliance at zoya.finance_\n"
        "🌙 _HalalStock Analyser – Not financial advice_"
    )
    return messages


def send_telegram(message: str) -> bool:
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT:
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
        return True
    except Exception as e:
        log.error(f"Telegram failed: {e}")
        return False


def send_all_telegram(messages: list) -> bool:
    success = 0
    for msg in messages:
        if send_telegram(msg):
            success += 1
        time.sleep(1)
    log.info(f"Telegram: sent {success}/{len(messages)} messages.")
    return success > 0


def send_email(results_by_region: dict) -> bool:
    if not EMAIL_SENDER or not EMAIL_PASSWORD:
        return False
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    today   = datetime.now().strftime("%d %b %Y")
    all_r   = [r for rs in results_by_region.values() for r in rs]
    total_b = sum(1 for r in all_r if "BUY" in r["verdict"])

    html = f"""<html><body style="font-family:Arial,sans-serif;background:#0d1117;color:#f0f6fc;padding:20px">
    <h2>🌙 HalalStock Daily Report – {today}</h2>
    <p>📊 Screened <b>{len(all_r)}</b> stocks · 🟢 BUY signals: <b>{total_b}</b></p><hr style="border-color:#30363d">"""

    for region_name, results in results_by_region.items():
        if not results:
            continue
        meta = MARKET_UNIVERSE.get(region_name, {})
        html += f"<h3>{region_name}</h3><p style='color:#8b949e;font-size:12px'>{meta.get('note','')}</p>"
        html += """<table style="width:100%;border-collapse:collapse;font-size:12px">
        <tr style="background:#21262d;text-align:center">
          <th style="padding:6px;text-align:left">Stock</th>
          <th>Score</th><th>Verdict</th><th>Price</th><th>Stop</th>
          <th>1yr</th><th>2yr</th><th>3yr</th><th>5yr</th><th>10yr</th>
        </tr>"""
        for r in sorted(results, key=lambda x: x["score"], reverse=True):
            c = "#3fb950" if "BUY" in r["verdict"] else ("#d29922" if "WATCH" in r["verdict"] else "#f85149")
            html += f"""<tr style="border-bottom:1px solid #30363d;text-align:center">
              <td style="padding:6px;text-align:left"><b>{r['name']}</b><br>
                <small style="color:#8b949e">{r['ticker']}</small></td>
              <td style="color:{c}"><b>{r['score']}</b></td>
              <td style="color:{c}">{r['verdict']}</td>
              <td>${r['price']:.2f}</td>
              <td style="color:#f85149">${r['stop']}</td>
              <td>${r.get('1yr_base','?')}</td>
              <td>${r.get('2yr_base','?')}</td>
              <td>${r.get('3yr_base','?')}</td>
              <td>${r.get('5yr_base','?')}</td>
              <td>${r.get('10yr_base','?')}</td>
            </tr>"""
        html += "</table><br>"

    html += """<hr style="border-color:#30363d">
    <p style="color:#8b949e;font-size:11px">⚠️ Not financial advice. Targets are CAGR estimates.
    Verify at <a href="https://zoya.finance" style="color:#58a6ff">zoya.finance</a>.
    🌙 HalalStock Analyser</p></body></html>"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🌙 HalalStock – {today} – {total_b} BUY signals"
    msg["From"]    = EMAIL_SENDER
    msg["To"]      = EMAIL_RECEIVERS
    msg.attach(MIMEText(html, "html"))

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
    results_by_region = {}

    for region_name, config in MARKET_UNIVERSE.items():
        log.info(f"\n── {region_name} ──")
        region_results = []
        for ticker in config["tickers"]:
            log.info(f"  Analysing {ticker}…")
            r = analyse_stock(ticker)
            if r:
                r["region"] = region_name
                region_results.append(r)
            time.sleep(0.4)
        results_by_region[region_name] = region_results

    messages = build_messages(results_by_region)
    for m in messages:
        log.info("\n" + m)

    tg_sent = send_all_telegram(messages)
    if not tg_sent:
        send_email(results_by_region)

    os.makedirs("data", exist_ok=True)
    with open("data/latest_results.json", "w") as f:
        json.dump({
            "date":      datetime.now().isoformat(),
            "results":   [r for rs in results_by_region.values() for r in rs],
            "by_region": results_by_region,
        }, f, indent=2)
    log.info("Saved to data/latest_results.json")


if __name__ == "__main__":
    run_daily()
