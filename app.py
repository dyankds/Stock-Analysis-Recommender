"""
🌙 HalalStock Analyser – Daily Recommendations for 5–10 Year Investors
Built on the architecture of ZhuLinsen/daily_stock_analysis, extended for:
  • Global markets (US, EU, MY, SA)
  • Halal/Sharia screening
  • Sukuk & Islamic ETF discovery
  • Streamlit web + mobile-responsive UI
  • Telegram / Email alerts
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json, os, time
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

# ── Page config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="HalalStock Analyser",
    page_icon="🌙",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS (mobile-responsive + dark crescent theme) ─────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');

  html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

  /* Sidebar */
  section[data-testid="stSidebar"] { background: #0d1117; }
  section[data-testid="stSidebar"] * { color: #e6edf3 !important; }

  /* Cards */
  .metric-card {
    background: linear-gradient(135deg, #161b22, #21262d);
    border: 1px solid #30363d;
    border-radius: 12px;
    padding: 16px 20px;
    margin-bottom: 12px;
  }
  .buy-card   { border-left: 4px solid #3fb950; }
  .hold-card  { border-left: 4px solid #d29922; }
  .avoid-card { border-left: 4px solid #f85149; }
  .halal-badge {
    background: #1f4d2e;
    color: #3fb950;
    border-radius: 6px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: 600;
    margin-left: 6px;
  }
  .sukuk-badge {
    background: #1a3a5c;
    color: #58a6ff;
    border-radius: 6px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: 600;
    margin-left: 6px;
  }
  .score-ring {
    font-size: 2rem;
    font-weight: 700;
  }
  /* Mobile tweaks */
  @media (max-width: 768px) {
    .block-container { padding: 8px !important; }
    .metric-card { padding: 12px; }
  }
  /* Header */
  .app-header {
    background: linear-gradient(90deg, #0d1117, #1a2332);
    border-bottom: 1px solid #30363d;
    padding: 12px 0 8px;
    margin-bottom: 20px;
    text-align: center;
  }
  .app-header h1 { color: #f0f6fc; margin: 0; font-size: 1.8rem; }
  .app-header p  { color: #8b949e; margin: 0; font-size: 0.85rem; }
</style>
""", unsafe_allow_html=True)

# ── Data: Halal Universe ─────────────────────────────────────────────────────
HALAL_UNIVERSE = {
    # === GLOBAL TECH (generally halal – no haram primary revenue) ===
    "AAPL":  {"name":"Apple",           "sector":"Technology",       "market":"US",  "halal":True,  "type":"equity"},
    "MSFT":  {"name":"Microsoft",       "sector":"Technology",       "market":"US",  "halal":True,  "type":"equity"},
    "NVDA":  {"name":"NVIDIA",          "sector":"Technology",       "market":"US",  "halal":True,  "type":"equity"},
    "GOOGL": {"name":"Alphabet",        "sector":"Technology",       "market":"US",  "halal":True,  "type":"equity"},
    "META":  {"name":"Meta Platforms",  "sector":"Technology",       "market":"US",  "halal":True,  "type":"equity"},
    "TSM":   {"name":"TSMC",            "sector":"Semiconductors",   "market":"TW",  "halal":True,  "type":"equity"},
    "ASML":  {"name":"ASML Holding",    "sector":"Semiconductors",   "market":"EU",  "halal":True,  "type":"equity"},
    "SAP":   {"name":"SAP SE",          "sector":"Enterprise SW",    "market":"EU",  "halal":True,  "type":"equity"},
    # === HEALTHCARE ===
    "JNJ":   {"name":"Johnson & Johnson","sector":"Healthcare",      "market":"US",  "halal":True,  "type":"equity"},
    "ABBV":  {"name":"AbbVie",          "sector":"Healthcare",       "market":"US",  "halal":True,  "type":"equity"},
    "NVO":   {"name":"Novo Nordisk",    "sector":"Healthcare",       "market":"EU",  "halal":True,  "type":"equity"},
    "ROG.SW":{"name":"Roche Holding",   "sector":"Healthcare",       "market":"EU",  "halal":True,  "type":"equity"},
    # === CONSUMER (halal – no alcohol/tobacco primary) ===
    "PG":    {"name":"Procter & Gamble","sector":"Consumer Staples", "market":"US",  "halal":True,  "type":"equity"},
    "NESN.SW":{"name":"Nestlé",         "sector":"Consumer Staples", "market":"EU",  "halal":True,  "type":"equity"},
    # === ENERGY / MATERIALS ===
    "FSLR":  {"name":"First Solar",     "sector":"Clean Energy",     "market":"US",  "halal":True,  "type":"equity"},
    "ENPH":  {"name":"Enphase Energy",  "sector":"Clean Energy",     "market":"US",  "halal":True,  "type":"equity"},
    # === ISLAMIC ETFs (Sharia-certified funds) ===
    "SPUS":  {"name":"SP500 Sharia ETF","sector":"Islamic ETF",      "market":"US",  "halal":True,  "type":"islamic_etf"},
    "HLAL":  {"name":"Wahed FTSE Shariah","sector":"Islamic ETF",    "market":"US",  "halal":True,  "type":"islamic_etf"},
    "ISDU":  {"name":"iShares MSCI Wrld Isl","sector":"Islamic ETF", "market":"US",  "halal":True,  "type":"islamic_etf"},
    # === SUKUK (Bond-like, Sharia-compliant) ===
    "SUKUK.L":{"name":"iShares Global Sukuk","sector":"Sukuk",       "market":"LSE", "halal":True,  "type":"sukuk"},
    "ISUS.L":{"name":"iShares MSCI USA Isl","sector":"Islamic ETF",  "market":"LSE", "halal":True,  "type":"sukuk"},
    # === MALAYSIA (Bursa – deeply halal market) ===
    "1155.KL":{"name":"Maybank (Bursa)","sector":"Islamic Banking",  "market":"MY",  "halal":True,  "type":"equity"},
    "5347.KL":{"name":"Tenaga Nasional","sector":"Utilities",        "market":"MY",  "halal":True,  "type":"equity"},
}

