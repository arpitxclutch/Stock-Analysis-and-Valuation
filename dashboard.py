import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from data_fetch import get_stock_data
from monte_carlo import run_simulation
from risk_metrics import calculate_metrics
from valuation_engine import run_valuation
from financial_data import FUNDAMENTAL_DATA
from cross_verify import cross_verify_and_correct

st.set_page_config(
    page_title="Equity Lab — Arpit Sharma | IPM 2",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ═════════════════════════════════════════════════════════════════════════════
#  GLOBAL CSS — Modern dark glassmorphism theme
# ═════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    code, pre, .stCode {
        font-family: 'JetBrains Mono', monospace !important;
    }

    /* Main container */
    .block-container { padding: 1.5rem 2rem 2rem 2rem; max-width: 1400px; }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0d0d14 0%, #111122 100%);
        border-right: 1px solid rgba(0,212,255,0.08);
    }
    section[data-testid="stSidebar"] .stSelectbox label,
    section[data-testid="stSidebar"] .stSlider label,
    section[data-testid="stSidebar"] .stTextInput label {
        color: #8b949e !important; font-weight: 500;
    }

    /* Glass card */
    .glass-card {
        background: rgba(255,255,255,0.03);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 16px;
        padding: 24px;
        margin: 12px 0;
        transition: all 0.3s ease;
    }
    .glass-card:hover {
        border-color: rgba(0,212,255,0.2);
        box-shadow: 0 8px 32px rgba(0,212,255,0.06);
    }

    /* Signal banners */
    .signal-banner {
        border-radius: 16px;
        padding: 28px 20px;
        text-align: center;
        margin: 16px 0;
        box-shadow: 0 8px 32px rgba(0,0,0,0.3);
        border: 1px solid rgba(255,255,255,0.05);
    }
    .signal-banner h1 { margin: 0; font-weight: 800; letter-spacing: 1px; }
    .signal-banner h3 { margin-top: 12px; font-weight: 400; opacity: 0.9; }

    /* Metric cards */
    div[data-testid="stMetric"] {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 12px;
        padding: 16px;
        transition: all 0.3s ease;
    }
    div[data-testid="stMetric"]:hover {
        border-color: rgba(0,212,255,0.25);
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(0,212,255,0.08);
    }
    div[data-testid="stMetric"] label { color: #8b949e !important; font-weight: 500; font-size: 13px; }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] { font-weight: 700; }

    /* Tables */
    .stDataFrame, .stTable { border-radius: 12px; overflow: hidden; }

    /* Expanders */
    details { border: 1px solid rgba(255,255,255,0.06) !important; border-radius: 12px !important; }
    details summary { font-weight: 600 !important; }

    /* Info/Warning/Error boxes */
    div[data-testid="stAlert"] { border-radius: 12px; }

    /* Headings */
    h1 { font-weight: 800 !important; }
    h2 { font-weight: 700 !important; color: #e6e6e6 !important; }
    h3 { font-weight: 600 !important; color: #c9d1d9 !important; }

    /* Dividers */
    hr { border-color: rgba(255,255,255,0.06) !important; margin: 24px 0 !important; }

    /* Footer */
    .footer-badge {
        background: linear-gradient(135deg, #0d1117 0%, #161b22 100%);
        border: 1px solid rgba(0,212,255,0.15);
        border-radius: 16px;
        padding: 20px;
        text-align: center;
        margin-top: 40px;
    }

    /* Scrollbar */
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: #0a0a0f; }
    ::-webkit-scrollbar-thumb { background: #222; border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: #333; }

    /* Spinner */
    .stSpinner > div { border-top-color: #00d4ff !important; }

    /* Hide deploy button */
    .stDeployButton { display: none; }
</style>
""", unsafe_allow_html=True)

# ═════════════════════════════════════════════════════════════════════════════
#  DATA: Stock registry & sector map
# ═════════════════════════════════════════════════════════════════════════════

STOCK_INFO = {
    "TATAMOTORS.NS": ("Tata Motors", "Rithin Reji"),
    "M&M.NS":        ("Mahindra & Mahindra", "Vinamra Gupta"),
    "OLECTRA.NS":    ("Olectra Greentech", "Aryan Jha"),
    "ATHERENERG.NS": ("Ather Energy", ""),
    "TSLA":    ("Tesla Inc.", ""),
    "P911.DE": ("Porsche AG", "Gautam Poturaju"),
    "F":       ("Ford Motor Co.", "Archana V"),
    "VOW3.DE": ("Volkswagen AG", "Sunidhi Datar"),
    "HYMTF":   ("Hyundai Motor", "Samarth Rao"),
    "APOLLOTYRE.NS": ("Apollo Tyres", "Anirudh Agarwal"),
    "MRF.NS":        ("MRF Ltd.", "Shrisai Hari"),
    "JKTYRE.NS":     ("JK Tyre & Industries", "Swayam Panigrahi"),
    "CEATLTD.NS":    ("CEAT Ltd.", "Harshini Venkat"),
    "SBIN.NS":      ("State Bank of India", "Anoushka Gadhwal"),
    "HDFCBANK.NS":  ("HDFC Bank", "Ryan Kidangan"),
    "ICICIBANK.NS": ("ICICI Bank", "Himangshi Bose"),
    "AXISBANK.NS":  ("Axis Bank", "Bismaya Nayak"),
    "LAURUSLABS.NS": ("Laurus Labs", "Satvik Sharma"),
    "AUROPHARMA.NS": ("Aurobindo Pharma", "Arya Mukharjee"),
    "SUNPHARMA.NS":  ("Sun Pharma", "Yogesh Bolkotagi"),
    "DIVISLAB.NS":   ("Divi's Laboratories", "Bhavansh Madan"),
    "ITC.NS":       ("ITC Ltd.", "Gajanan Kudva / Srutayus Das"),
    "CHALET.NS":    ("Chalet Hotels", "Shreya Joshi"),
    "MHRIL.NS":     ("Mahindra Holidays", "Gowri Shetty"),
    "INDHOTEL.NS":  ("Indian Hotels Co.", "Aarohi Jain"),
    "HUL.NS":       ("Hindustan Unilever", "Suhina Sarkar"),
    "NESTLEIND.NS": ("Nestlé India", "Saaraansh Razdan"),
    "SHREECEM.NS":   ("Shree Cement", "Anjor Singh"),
    "ULTRACEMCO.NS": ("UltraTech Cement", "Rahul Gowda"),
    "DALBHARAT.NS":  ("Dalmia Bharat", "Kushagra Shukla"),
    "RAMCOCEM.NS":   ("Ramco Cements", "Grace Rebecca David"),
    "ABSLAMC.NS":    ("Aditya Birla Sun Life AMC", "Pallewar Pranav"),
    "HDFCAMC.NS":    ("HDFC AMC", "Rittika Saraswat"),
    "NAM-INDIA.NS":  ("Nippon Life India AMC", "Sam Phillips"),
    "UTIAMC.NS":     ("UTI AMC", "Abhinav Singh"),
    "NVDA":  ("NVIDIA Corp.", "Sijal Verma"),
    "MSFT":  ("Microsoft Corp.", "Gurleen Kaur"),
    "GOOGL": ("Alphabet Inc.", "Anugraha AB"),
    "META":  ("Meta Platforms", "Senjuti Pal"),
    "IBM":   ("IBM Corp.", "Biba Pattnaik"),
    "ASML":  ("ASML Holding", "Adaa Gujral"),
    "INTC":  ("Intel Corp.", "Aditi Ranjan"),
    "QCOM":  ("Qualcomm Inc.", "Arpit Sharma"),
    "CRM":   ("Salesforce Inc.", "Rishit Hotchandani"),
    "PLTR":  ("Palantir Technologies", "Krrish Bahuguna"),
    "CRWD":  ("CrowdStrike Holdings", "Ashi Beniwal"),
    "WBD":  ("Warner Bros. Discovery", "Dhairya Vanker"),
    "NFLX": ("Netflix Inc.", "Hiya Phatnani"),
    "DIS":  ("Walt Disney Co.", "Siya Sharma"),
    "PARA": ("Paramount Global", "Tanvi Gujarathi"),
    "PG":   ("Procter & Gamble", "Nayan Kanchan"),
    "WMT":  ("Walmart Inc.", ""),
    "LMT": ("Lockheed Martin", "Siddhant Mehta"),
    "GD":  ("General Dynamics", "Shlok Pratap Singh"),
    "NOC": ("Northrop Grumman", "Harshdeep Roshan"),
    "RTX": ("RTX Corporation", "Prandeep Poddar"),
}

def _is_indian(t): return t.endswith(".NS") or t.endswith(".BO")
def _cur(t): return "₹" if _is_indian(t) else "$"
def _fmt(v, t): return f"{_cur(t)}{v:,.2f}"

GLOBAL_STOCKS = {
    "🚗 Auto (India)":              ["TATAMOTORS.NS", "M&M.NS", "OLECTRA.NS", "ATHERENERG.NS"],
    "🌍 Auto (Global)":             ["TSLA", "P911.DE", "F", "VOW3.DE", "HYMTF"],
    "🛞 Tyres (India)":             ["APOLLOTYRE.NS", "MRF.NS", "JKTYRE.NS", "CEATLTD.NS"],
    "🏦 Banking (India)":           ["SBIN.NS", "HDFCBANK.NS", "ICICIBANK.NS", "AXISBANK.NS"],
    "💊 Pharma (India)":            ["LAURUSLABS.NS", "AUROPHARMA.NS", "SUNPHARMA.NS", "DIVISLAB.NS"],
    "🏨 Consumer & Hotels (India)": ["ITC.NS", "CHALET.NS", "MHRIL.NS", "INDHOTEL.NS", "HUL.NS", "NESTLEIND.NS"],
    "🧱 Cement (India)":            ["SHREECEM.NS", "ULTRACEMCO.NS", "DALBHARAT.NS", "RAMCOCEM.NS"],
    "📈 AMC / Finance (India)":     ["ABSLAMC.NS", "HDFCAMC.NS", "NAM-INDIA.NS", "UTIAMC.NS"],
    "💻 Tech (US/Global)":          ["NVDA", "MSFT", "GOOGL", "META", "IBM", "ASML", "INTC", "QCOM", "CRM", "PLTR", "CRWD"],
    "🎬 Media & Consumer (US)":     ["WBD", "NFLX", "DIS", "PARA", "PG", "WMT"],
    "🛡️ Defense (US)":              ["LMT", "GD", "NOC", "RTX"],
}

def _display_name(t):
    info = STOCK_INFO.get(t)
    if info:
        c, p = info
        return f"{c} ({p})" if p else c
    return t

# Sector lookup (strip emoji from key for cross_verify)
SECTOR_CLEAN = {}
TICKER_TO_SECTOR = {}
for sec, tickers in GLOBAL_STOCKS.items():
    clean = sec.split(" ", 1)[1] if " " in sec else sec
    SECTOR_CLEAN[sec] = clean
    for t in tickers:
        TICKER_TO_SECTOR[t] = clean

# Plotly template
PLOTLY_LAYOUT = dict(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", color="#c9d1d9"),
    margin=dict(l=40, r=40, t=50, b=40),
    legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor="rgba(255,255,255,0.05)"),
)

# ═════════════════════════════════════════════════════════════════════════════
#  HEADER
# ═════════════════════════════════════════════════════════════════════════════

st.markdown("""
<div style="text-align:center;padding:10px 0 0 0;">
    <h1 style="font-size:2.6rem;font-weight:900;margin:0;
               background:linear-gradient(135deg,#00d4ff 0%,#7b2ff7 50%,#ff6b6b 100%);
               -webkit-background-clip:text;-webkit-text-fill-color:transparent;
               background-clip:text;">
        🏛️ Institutional Equity Lab
    </h1>
    <p style="color:#58a6ff;font-size:1.05rem;margin:6px 0 0 0;font-weight:500;letter-spacing:0.5px;">
        Damodaran DCF Valuation &nbsp;·&nbsp; Monte Carlo Simulation &nbsp;·&nbsp; Cross-Verification
    </p>
    <p style="color:#484f58;font-size:0.85rem;margin:4px 0 0 0;">
        Built by <b style="color:#8b949e;">Arpit Sharma</b> &nbsp;|&nbsp; IPM 2
    </p>
</div>
""", unsafe_allow_html=True)

st.markdown("---")

# ═════════════════════════════════════════════════════════════════════════════
#  SIDEBAR
# ═════════════════════════════════════════════════════════════════════════════

st.sidebar.markdown("""
<div style="text-align:center;padding:10px 0 20px 0;">
    <p style="font-size:1.3rem;font-weight:800;margin:0;
              background:linear-gradient(90deg,#00d4ff,#7b2ff7);
              -webkit-background-clip:text;-webkit-text-fill-color:transparent;">
        EQUITY LAB
    </p>
    <p style="color:#484f58;font-size:0.75rem;margin:2px 0 0 0;">Arpit Sharma · IPM 2</p>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("### 🎯 Market Selection")
category = st.sidebar.selectbox("Sector", list(GLOBAL_STOCKS.keys()), label_visibility="collapsed")
ticker_list = GLOBAL_STOCKS[category]
display_list = [_display_name(t) for t in ticker_list]
selected_display = st.sidebar.selectbox("Company", display_list)
selected_ticker = ticker_list[display_list.index(selected_display)]
custom_ticker = st.sidebar.text_input("Custom Ticker", placeholder="e.g. RELIANCE.NS")
ticker = custom_ticker.strip() if custom_ticker.strip() else selected_ticker
cur = _cur(ticker)

st.sidebar.markdown("---")
st.sidebar.markdown("### ⚙️ Simulation")
sims = st.sidebar.slider("Simulations", 5000, 50000, 10000, step=1000)
years = st.sidebar.slider("Horizon (Years)", 0.5, 10.0, 1.0, step=0.5)
crash_scenario = st.sidebar.slider("Market Stress %", 0, 50, 0)

# ═════════════════════════════════════════════════════════════════════════════
#  MAIN CONTENT
# ═════════════════════════════════════════════════════════════════════════════

try:
    info = STOCK_INFO.get(ticker, (ticker, ""))
    co_name, person = info
    person_html = f"""<span style="background:rgba(0,212,255,0.1);color:#00d4ff;padding:4px 12px;
                       border-radius:20px;font-size:0.85rem;font-weight:500;margin-left:12px;">
                       👤 {person}</span>""" if person else ""

    st.markdown(f"""
    <div class="glass-card" style="padding:20px 28px;">
        <h2 style="margin:0;font-size:1.8rem;">{co_name}
            <code style="background:rgba(0,212,255,0.08);color:#00d4ff;padding:4px 10px;
                         border-radius:8px;font-size:0.9rem;margin-left:8px;">{ticker}</code>
            {person_html}
        </h2>
    </div>
    """, unsafe_allow_html=True)

    has_fundamentals = ticker in FUNDAMENTAL_DATA
    val = None
    intrinsic = 0

    # ═══════════════════════════════════════════════════════════════════════
    #  STEP 1-3: DAMODARAN DCF
    # ═══════════════════════════════════════════════════════════════════════
    if has_fundamentals:
        with st.spinner("Running Damodaran DCF Valuation…"):
            val = run_valuation(ticker)

        mc_sel = val["model_selection"]
        vd = val["valuation_detail"]
        fd = val["fundamentals"]
        comp = val["computed"]
        intrinsic = val["intrinsic_value_per_share"]
        unit = fd["unit"]

        # ── STEP 1 ─────────────────────────────────────────────────────
        st.markdown("""
        <div style="display:flex;align-items:center;gap:10px;margin:24px 0 8px 0;">
            <span style="background:linear-gradient(135deg,#00d4ff,#7b2ff7);color:white;
                         padding:6px 14px;border-radius:20px;font-weight:700;font-size:0.85rem;">STEP 1</span>
            <span style="font-size:1.25rem;font-weight:700;color:#e6e6e6;">Choosing the Right Valuation Model</span>
        </div>
        """, unsafe_allow_html=True)
        st.caption("Replicates Damodaran's `model1.xls` — every question answered with our data")

        qa = mc_sel["qa_inputs"]
        with st.expander("📝 Model Inputs — Full Q&A", expanded=True):
            cs = ""
            for item in qa:
                s = item.get("section", "")
                if s and s != cs:
                    st.markdown(f"<p style='color:#58a6ff;font-weight:700;margin:16px 0 6px 0;font-size:0.95rem;'>"
                                f"━━ {s} ━━</p>", unsafe_allow_html=True)
                    cs = s
                if "formula" in item:
                    st.markdown(f"**{item['question']}**")
                    st.code(item["formula"], language="text")
                    st.markdown(f"<p style='color:#00d4ff;font-weight:600;'>= {item['answer']}</p>",
                                unsafe_allow_html=True)
                else:
                    st.markdown(f"<p style='margin:4px 0;'><span style='color:#8b949e;'>{item['question']}</span>"
                                f" → <code style='color:#00d4ff;'>{item['answer']}</code></p>",
                                unsafe_allow_html=True)
                if "note" in item:
                    st.caption(f"ℹ️ {item['note']}")

        with st.expander("🧠 Decision Trail — How We Arrived at the Model", expanded=True):
            for i, step in enumerate(mc_sel["decision_trail"], 1):
                st.markdown(f"<p style='margin:6px 0;'><span style='color:#58a6ff;font-weight:700;'>{i}.</span> {step}</p>",
                            unsafe_allow_html=True)

        # Model selector output card
        st.markdown(f"""
        <div class="glass-card" style="border-color:rgba(0,212,255,0.2);background:rgba(0,212,255,0.02);">
            <p style="color:#00d4ff;font-weight:700;font-size:0.9rem;margin:0 0 12px 0;letter-spacing:1px;">
                📐 OUTPUT FROM MODEL SELECTOR</p>
            <table style="width:100%;color:#e6e6e6;font-size:0.95rem;">
                <tr><td style="padding:8px 0;color:#8b949e;width:40%;">Type of Model</td>
                    <td style="padding:8px 0;font-weight:600;">{mc_sel['model_type']}</td></tr>
                <tr><td style="padding:8px 0;color:#8b949e;">Earnings Level</td>
                    <td style="padding:8px 0;font-weight:600;">{mc_sel['earnings_level']}</td></tr>
                <tr><td style="padding:8px 0;color:#8b949e;">Cashflows to Discount</td>
                    <td style="padding:8px 0;font-weight:600;">{mc_sel['cashflow_type']}</td></tr>
                <tr><td style="padding:8px 0;color:#8b949e;">Growth Pattern</td>
                    <td style="padding:8px 0;font-weight:600;">{mc_sel['growth_pattern']}</td></tr>
                <tr style="background:rgba(0,212,255,0.05);border-radius:8px;">
                    <td style="padding:10px 0;color:#00d4ff;font-weight:600;">Selected Model</td>
                    <td style="padding:10px 0;font-weight:700;color:#00d4ff;font-size:1.05rem;">
                        {mc_sel['model_description']}
                        <code style="margin-left:8px;font-size:0.8rem;">{mc_sel['model_code']}.xls</code></td></tr>
            </table>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        # ── STEP 2 ─────────────────────────────────────────────────────
        st.markdown("""
        <div style="display:flex;align-items:center;gap:10px;margin:8px 0 16px 0;">
            <span style="background:linear-gradient(135deg,#00d4ff,#7b2ff7);color:white;
                         padding:6px 14px;border-radius:20px;font-weight:700;font-size:0.85rem;">STEP 2</span>
            <span style="font-size:1.25rem;font-weight:700;color:#e6e6e6;">Annual Report Data (DCF Inputs)</span>
        </div>
        """, unsafe_allow_html=True)

        i1, i2, i3 = st.columns(3)
        with i1:
            st.markdown("""<p style="color:#00d4ff;font-weight:700;font-size:0.9rem;letter-spacing:0.5px;
                            margin-bottom:8px;">📄 INCOME STATEMENT</p>""", unsafe_allow_html=True)
            for label, key in [("Revenue","revenue"),("EBIT","ebit"),("Net Income","net_income")]:
                st.write(f"{label}: **{cur}{fd[key]:,.0f} {unit}**")
            st.write(f"EPS: **{cur}{comp['EPS']:,.2f}**")
            st.write(f"Tax Rate: **{fd['tax_rate']:.0%}**")
        with i2:
            st.markdown("""<p style="color:#7b2ff7;font-weight:700;font-size:0.9rem;letter-spacing:0.5px;
                            margin-bottom:8px;">💰 CASH FLOW</p>""", unsafe_allow_html=True)
            for label, key in [("Depreciation","depreciation"),("CapEx","capex"),("ΔWC","delta_wc"),("Dividends","dividends_total")]:
                st.write(f"{label}: **{cur}{fd[key]:,.0f} {unit}**")
            st.markdown(f"<p style='color:#00d4ff;font-weight:700;'>FCFE: {cur}{comp['FCFE_total']:,.0f} {unit} &nbsp;|&nbsp; "
                        f"FCFF: {cur}{comp['FCFF_total']:,.0f} {unit}</p>", unsafe_allow_html=True)
        with i3:
            st.markdown("""<p style="color:#ff6b6b;font-weight:700;font-size:0.9rem;letter-spacing:0.5px;
                            margin-bottom:8px;">🏗️ BALANCE SHEET & RATES</p>""", unsafe_allow_html=True)
            st.write(f"Debt: **{cur}{fd['total_debt']:,.0f} {unit}** | Cash: **{cur}{fd['cash']:,.0f} {unit}**")
            st.write(f"Shares: **{fd['shares_outstanding']:,.2f} {unit}**")
            st.write(f"D/E Ratio: **{fd['debt_ratio']:.1%}** | Beta: **{fd['beta']:.2f}**")
            st.write(f"Ke: **{fd['cost_of_equity']:.1%}** | WACC: **{fd['wacc']:.1%}**")
            st.write(f"Rf: **{fd['risk_free_rate']:.1%}** | ERP: **{fd['erp']:.1%}**")

        st.markdown("---")

        # ── STEP 3 ─────────────────────────────────────────────────────
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:10px;margin:8px 0 16px 0;">
            <span style="background:linear-gradient(135deg,#00d4ff,#7b2ff7);color:white;
                         padding:6px 14px;border-radius:20px;font-weight:700;font-size:0.85rem;">STEP 3</span>
            <span style="font-size:1.25rem;font-weight:700;color:#e6e6e6;">{vd.get('model','DCF')} — Year-by-Year</span>
        </div>
        """, unsafe_allow_html=True)

        if "year_by_year" in vd and vd["year_by_year"]:
            df_yby = pd.DataFrame(vd["year_by_year"])
            skip_cols = ("Year","Phase","Growth","Growth Rate","Expected Growth","Cost of Equity","WACC")
            for col in df_yby.columns:
                if col in skip_cols: continue
                if df_yby[col].dtype in [np.float64, np.int64, float, int]:
                    df_yby[col] = df_yby[col].apply(lambda x: f"{cur}{x:,.2f}" if abs(x)>=1 else f"{x:.6f}")
            st.dataframe(df_yby, use_container_width=True, hide_index=True)

        if "formula" in vd:
            st.code(vd["formula"], language="text")

        if "summary" in vd:
            with st.expander("📊 Valuation Summary Table", expanded=False):
                rows = []
                for k, v in vd["summary"].items():
                    if isinstance(v, float):
                        f_ = f"{v:.2%}" if abs(v)<1 and v!=0 else f"{cur}{v:,.2f}"
                    else:
                        f_ = f"{v:,}" if isinstance(v, int) else str(v)
                    rows.append({"Item": k, "Value": f_})
                st.table(pd.DataFrame(rows))

        if intrinsic > 0:
            st.markdown(f"""
            <div style="background:linear-gradient(135deg,rgba(0,212,255,0.08) 0%,rgba(123,47,247,0.08) 100%);
                        padding:30px;border-radius:16px;text-align:center;margin:20px 0;
                        border:2px solid rgba(0,212,255,0.3);
                        box-shadow:0 0 40px rgba(0,212,255,0.08);">
                <p style="color:#8b949e;font-size:0.9rem;margin:0;font-weight:500;letter-spacing:1px;">INTRINSIC VALUE PER SHARE</p>
                <h1 style="margin:8px 0;font-size:2.8rem;font-weight:900;
                           background:linear-gradient(90deg,#00d4ff,#7b2ff7);
                           -webkit-background-clip:text;-webkit-text-fill-color:transparent;">{_fmt(intrinsic,ticker)}</h1>
                <p style="color:#484f58;margin:0;font-size:0.85rem;">
                    Model: {mc_sel['model_description']} · <code>{mc_sel['model_code']}.xls</code></p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.warning("⚠️ Intrinsic value ≤ 0. Inputs may need adjustment.")

        st.markdown("---")
    else:
        st.info("ℹ️ No fundamental data for DCF. Showing Monte Carlo simulation only.")

    # ═══════════════════════════════════════════════════════════════════════
    #  STEP 4: MONTE CARLO
    # ═══════════════════════════════════════════════════════════════════════
    st.markdown("""
    <div style="display:flex;align-items:center;gap:10px;margin:8px 0 16px 0;">
        <span style="background:linear-gradient(135deg,#ff6b6b,#ff9a56);color:white;
                     padding:6px 14px;border-radius:20px;font-weight:700;font-size:0.85rem;">STEP 4</span>
        <span style="font-size:1.25rem;font-weight:700;color:#e6e6e6;">Monte Carlo Risk Simulation</span>
    </div>
    """, unsafe_allow_html=True)

    with st.spinner(f"Fetching market data for {ticker}…"):
        s0, auto_mu, auto_sigma, source_name = get_stock_data(ticker)
    st.sidebar.success(f"✅ {source_name}")

    adjusted_mu = auto_mu - (crash_scenario / 100)
    with st.spinner("Running Monte Carlo…"):
        paths, low_band, high_band = run_simulation(s0, adjusted_mu, auto_sigma, years, n_sims=sims)
    final_prices = paths[-1]
    metrics = calculate_metrics(final_prices, s0, adjusted_mu, auto_sigma)

    # Signal
    if val and intrinsic > 0:
        mos = (intrinsic - s0) / s0
        if mos > 0.20:
            sig_gradient = "linear-gradient(135deg,#0d4f1e 0%,#1b8a2a 100%)"
            sig_border = "rgba(27,138,42,0.5)"
            vt = "🟢 UNDERVALUED — BUY"
        elif mos > -0.10:
            sig_gradient = "linear-gradient(135deg,#4a3500 0%,#c47f17 100%)"
            sig_border = "rgba(196,127,23,0.5)"
            vt = "🟡 FAIRLY VALUED — HOLD"
        else:
            sig_gradient = "linear-gradient(135deg,#4a0d0d 0%,#b52a2a 100%)"
            sig_border = "rgba(181,42,42,0.5)"
            vt = "🔴 OVERVALUED — AVOID"
        our_signal = vt
        subtitle = f"Market: {_fmt(s0,ticker)} &nbsp;·&nbsp; DCF: {_fmt(intrinsic,ticker)} &nbsp;·&nbsp; Margin: {mos:+.1%} &nbsp;·&nbsp; MC ({years}yr): {_fmt(metrics['Expected Price'],ticker)}"
    else:
        our_signal = metrics["Signal"]
        if "BUY" in our_signal:
            sig_gradient = "linear-gradient(135deg,#0d4f1e 0%,#1b8a2a 100%)"
            sig_border = "rgba(27,138,42,0.5)"
        elif "HOLD" in our_signal:
            sig_gradient = "linear-gradient(135deg,#4a3500 0%,#c47f17 100%)"
            sig_border = "rgba(196,127,23,0.5)"
        else:
            sig_gradient = "linear-gradient(135deg,#4a0d0d 0%,#b52a2a 100%)"
            sig_border = "rgba(181,42,42,0.5)"
        vt = our_signal
        subtitle = f"MC Target ({years}yr): {_fmt(metrics['Expected Price'],ticker)}"

    st.markdown(f"""
    <div class="signal-banner" style="background:{sig_gradient};border-color:{sig_border};">
        <h1 style="color:white;font-size:2rem;">{vt}</h1>
        <h3 style="color:rgba(255,255,255,0.85);font-size:1rem;">{subtitle}</h3>
    </div>
    """, unsafe_allow_html=True)

    # Metrics row
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Current Price", _fmt(s0, ticker))
    if val and intrinsic > 0:
        m2.metric("DCF Intrinsic", _fmt(intrinsic, ticker), f"{((intrinsic/s0)-1):+.1%}")
    else:
        m2.metric("MC Expected", _fmt(metrics["Expected Price"], ticker), f"{((metrics['Expected Price']/s0)-1):+.1%}")
    m3.metric("VaR 95%", f"{metrics['VaR 95% (Rel)']:.1%}")
    m4.metric("Prob. of Profit", f"{metrics['Prob. of Profit']:.1f}%")

    st.markdown("")

    # Detailed risk in columns
    d1, d2, d3, d4 = st.columns(4)
    with d1:
        st.markdown("<p style='color:#00d4ff;font-weight:700;font-size:0.85rem;letter-spacing:0.5px;'>📈 PRICE TARGETS</p>",
                    unsafe_allow_html=True)
        for l, k in [("Expected","Expected Price"),("Median","Median Price"),("Best","Best Case Price"),
                     ("Worst","Worst Case Price"),("90th %ile","90th Percentile Price"),("10th %ile","10th Percentile Price")]:
            st.write(f"{l}: **{_fmt(metrics[k],ticker)}**")
    with d2:
        st.markdown("<p style='color:#ff6b6b;font-weight:700;font-size:0.85rem;letter-spacing:0.5px;'>⚠️ RISK METRICS</p>",
                    unsafe_allow_html=True)
        st.write(f"VaR 95%: **{metrics['VaR 95% (Rel)']:.2%}**")
        st.write(f"CVaR 95%: **{metrics['CVaR 95%']:.2%}**")
        st.write(f"VaR 99%: **{metrics['VaR 99% (Rel)']:.2%}**")
        st.write(f"CVaR 99%: **{metrics['CVaR 99%']:.2%}**")
        st.write(f"Max DD: **{metrics['Max Drawdown']:.1f}%**")
        st.write(f"Volatility: **{metrics['Volatility (Annual)']:.1f}%**")
    with d3:
        st.markdown("<p style='color:#7b2ff7;font-weight:700;font-size:0.85rem;letter-spacing:0.5px;'>📊 PROBABILITY</p>",
                    unsafe_allow_html=True)
        st.write(f"Profit: **{metrics['Prob. of Profit']:.1f}%**")
        st.write(f">10% Gain: **{metrics['Prob. of >10% Gain']:.1f}%**")
        st.write(f">25% Gain: **{metrics['Prob. of >25% Gain']:.1f}%**")
        st.write(f">10% Loss: **{metrics['Prob. of >10% Loss']:.1f}%**")
        st.write(f"Avg Up: **+{metrics['Avg Upside']:.1f}%**")
        st.write(f"Avg Down: **{metrics['Avg Downside']:.1f}%**")
    with d4:
        st.markdown("<p style='color:#ff9a56;font-weight:700;font-size:0.85rem;letter-spacing:0.5px;'>🏆 RATIOS</p>",
                    unsafe_allow_html=True)
        st.write(f"Sharpe: **{metrics['Sharpe Ratio']:.2f}**")
        st.write(f"Sortino: **{metrics['Sortino Ratio']:.2f}**")
        st.write(f"Risk-Reward: **{metrics['Risk-Reward Ratio']:.2f}**")
        st.write(f"Exp. Return: **{metrics['Expected Return']:.1f}%**")
        st.write(f"Max Upside: **+{metrics['Max Upside']:.1f}%**")

    st.markdown("---")

    # Charts
    cl, cr = st.columns(2)
    with cl:
        fig = go.Figure()
        x = np.arange(len(low_band))
        fig.add_trace(go.Scatter(x=x, y=high_band, fill=None, mode="lines",
                                  line=dict(color="rgba(0,212,255,0.15)", width=0), name="Top 5%"))
        fig.add_trace(go.Scatter(x=x, y=low_band, fill="tonexty", mode="lines",
                                  line=dict(color="rgba(255,107,107,0.15)", width=0),
                                  fillcolor="rgba(123,47,247,0.08)", name="90% Confidence"))
        fig.add_trace(go.Scatter(y=np.mean(paths, axis=1), mode="lines",
                                  line=dict(color="#00d4ff", width=2.5), name="Expected Path"))
        if val and intrinsic > 0:
            fig.add_hline(y=intrinsic, line_dash="dot", line_color="rgba(123,47,247,0.7)",
                          annotation_text=f"DCF {_fmt(intrinsic,ticker)}",
                          annotation_font_color="#7b2ff7")
        fig.update_layout(**PLOTLY_LAYOUT, title="Monte Carlo Confidence Bands",
                          xaxis_title="Trading Days", yaxis_title=f"Price ({cur})", height=420)
        st.plotly_chart(fig, use_container_width=True)

    with cr:
        fig2 = go.Figure()
        fig2.add_trace(go.Histogram(x=final_prices, nbinsx=60,
                                     marker_color="rgba(0,212,255,0.4)",
                                     marker_line=dict(color="rgba(0,212,255,0.6)", width=0.5)))
        fig2.add_vline(x=s0, line_dash="dash", line_color="rgba(255,255,0,0.7)",
                       annotation_text=f"Market {_fmt(s0,ticker)}", annotation_font_color="yellow")
        if val and intrinsic > 0:
            fig2.add_vline(x=intrinsic, line_dash="dot", line_color="rgba(123,47,247,0.7)",
                           annotation_text=f"DCF {_fmt(intrinsic,ticker)}", annotation_font_color="#7b2ff7")
        fig2.update_layout(**PLOTLY_LAYOUT, title="Terminal Price Distribution",
                           xaxis_title=f"Price ({cur})", yaxis_title="Frequency", height=420)
        st.plotly_chart(fig2, use_container_width=True)

    # Benchmark table
    st.markdown("#### 📊 Performance vs. Benchmarks")
    bn, br = ("Nifty 50 (12%)", 1.12) if _is_indian(ticker) else ("S&P 500 (10%)", 1.10)
    mg = s0 * (br ** years)
    bench_rows = []
    if val and intrinsic > 0:
        bench_rows.append({"Scenario": f"{co_name} — DCF", "Value": _fmt(intrinsic, ticker), "Return": f"{((intrinsic/s0)-1):+.1%}"})
    bench_rows.append({"Scenario": f"{co_name} — Monte Carlo", "Value": _fmt(metrics["Expected Price"], ticker), "Return": f"{((metrics['Expected Price']/s0)-1):+.1%}"})
    bench_rows.append({"Scenario": bn, "Value": _fmt(mg, ticker), "Return": f"{((mg/s0)-1):+.1%}"})
    st.table(pd.DataFrame(bench_rows))

    st.markdown("---")

    # ═══════════════════════════════════════════════════════════════════════
    #  STEP 5: CROSS-VERIFICATION + AUTO-CORRECTION
    # ═══════════════════════════════════════════════════════════════════════
    if has_fundamentals and val and intrinsic > 0:
        st.markdown("""
        <div style="display:flex;align-items:center;gap:10px;margin:8px 0 16px 0;">
            <span style="background:linear-gradient(135deg,#ff6b6b,#7b2ff7);color:white;
                         padding:6px 14px;border-radius:20px;font-weight:700;font-size:0.85rem;">STEP 5</span>
            <span style="font-size:1.25rem;font-weight:700;color:#e6e6e6;">Cross-Verification & Auto-Correction</span>
        </div>
        """, unsafe_allow_html=True)
        st.caption("Checks our DCF against analyst consensus & industry. Auto-corrects if deviation >30%.")

        sector = TICKER_TO_SECTOR.get(ticker, SECTOR_CLEAN.get(category, category))
        with st.spinner("Cross-verifying…"):
            cv = cross_verify_and_correct(ticker, intrinsic, s0, our_signal, sector, fd, val)

        consensus = cv["consensus"]
        sector_data = cv["sector_data"]
        is_india = _is_indian(ticker)

        # Check 1
        flag_emoji = "🇮🇳" if is_india else "🇺🇸"
        check1_title = "Indian Brokerage Consensus" if is_india else "Wall Street Analyst Consensus"
        check1_firms = ("Motilal Oswal · ICICI Direct · HDFC Securities · Kotak · Jefferies India · CLSA · Nuvama"
                        if is_india else
                        "Goldman Sachs · Morgan Stanley · JP Morgan · UBS · Bank of America")

        st.markdown(f"""
        <div class="glass-card" style="border-color:rgba(88,166,255,0.15);">
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">
                <span style="font-size:1.5rem;">{flag_emoji}</span>
                <span style="font-size:1.1rem;font-weight:700;color:#e6e6e6;">{check1_title}</span>
            </div>
            <p style="color:#484f58;font-size:0.8rem;margin:0;">{check1_firms}</p>
        </div>
        """, unsafe_allow_html=True)

        if consensus["available"]:
            st.caption(f"Source: {consensus.get('source', 'N/A')}")
            ws_rows = [
                {"Metric": "Consensus Target (Mean)", "Value": f"{cur}{consensus['target_mean']:,.2f}"},
                {"Metric": "Target Range", "Value": f"{cur}{consensus['target_low']:,.2f} — {cur}{consensus['target_high']:,.2f}"},
                {"Metric": "Rating", "Value": str(consensus.get('recommendation','N/A')).upper()},
                {"Metric": "# Analysts", "Value": str(consensus.get('num_analysts','N/A'))},
                {"Metric": "Our DCF", "Value": f"{cur}{intrinsic:,.2f}"},
                {"Metric": "Deviation", "Value": f"{cv['deviation']:+.1%}" if cv["deviation"] else "N/A"},
            ]
            st.table(pd.DataFrame(ws_rows))

            brokerages = consensus.get("top_brokerages", {})
            if brokerages:
                brok_label = "Indian Brokerage" if is_india else "Wall Street Firm"
                st.markdown(f"**Individual {brok_label} Targets:**")
                brok_rows = [{"Firm": f, "Target": f"{cur}{d['target']:,.2f}", "Rating": d["rating"]}
                             for f, d in brokerages.items()]
                st.table(pd.DataFrame(brok_rows))
        else:
            st.warning("Analyst consensus not available.")

        # Check 2
        st.markdown(f"""
        <div class="glass-card" style="border-color:rgba(123,47,247,0.15);margin-top:8px;">
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">
                <span style="font-size:1.5rem;">📊</span>
                <span style="font-size:1.1rem;font-weight:700;color:#e6e6e6;">Industry / Sector Benchmark</span>
            </div>
            <p style="color:#484f58;font-size:0.8rem;margin:0;">
                Sources: {sector_data.get('credible_sources','N/A')} · Benchmark: {sector_data.get('benchmark_index','N/A')}</p>
        </div>
        """, unsafe_allow_html=True)

        outlook_colors = {"Bullish": "#1b8a2a", "Neutral-Bullish": "#7baa2a", "Neutral": "#c47f17",
                          "Mixed": "#c47f17", "Bearish": "#b52a2a"}
        oc = outlook_colors.get(sector_data["outlook"], "#555")
        st.markdown(f"""
        <div style="display:flex;gap:16px;align-items:center;margin:8px 0 12px 0;">
            <span style="background:{oc};color:white;padding:4px 14px;border-radius:20px;font-weight:600;font-size:0.85rem;">
                {sector_data['outlook']}</span>
            <span style="color:#8b949e;">PE: <b style="color:#e6e6e6;">{sector_data['avg_pe']}x</b></span>
            <span style="color:#8b949e;">Growth: <b style="color:#e6e6e6;">{sector_data['avg_growth']:.0%}</b></span>
        </div>
        """, unsafe_allow_html=True)
        st.markdown(f"> {sector_data['narrative']}")

        if cv["industry_mismatch"]:
            st.warning("⚠️ Our signal conflicts with sector outlook.")

        st.markdown("---")

        # Auto-correction
        if cv["needs_correction"]:
            st.markdown("""
            <div style="background:linear-gradient(135deg,rgba(255,107,107,0.08),rgba(123,47,247,0.08));
                        padding:16px 20px;border-radius:12px;border:1px solid rgba(255,107,107,0.2);margin:0 0 16px 0;">
                <p style="color:#ff6b6b;font-weight:700;font-size:1rem;margin:0;">
                    🔧 AUTO-CORRECTION TRIGGERED</p>
                <p style="color:#8b949e;margin:4px 0 0 0;font-size:0.85rem;">
                    Deviation exceeded 30%. Fetching real data from Yahoo Finance and re-running Damodaran model…</p>
            </div>
            """, unsafe_allow_html=True)

            for reason in cv["deviation_reasons"]:
                st.warning(reason)

            if cv["corrections_made"]:
                st.markdown("**📋 Corrections Applied:**")
                corr_rows = []
                for c in cv["corrections_made"]:
                    if c["field"] == "FETCH_ERROR":
                        st.error(f"Fetch error: {c['new']}")
                        continue
                    old, new = c["old"], c["new"]
                    if isinstance(old, float) and abs(old) < 1:
                        os, ns = f"{old:.2%}", f"{new:.2%}"
                    elif isinstance(old, float):
                        os, ns = f"{cur}{old:,.2f}", f"{cur}{new:,.2f}"
                    else:
                        os, ns = str(old), str(new)
                    chg = f"{((new-old)/abs(old)):+.1%}" if isinstance(old,(int,float)) and isinstance(new,(int,float)) and old!=0 else ""
                    corr_rows.append({"Field": c["field"], "Original": os, "Corrected": ns, "Δ": chg, "Source": c["source"]})
                if corr_rows:
                    st.dataframe(pd.DataFrame(corr_rows), use_container_width=True, hide_index=True)

            cr_result = cv["corrected_result"]
            if cr_result and cr_result["intrinsic_value"] > 0:
                new_intrinsic = cr_result["intrinsic_value"]
                new_vd = cr_result["valuation_detail"]
                new_mc = cr_result["model_selection"]

                st.markdown(f"#### 💎 Corrected: {new_vd.get('model','DCF')} — Year-by-Year")
                if "year_by_year" in new_vd and new_vd["year_by_year"]:
                    df_n = pd.DataFrame(new_vd["year_by_year"])
                    for col in df_n.columns:
                        if col in skip_cols: continue
                        if df_n[col].dtype in [np.float64, np.int64, float, int]:
                            df_n[col] = df_n[col].apply(lambda x: f"{cur}{x:,.2f}" if abs(x)>=1 else f"{x:.6f}")
                    st.dataframe(df_n, use_container_width=True, hide_index=True)

                if "summary" in new_vd:
                    with st.expander("📊 Corrected Summary", expanded=False):
                        rows = []
                        for k, v in new_vd["summary"].items():
                            if isinstance(v, float):
                                f_ = f"{v:.2%}" if abs(v)<1 and v!=0 else f"{cur}{v:,.2f}"
                            else:
                                f_ = f"{v:,}" if isinstance(v, int) else str(v)
                            rows.append({"Item": k, "Value": f_})
                        st.table(pd.DataFrame(rows))

                # Side-by-side
                st.markdown("#### ⚖️ Original vs. Corrected")
                col_o, col_c = st.columns(2)
                with col_o:
                    st.markdown(f"""
                    <div class="glass-card" style="border-color:rgba(255,107,107,0.3);text-align:center;">
                        <p style="color:#ff6b6b;font-weight:700;font-size:0.85rem;letter-spacing:1px;margin:0;">ORIGINAL DCF</p>
                        <h1 style="margin:8px 0;font-size:2.2rem;font-weight:900;color:#ff6b6b;">{_fmt(intrinsic,ticker)}</h1>
                        <p style="color:#484f58;font-size:0.8rem;margin:0;">{mc_sel['model_code']}.xls · vs Market: {((intrinsic/s0)-1):+.1%}</p>
                    </div>""", unsafe_allow_html=True)
                with col_c:
                    st.markdown(f"""
                    <div class="glass-card" style="border-color:rgba(0,212,255,0.3);text-align:center;">
                        <p style="color:#00d4ff;font-weight:700;font-size:0.85rem;letter-spacing:1px;margin:0;">CORRECTED DCF</p>
                        <h1 style="margin:8px 0;font-size:2.2rem;font-weight:900;
                                   background:linear-gradient(90deg,#00d4ff,#7b2ff7);
                                   -webkit-background-clip:text;-webkit-text-fill-color:transparent;">{_fmt(new_intrinsic,ticker)}</h1>
                        <p style="color:#484f58;font-size:0.8rem;margin:0;">{new_mc['model_code']}.xls · vs Market: {((new_intrinsic/s0)-1):+.1%}</p>
                    </div>""", unsafe_allow_html=True)

                chg = (new_intrinsic - intrinsic) / intrinsic if intrinsic != 0 else 0
                chg_color = "#1b8a2a" if chg > 0 else "#b52a2a"
                st.markdown(f"<p style='text-align:center;margin:8px 0;color:{chg_color};font-weight:600;'>"
                            f"Correction Impact: {chg:+.1%} ({_fmt(intrinsic,ticker)} → {_fmt(new_intrinsic,ticker)})</p>",
                            unsafe_allow_html=True)

                # Comparison chart
                fig_comp = go.Figure()
                labels = ["Market Price", "Original DCF", "Corrected DCF"]
                values = [s0, intrinsic, new_intrinsic]
                colors = ["#ffd700", "#ff6b6b", "#00d4ff"]
                if consensus["available"] and consensus["target_mean"]:
                    labels.append("Analyst Consensus")
                    values.append(consensus["target_mean"])
                    colors.append("#7b2ff7")

                fig_comp.add_trace(go.Bar(
                    x=labels, y=values, marker_color=colors,
                    text=[f"{cur}{v:,.0f}" for v in values], textposition="outside",
                    textfont=dict(color="#e6e6e6", size=14, family="Inter"),
                    marker_line=dict(width=0),
                ))
                fig_comp.update_layout(**PLOTLY_LAYOUT, title="Value Comparison",
                                       yaxis_title=f"Price ({cur})", height=380, showlegend=False)
                fig_comp.update_traces(marker_cornerradius=6)
                st.plotly_chart(fig_comp, use_container_width=True)

                # Corrected verdict
                new_mos = (new_intrinsic - s0) / s0
                if new_mos > 0.20:
                    nvg = "linear-gradient(135deg,#0d4f1e,#1b8a2a)"
                    nvt = "🟢 UNDERVALUED — BUY"
                elif new_mos > -0.10:
                    nvg = "linear-gradient(135deg,#4a3500,#c47f17)"
                    nvt = "🟡 FAIRLY VALUED — HOLD"
                else:
                    nvg = "linear-gradient(135deg,#4a0d0d,#b52a2a)"
                    nvt = "🔴 OVERVALUED — AVOID"
                st.markdown(f"""
                <div class="signal-banner" style="background:{nvg};">
                    <p style="color:rgba(255,255,255,0.6);font-size:0.85rem;margin:0;letter-spacing:1px;">CORRECTED VERDICT</p>
                    <h1 style="color:white;font-size:1.8rem;">{nvt}</h1>
                    <h3 style="color:rgba(255,255,255,0.8);font-size:0.95rem;">
                        DCF: {_fmt(new_intrinsic,ticker)} · Market: {_fmt(s0,ticker)} · Margin: {new_mos:+.1%}</h3>
                </div>""", unsafe_allow_html=True)
            else:
                st.warning("Could not compute corrected value. Using original analysis.")
        else:
            st.markdown(f"""
            <div class="glass-card" style="border-color:rgba(27,138,42,0.3);background:rgba(27,138,42,0.03);text-align:center;">
                <p style="font-size:1.5rem;margin:0;">✅</p>
                <p style="color:#1b8a2a;font-weight:700;font-size:1.05rem;margin:8px 0 4px 0;">
                    No Correction Needed</p>
                <p style="color:#8b949e;font-size:0.85rem;margin:0;">
                    Our DCF aligns with {'Indian brokerage' if is_india else 'Wall Street'} consensus and sector outlook.</p>
            </div>
            """, unsafe_allow_html=True)

            if consensus["available"] and consensus["target_mean"]:
                fig_ok = go.Figure()
                fig_ok.add_trace(go.Bar(
                    x=["Market Price", "Our DCF", f"{'Indian' if is_india else 'WS'} Consensus"],
                    y=[s0, intrinsic, consensus["target_mean"]],
                    marker_color=["#ffd700", "#00d4ff", "#7b2ff7"],
                    text=[f"{cur}{v:,.0f}" for v in [s0, intrinsic, consensus["target_mean"]]],
                    textposition="outside", textfont=dict(color="#e6e6e6", size=14),
                ))
                fig_ok.update_layout(**PLOTLY_LAYOUT, title="Our DCF vs Consensus vs Market",
                                      yaxis_title=f"Price ({cur})", height=360, showlegend=False)
                fig_ok.update_traces(marker_cornerradius=6)
                st.plotly_chart(fig_ok, use_container_width=True)

        st.markdown("---")

    # ═══════════════════════════════════════════════════════════════════════
    #  FOOTER
    # ═══════════════════════════════════════════════════════════════════════
    st.markdown(f"""
    <div class="footer-badge">
        <p style="margin:0;font-size:0.75rem;color:#484f58;">
            Price: {source_name} · DCF: {mc_sel['model_code'] if val else 'N/A'} ·
            {sims:,} simulations · {years}yr horizon · {crash_scenario}% stress
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style="text-align:center;padding:30px 0 10px 0;">
        <div style="display:inline-block;background:linear-gradient(135deg,rgba(0,212,255,0.06),rgba(123,47,247,0.06));
                    border:1px solid rgba(0,212,255,0.12);border-radius:16px;padding:20px 40px;">
            <p style="margin:0;font-size:1.3rem;font-weight:800;
                      background:linear-gradient(90deg,#00d4ff,#7b2ff7,#ff6b6b);
                      -webkit-background-clip:text;-webkit-text-fill-color:transparent;">
                Arpit Sharma</p>
            <p style="color:#58a6ff;font-size:0.9rem;margin:4px 0 0 0;font-weight:500;">IPM 2</p>
            <p style="color:#484f58;font-size:0.75rem;margin:6px 0 0 0;">
                Institutional Equity Lab · Damodaran DCF + Monte Carlo + Auto-Correction</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

except ValueError as e:
    st.error(f"Data Error: {e}")
except Exception as e:
    st.error(f"Error for {ticker}: {type(e).__name__}: {e}")
    st.exception(e)