HALAL_SCREENS = {
    "No alcohol revenue",
    "No gambling/casinos",
    "No tobacco products",
    "No conventional interest-based banking",
    "No weapons/defence primary",
    "No pork-related products",
    "Debt/Assets < 33%",
    "Interest income < 5% revenue",
}

BROKERS_FOR_ESTONIA = [
    {"name":"Interactive Brokers (IBKR)", "rating":"⭐⭐⭐⭐⭐",
     "url":"https://www.interactivebrokers.eu",
     "fees":"$0 commissions (US), €3 min EU",
     "notes":"Best for EU residents. EU-regulated. Access to US, EU, MY, SG markets. Halal ETFs available.",
     "halal_etfs":True, "sukuk":True},
    {"name":"Lightyear",                  "rating":"⭐⭐⭐⭐",
     "url":"https://lightyear.com",
     "fees":"€1/trade, no custody fee",
     "notes":"Built in Tallinn 🇪🇪. Excellent for Baltic investors. US & EU stocks. No sukuk yet.",
     "halal_etfs":True, "sukuk":False},
    {"name":"Trading 212",               "rating":"⭐⭐⭐⭐",
     "url":"https://trading212.com",
     "fees":"0% commission, spread applies",
     "notes":"Commission-free. Fractional shares. SPUS & HLAL available. No sukuk bonds.",
     "halal_etfs":True, "sukuk":False},
    {"name":"Degiro",                    "rating":"⭐⭐⭐⭐",
     "url":"https://degiro.eu",
     "fees":"€1–3/trade",
     "notes":"Large EU broker. Access to LSE for Sukuk ETFs (SUKUK.L). Good for EU-listed Islamic ETFs.",
     "halal_etfs":True, "sukuk":True},
    {"name":"Saxo Bank",                 "rating":"⭐⭐⭐⭐",
     "url":"https://home.saxo",
     "fees":"0.08%–0.12% per trade",
     "notes":"Premium, good for active traders. Access to MY Bursa. Sukuk accessible via LSE.",
     "halal_etfs":True, "sukuk":True},
]

# ── Helper functions ─────────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def fetch_stock_data(ticker: str, period: str = "2y") -> dict:
    """Fetch OHLCV + fundamentals via yfinance."""
    try:
        tkr = yf.Ticker(ticker)
        hist = tkr.history(period=period)
        info = tkr.info or {}
        return {"hist": hist, "info": info, "ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def compute_technicals(hist: pd.DataFrame) -> dict:
    """MA, RSI, MACD, Bollinger Bands."""
    if hist.empty or len(hist) < 50:
        return {}
    close = hist["Close"]
    ma20  = close.rolling(20).mean()
    ma50  = close.rolling(50).mean()
    ma200 = close.rolling(200).mean()

    # RSI
    delta = close.diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean()
    rs    = gain / loss.replace(0, np.nan)
    rsi   = 100 - (100 / (1 + rs))

    # MACD
    ema12 = close.ewm(span=12).mean()
    ema26 = close.ewm(span=26).mean()
    macd  = ema12 - ema26
    signal= macd.ewm(span=9).mean()

    # Bollinger
    bb_mid = close.rolling(20).mean()
    bb_std = close.rolling(20).std()
    bb_up  = bb_mid + 2 * bb_std
    bb_dn  = bb_mid - 2 * bb_std

    price = float(close.iloc[-1])
    return {
        "price":   price,
        "ma20":    float(ma20.iloc[-1]) if not pd.isna(ma20.iloc[-1]) else None,
        "ma50":    float(ma50.iloc[-1]) if not pd.isna(ma50.iloc[-1]) else None,
        "ma200":   float(ma200.iloc[-1]) if not pd.isna(ma200.iloc[-1]) else None,
        "rsi":     float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50,
        "macd":    float(macd.iloc[-1]) if not pd.isna(macd.iloc[-1]) else 0,
        "macd_sig":float(signal.iloc[-1]) if not pd.isna(signal.iloc[-1]) else 0,
        "bb_up":   float(bb_up.iloc[-1]) if not pd.isna(bb_up.iloc[-1]) else price*1.05,
        "bb_dn":   float(bb_dn.iloc[-1]) if not pd.isna(bb_dn.iloc[-1]) else price*0.95,
        "trend":   "bullish" if price > float(ma200.iloc[-1] or 0) else "bearish",
        "hist":    hist,
    }


def long_term_score(info: dict, tech: dict, asset_type: str) -> dict:
    """
    Score a stock 0–100 for 5–10 year medium-term investing.
    Returns score, verdict, key metrics.
    """
    score = 50  # start neutral
    notes = []

    if asset_type in ("sukuk", "islamic_etf"):
        # ETFs / Sukuk: simpler scoring
        score = 72
        return {"score": score, "verdict": "BUY", "notes": ["Sharia-certified fund/sukuk – low individual company risk", "Diversified exposure"]}

    pe  = info.get("trailingPE") or info.get("forwardPE")
    pb  = info.get("priceToBook")
    roe = info.get("returnOnEquity")
    dy  = info.get("dividendYield") or 0
    de  = info.get("debtToEquity")
    rev_g = info.get("revenueGrowth") or info.get("earningsGrowth") or 0
    fcf = info.get("freeCashflow")
    mc  = info.get("marketCap") or 0
    sector = info.get("sector", "")

    # PE ratio
    if pe:
        if pe < 15:   score += 12; notes.append(f"✅ Low PE {pe:.1f} (undervalued)")
        elif pe < 25: score += 6;  notes.append(f"✅ Fair PE {pe:.1f}")
        elif pe < 40: score -= 5;  notes.append(f"⚠️ High PE {pe:.1f}")
        else:         score -= 12; notes.append(f"❌ Very high PE {pe:.1f}")

    # Price-to-Book
    if pb:
        if pb < 1:    score += 8; notes.append(f"✅ Trades below book (P/B {pb:.1f})")
        elif pb < 3:  score += 4
        elif pb > 10: score -= 6; notes.append(f"⚠️ High P/B {pb:.1f}")

    # ROE
    if roe:
        if roe > 0.20:  score += 10; notes.append(f"✅ Strong ROE {roe*100:.1f}%")
        elif roe > 0.10: score += 5
        elif roe < 0:   score -= 10; notes.append(f"❌ Negative ROE")

    # Revenue growth
    if rev_g:
        if rev_g > 0.20: score += 10; notes.append(f"✅ High growth {rev_g*100:.0f}%")
        elif rev_g > 0.05: score += 5
        elif rev_g < 0:  score -= 8; notes.append(f"⚠️ Declining revenue")

    # Debt/Equity (Sharia limit ~33%)
    if de:
        de_ratio = de / 100
        if de_ratio < 0.33: score += 8; notes.append(f"✅ Low debt/equity {de_ratio:.2f} (Sharia-safe)")
        elif de_ratio < 0.6: score += 2
        else:               score -= 8; notes.append(f"❌ High debt {de_ratio:.2f} (Sharia concern)")

    # Dividend
    if dy > 0.015: score += 5; notes.append(f"✅ Dividend yield {dy*100:.1f}%")

    # FCF
    if fcf and fcf > 0 and mc > 0:
        fcf_yield = fcf / mc
        if fcf_yield > 0.04: score += 8; notes.append(f"✅ Strong FCF yield {fcf_yield*100:.1f}%")

    # Technical overlay
    if tech:
        if tech.get("trend") == "bullish":  score += 5; notes.append("✅ Above 200-day MA")
        if tech.get("rsi", 50) < 40:        score += 5; notes.append("✅ Oversold RSI – entry opportunity")
        elif tech.get("rsi", 50) > 75:      score -= 5; notes.append("⚠️ Overbought RSI")

    score = max(0, min(100, score))

    if score >= 70:   verdict = "BUY"
    elif score >= 50: verdict = "HOLD/WATCH"
    else:             verdict = "AVOID"

    # Entry / stop / target
    price = tech.get("price", 0) if tech else 0
    stop   = round(price * 0.90, 2)  # 10% stop
    target = round(price * 1.45, 2)  # ~45% over 5yr (≈7.7% CAGR)

    return {
        "score":   score,
        "verdict": verdict,
        "notes":   notes[:6],
        "entry":   price,
        "stop":    stop,
        "target":  target,
    }


def render_sparkline(hist: pd.DataFrame, color: str) -> go.Figure:
    fig = go.Figure(go.Scatter(
        x=hist.index[-60:], y=hist["Close"].iloc[-60:],
        mode="lines", line=dict(color=color, width=1.5),
        fill="tozeroy", fillcolor=color.replace(")", ",0.1)").replace("rgb","rgba"),
    ))
    fig.update_layout(
        height=80, margin=dict(l=0,r=0,t=0,b=0),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        showlegend=False,
    )
    return fig


# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🌙 HalalStock Analyser")
    st.caption(f"Updated: {datetime.now().strftime('%d %b %Y %H:%M')}")
    st.divider()

    page = st.radio("Navigation", [
        "📊 Daily Dashboard",
        "🔍 Screen Stocks",
        "🏦 Sukuk & Islamic ETFs",
        "🛒 Where to Buy",
        "🔔 Alert Settings",
        "ℹ️ About Halal Screening",
    ])
    st.divider()

    # Quick filters
    st.markdown("**Filters**")
    show_only_buy     = st.toggle("Show BUY only",        value=False)
    show_sukuk        = st.toggle("Include Sukuk / ETFs", value=True)
    selected_markets  = st.multiselect("Markets", ["US","EU","MY","LSE"], default=["US","EU"])

    st.divider()
    st.markdown("**Alert Channel**")
    tg_token = st.text_input("Telegram Bot Token", type="password",
                              placeholder="Optional – see Alert Settings")
    tg_chat  = st.text_input("Telegram Chat ID", placeholder="e.g. -100123456")


# ── Main content ─────────────────────────────────────────────────────────────

st.markdown("""
<div class="app-header">
  <h1>🌙 HalalStock Daily Analyser</h1>
  <p>Sharia-compliant global stocks · 5–10 year medium-term focus · Daily AI recommendations</p>
</div>
""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
if "📊 Daily Dashboard" in page:
# ════════════════════════════════════════════════════════════════════════════

    # Filter universe
    filtered = {
        k: v for k, v in HALAL_UNIVERSE.items()
        if v["market"] in selected_markets
        and (show_sukuk or v["type"] == "equity")
    }

    # Analyse
    results = []
    with st.spinner("📡 Fetching live prices & fundamentals…"):
        progress = st.progress(0)
        items = list(filtered.items())
        for i, (ticker, meta) in enumerate(items):
            data = fetch_stock_data(ticker)
            if not data["ok"]:
                progress.progress((i+1)/len(items))
                continue
            tech  = compute_technicals(data["hist"])
            score_data = long_term_score(data["info"], tech, meta["type"])
            price_chg  = 0
            if not data["hist"].empty and len(data["hist"]) > 1:
                price_chg = (data["hist"]["Close"].iloc[-1] - data["hist"]["Close"].iloc[-2]) / data["hist"]["Close"].iloc[-2] * 100
            results.append({
                "ticker":  ticker,
                "name":    meta["name"],
                "sector":  meta["sector"],
                "market":  meta["market"],
                "type":    meta["type"],
                **score_data,
                "price_chg": price_chg,
                "hist":    data["hist"],
                "info":    data["info"],
                "tech":    tech,
            })
            progress.progress((i+1)/len(items))
        progress.empty()

    results.sort(key=lambda x: x["score"], reverse=True)
    if show_only_buy:
        results = [r for r in results if r["verdict"] == "BUY"]

    # ── Top picks banner ────────────────────────────────────────────────────
    buys = [r for r in results if r["verdict"] == "BUY"]
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("🟢 BUY signals",   len(buys))
    col2.metric("🟡 HOLD/WATCH",    sum(1 for r in results if r["verdict"]=="HOLD/WATCH"))
    col3.metric("🔴 AVOID",         sum(1 for r in results if r["verdict"]=="AVOID"))
    col4.metric("📊 Stocks scanned",len(results))

    st.divider()
    st.subheader("🏆 Top Recommendations (5–10 Year Horizon)")

    top5 = results[:5]
    for r in top5:
        verdict    = r["verdict"]
        card_class = "buy-card" if verdict=="BUY" else ("hold-card" if verdict=="HOLD/WATCH" else "avoid-card")
        color      = "#3fb950" if verdict=="BUY" else ("#d29922" if verdict=="HOLD/WATCH" else "#f85149")
        badge      = "sukuk-badge" if r["type"] in ("sukuk","islamic_etf") else "halal-badge"
        badge_txt  = "🏦 Sukuk/ETF" if r["type"] in ("sukuk","islamic_etf") else "🌙 Halal"

        with st.container():
            st.markdown(f"""
            <div class="metric-card {card_class}">
              <div style="display:flex;justify-content:space-between;align-items:center">
                <div>
                  <span style="font-size:1.1rem;font-weight:700;color:#f0f6fc">{r['name']} ({r['ticker']})</span>
                  <span class="{badge}">{badge_txt}</span>
                </div>
                <div style="text-align:right">
                  <span class="score-ring" style="color:{color}">{r['score']}</span>
                  <span style="color:#8b949e;font-size:0.8rem">/100</span>
                </div>
              </div>
              <div style="color:{color};font-weight:600;margin:4px 0">{verdict}</div>
              <div style="color:#8b949e;font-size:0.8rem">{r['sector']} · {r['market']} · 
                Entry: ${r['entry']:.2f} | Stop: ${r['stop']:.2f} | 5yr Target: ${r['target']:.2f}</div>
              <div style="margin-top:8px;font-size:0.8rem;color:#c9d1d9">
                {'  '.join(r['notes'][:3])}
              </div>
            </div>
            """, unsafe_allow_html=True)

    # ── Full table ───────────────────────────────────────────────────────────
    st.divider()
    st.subheader("📋 Full Screened Universe")

    df = pd.DataFrame([{
        "Ticker":     r["ticker"],
        "Name":       r["name"],
        "Market":     r["market"],
        "Sector":     r["sector"],
        "Type":       r["type"],
        "Score":      r["score"],
        "Verdict":    r["verdict"],
        "Entry $":    f"{r['entry']:.2f}",
        "5yr Target": f"{r['target']:.2f}",
        "Day %":      f"{r['price_chg']:+.2f}%",
    } for r in results])

    def colour_row(row):
        v = row.get("Verdict", "")
        if v == "BUY":
            color = "#3fb950"
        elif v == "HOLD/WATCH":
            color = "#d29922"
        else:
            color = "#f85149"
        return [f"color: {color}; font-weight: 600" if col == "Verdict" else "" for col in row.index]

    try:
        styled = df.style.apply(colour_row, axis=1)
        st.dataframe(styled, use_container_width=True, hide_index=True)
    except Exception:
        # Fallback: plain dataframe if styling fails
        st.dataframe(df, use_container_width=True, hide_index=True)


# ════════════════════════════════════════════════════════════════════════════
elif "🔍 Screen Stocks" in page:
# ════════════════════════════════════════════════════════════════════════════
    st.subheader("🔍 Custom Stock Halal Screener")
    st.caption("Enter any global ticker. We'll screen it against Sharia principles and score it for 5–10yr value.")

    col1, col2 = st.columns([3,1])
    custom_ticker = col1.text_input("Enter ticker (e.g. AAPL, 5347.KL, SUKUK.L)", placeholder="AAPL")
    run_screen    = col2.button("🔎 Screen it", use_container_width=True)

    if run_screen and custom_ticker:
        with st.spinner("Analysing…"):
            data = fetch_stock_data(custom_ticker.upper().strip())
        if not data["ok"]:
            st.error(f"Could not fetch {custom_ticker}. Check ticker symbol.")
        else:
            info = data["info"]
            tech = compute_technicals(data["hist"])

            # Heuristic halal check
            sector = (info.get("sector") or "").lower()
            industry = (info.get("industry") or "").lower()
            haram_keywords = ["alcohol","tobacco","gambling","casino","bank","insurance",
                              "brewery","distiller","defense","weapon","pork","hotel","adult"]
            is_haram_flag = any(k in sector or k in industry for k in haram_keywords)
            de = info.get("debtToEquity") or 0
            high_debt = (de / 100) > 0.33

            score_data = long_term_score(info, tech, "equity")

            col1, col2, col3 = st.columns(3)
            col1.metric("Sharia Check", "⚠️ Review needed" if is_haram_flag else "✅ Likely Halal")
            col2.metric("Debt/Equity",  f"{de/100:.2f}" + (" ❌" if high_debt else " ✅"))
            col3.metric("LT Score",     f"{score_data['score']}/100")

            st.markdown("### Checklist")
            checks = [
                ("No alcohol/gambling/tobacco sector",  not is_haram_flag),
                ("Debt-to-equity < 33%",                not high_debt),
                ("Positive ROE",                        (info.get("returnOnEquity") or 0) > 0),
                ("Revenue growing",                     (info.get("revenueGrowth") or 0) > 0),
                ("Above 200-day MA",                    tech.get("trend") == "bullish" if tech else False),
                ("RSI not overbought (<70)",            (tech.get("rsi",50) < 70) if tech else True),
            ]
            for label, passed in checks:
                st.write("✅" if passed else "❌", label)

            st.info("**Disclaimer:** This is a heuristic screen, not a certified Sharia ruling. Consult a qualified scholar or use a certified screener like Zoya or Islamicly for formal compliance.")


# ════════════════════════════════════════════════════════════════════════════
elif "🏦 Sukuk" in page:
# ════════════════════════════════════════════════════════════════════════════
    st.subheader("🏦 Sukuk & Islamic ETFs Guide")
    st.markdown("""
    **Sukuk** are Islamic bond-equivalents. Instead of paying interest (riba), sukuk give the holder a 
    *partial ownership* of an underlying asset and pay profit-sharing returns. They are traded like bonds 
    but fully Sharia-compliant.
    """)

    sukuk_list = [
        {"Name":"iShares Global Sukuk UCITS ETF",  "Ticker":"SUKUK.L", "Exchange":"London Stock Exchange",
         "Currency":"USD","TER":"0.45%","AUM":"~$850M",
         "Description":"Tracks the Bloomberg Global Sukuk Float Adj Index. Holds sovereign & corporate sukuk from UAE, Saudi Arabia, Malaysia, Indonesia."},
        {"Name":"Wahed FTSE USA Shariah ETF",      "Ticker":"HLAL",    "Exchange":"NASDAQ",
         "Currency":"USD","TER":"0.50%","AUM":"~$650M",
         "Description":"US equities filtered by FTSE Shariah screening. No financials, alcohol, tobacco, weapons."},
        {"Name":"SP Funds S&P 500 Sharia ETF",     "Ticker":"SPUS",    "Exchange":"NYSE Arca",
         "Currency":"USD","TER":"0.49%","AUM":"~$1.1B",
         "Description":"Largest US-listed Islamic equity ETF. Tracks S&P 500 Sharia index. Monthly Sharia audit."},
        {"Name":"iShares MSCI World Islamic ETF",  "Ticker":"ISDU",    "Exchange":"NASDAQ",
         "Currency":"USD","TER":"0.60%","AUM":"~$400M",
         "Description":"Global developed-market equities screened by MSCI Islamic methodology."},
        {"Name":"Amundi MSCI EM Islamic UCITS ETF","Ticker":"ISEM.L",  "Exchange":"London Stock Exchange",
         "Currency":"USD","TER":"0.45%","AUM":"~$200M",
         "Description":"Emerging market sukuk & equities. Covers Malaysia, Saudi Arabia, UAE, Indonesia."},
    ]

    for s in sukuk_list:
        with st.expander(f"🏦 {s['Name']} ({s['Ticker']})"):
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Exchange", s["Exchange"])
            c2.metric("Currency", s["Currency"])
            c3.metric("TER (fee)", s["TER"])
            c4.metric("AUM", s["AUM"])
            st.write(s["Description"])

    st.divider()
    st.markdown("### 📚 How Sukuk works")
    st.markdown("""
    1. **Issuer** (government or company) creates a Special Purpose Vehicle (SPV)
    2. SPV purchases a real asset (building, infrastructure, etc.)
    3. **Sukuk certificates** are issued to investors representing ownership of that asset
    4. Investors receive **rent / profit-sharing** (not interest)
    5. At maturity, the SPV sells the asset and returns principal

    → Suitable as the **fixed-income / bond portion** of a halal portfolio alongside equity ETFs.
    """)


# ════════════════════════════════════════════════════════════════════════════
elif "🛒 Where to Buy" in page:
# ════════════════════════════════════════════════════════════════════════════
    st.subheader("🛒 Where to Buy – Best Brokers for Estonia 🇪🇪")
    st.caption("EU-regulated brokers you can use from Tallinn with access to halal stocks, Islamic ETFs and Sukuk.")

    for b in BROKERS_FOR_ESTONIA:
        with st.container():
            st.markdown(f"""
            <div class="metric-card buy-card">
              <div style="display:flex;justify-content:space-between">
                <span style="font-size:1.05rem;font-weight:700;color:#f0f6fc">{b['name']}</span>
                <span>{b['rating']}</span>
              </div>
              <div style="color:#8b949e;margin:4px 0;font-size:0.85rem">
                💸 Fees: {b['fees']} &nbsp;|&nbsp; 
                {'🌙 Halal ETFs ✅' if b['halal_etfs'] else '🌙 Halal ETFs ❌'} &nbsp;|&nbsp; 
                {'🏦 Sukuk ✅' if b['sukuk'] else '🏦 Sukuk ❌'}
              </div>
              <div style="color:#c9d1d9;font-size:0.85rem">{b['notes']}</div>
              <div style="margin-top:8px"><a href="{b['url']}" style="color:#58a6ff">{b['url']}</a></div>
            </div>
            """, unsafe_allow_html=True)

    st.divider()
    st.markdown("### 💡 Recommended Setup for an Estonian Halal Investor")
    st.markdown("""
    | Goal | Broker | What to buy |
    |------|--------|-------------|
    | Core halal equities (US) | Lightyear or Trading 212 | SPUS, HLAL |
    | Sukuk (bond replacement) | IBKR or Degiro | SUKUK.L on LSE |
    | Malaysian stocks | IBKR | 5347.KL, 1155.KL |
    | Everything in one place | Interactive Brokers | All of the above |

    **Tax note for Estonia:** Gains held in an **Investment Account (Investeerimiskonto)** are tax-deferred 
    until withdrawal. All major EU brokers support this. Use it to let your halal portfolio compound 
    over your 5–10 year horizon without annual tax drag.
    """)


# ════════════════════════════════════════════════════════════════════════════
elif "🔔 Alert Settings" in page:
# ════════════════════════════════════════════════════════════════════════════
    st.subheader("🔔 Push Alerts & Scheduler")
    st.markdown("Set up daily alerts so you never miss a BUY signal.")

    tab1, tab2, tab3 = st.tabs(["📱 Telegram", "📧 Email", "⏰ Schedule"])

    with tab1:
        st.markdown("""
        #### Setup Telegram Bot
        1. Message `@BotFather` on Telegram → `/newbot`
        2. Copy the **Bot Token** → paste in sidebar
        3. Message your bot once, then run: `https://api.telegram.org/bot<TOKEN>/getUpdates`
        4. Copy your **Chat ID** → paste in sidebar
        5. Click **Send Test Alert** below
        """)
        if st.button("📤 Send Test Alert to Telegram"):
            token   = tg_token
            chat_id = tg_chat
            if token and chat_id:
                import urllib.request, urllib.parse
                msg = "🌙 *HalalStock Test Alert*\n\n✅ Your alerts are working!\n\nYou'll receive daily BUY/SELL signals here every weekday at 18:00."
                url = f"https://api.telegram.org/bot{token}/sendMessage"
                payload = urllib.parse.urlencode({"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"}).encode()
                try:
                    resp = urllib.request.urlopen(url, payload, timeout=10)
                    st.success("✅ Alert sent! Check Telegram.")
                except Exception as e:
                    st.error(f"Failed: {e}")
            else:
                st.warning("Enter Bot Token and Chat ID in the sidebar first.")

    with tab2:
        st.markdown("""
        #### Email Alerts via SMTP
        Configure in your `.env` file:
        ```
        EMAIL_SENDER=you@gmail.com
        EMAIL_PASSWORD=your_app_password   # Gmail App Password
        EMAIL_RECEIVERS=you@gmail.com
        ```
        Then run: `python scheduler.py` or use GitHub Actions for zero-cost hosting.
        """)

    with tab3:
        st.markdown("""
        #### GitHub Actions (Free hosting + scheduling)
        ```yaml
        # .github/workflows/daily.yml
        on:
          schedule:
            - cron: '0 15 * * 1-5'  # 18:00 EET (UTC+3)
        jobs:
          analyse:
            runs-on: ubuntu-latest
            steps:
              - uses: actions/checkout@v4
              - run: pip install -r requirements.txt
              - run: python scheduler.py
                env:
                  TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
                  TELEGRAM_CHAT_ID:   ${{ secrets.TELEGRAM_CHAT_ID }}
        ```
        Push this to GitHub and it runs free every weekday!
        """)


# ════════════════════════════════════════════════════════════════════════════
elif "ℹ️ About" in page:
# ════════════════════════════════════════════════════════════════════════════
    st.subheader("ℹ️ Halal Screening Methodology")
    st.markdown("""
    ### What makes a stock Halal?

    This system applies the **AAOIFI (Accounting & Auditing Organisation for Islamic Financial Institutions)**
    screening methodology, the same standard used by MSCI Islamic, FTSE Shariah and major Islamic ETFs.

    #### Business Activity Screens (Qualitative)
    Stocks are **excluded** if the company's primary business involves:
    """)
    for screen in HALAL_SCREENS:
        st.write("🚫", screen)

    st.markdown("""
    #### Financial Ratio Screens (Quantitative)
    | Ratio | Threshold | Reason |
    |-------|-----------|--------|
    | Total Debt / Total Assets | < 33% | Avoids excessive leverage (riba) |
    | Interest income / Total Revenue | < 5% | Minimises riba income |
    | Accounts Receivable / Total Assets | < 49% | Asset purity |
    | Cash & Interest-bearing securities / Total Assets | < 33% | Capital deployment in real assets |

    #### Scoring System (0–100)
    The 5–10 year composite score weights:
    - **40%** Fundamentals (PE, PB, ROE, FCF yield, revenue growth)
    - **25%** Sharia financial ratios (debt purity, revenue purity)
    - **20%** Dividend sustainability
    - **15%** Technical trend (above 200 MA, RSI positioning)

    **Score ≥ 70 = BUY · 50–69 = HOLD/WATCH · < 50 = AVOID**

    #### Certified Screeners (external)
    - **Zoya App** – stock-by-stock Sharia compliance checker
    - **Islamicly** – AAOIFI-compliant screening platform
    - **MSCI Islamic Index** – institutional grade
    - **Wahed Invest** – managed halal portfolios

    > *This tool is educational and informational only. It is not a Sharia ruling (fatwa). 
    Always cross-check with a qualified Islamic finance scholar or certified platform before investing.*
    """)

# ── Footer ───────────────────────────────────────────────────────────────────
st.divider()
st.caption("🌙 HalalStock Analyser · Built on ZhuLinsen/daily_stock_analysis architecture · MIT License · Not financial advice")
