"""
app.py
------
Main Streamlit dashboard for the Sector Intelligence Tracker.
Redesigned with NixTio modern dark theme layout, CSS animations, and simple Auth.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import datetime
import time

# Monkey patch pandas DataFrameGroupBy.get_group to avoid compatibility KeyErrors with Plotly Express in Pandas 3.0+
from pandas.core.groupby.generic import DataFrameGroupBy
_original_get_group = DataFrameGroupBy.get_group

def _patched_get_group(self, name, *args, **kwargs):
    try:
        return _original_get_group(self, name, *args, **kwargs)
    except KeyError:
        if not isinstance(name, tuple):
            try:
                return _original_get_group(self, (name,), *args, **kwargs)
            except KeyError:
                pass
        elif isinstance(name, tuple) and len(name) == 1:
            try:
                return _original_get_group(self, name[0], *args, **kwargs)
            except KeyError:
                pass
        raise

DataFrameGroupBy.get_group = _patched_get_group


from data.scrapers import (
    DataFetcher,
    SectorData
)
from data.sectors import SECTORS, list_sector_keys
from data.sector_meta import SECTOR_META
from utils.helpers import (
    format_large_number, 
    timestamp_label, 
    apply_nixtio_theme
)
from utils.ai_analyst import (
    generate_sector_analysis,
    stream_analyst_response
)
from components.analyst_chat import render_analyst_sidebar
import json

# ---------------------------------------------------------------------------
# Page configuration
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="NixTio — Sector Intelligence",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
    <head>
        <title>NixTio — Sector Intelligence</title>
        <meta name="description" content="Premium real-time sector intelligence and competitive analysis platform for India's sharpest operators.">
    </head>
""", unsafe_allow_html=True)

if "logged_in" not in st.session_state:
    st.session_state.logged_in = True
if "history" not in st.session_state:
    st.session_state.history = []
if "demo_mode" not in st.session_state:
    st.session_state.demo_mode = True
if "onboarded" not in st.session_state:
    st.session_state.onboarded = True
if "saas_token" not in st.session_state:
    st.session_state.saas_token = "mock_enterprise_token"
if "saas_user" not in st.session_state:
    st.session_state.saas_user = {
        "email": "admin@nixtio.com",
        "org_name": "NixTio Default",
        "plan_tier": "enterprise"
    }
if "sector_selector" not in st.session_state:
    st.session_state["sector_selector"] = list_sector_keys()[0]
if "last_sector" not in st.session_state:
    st.session_state["last_sector"] = st.session_state["sector_selector"]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

NEWS_API_KEY = st.secrets.get("NEWS_API_KEY", "")
CHART_COLORS = ["#B388FF", "#D4E157", "#9E9E9E", "#FFB74D", "#81C784", "#CE93D8"]

# ---------------------------------------------------------------------------
# Advanced Custom CSS — Premium Authentic Animations
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# NixTio Design System — Comprehensive CSS Override
# ---------------------------------------------------------------------------

NIXTIO_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Manrope:wght@700;800&display=swap');

/* GLOBAL DEFAULTS */
html, body, [class*="css"] {{
    font-family: 'Inter', sans-serif !important;
    color: #C9D1D9 !important;
}}

.stApp {{
    background-color: #0D1117 !important;
}}

/* HIDE STREAMLIT CHROME */
header[data-testid="stHeader"], footer, #MainMenu {{
    visibility: hidden !important;
    display: none !important;
}}



.main .block-container {{
    padding-top: 3rem !important;
    padding-left: 5rem !important;
    padding-right: 5rem !important;
    max-width: 1600px !important;
    margin: 0 auto !important;
}}

/* SIDEBAR STYLING */
[data-testid="stSidebar"] {{
    background-color: #161B22 !important;
    border-right: 1px solid #21262D !important;
}}

[data-testid="stSidebar"] > div:first-child {{
    padding-top: 20px !important;
}}

/* Sidebar navigation labels */
[data-testid="stSidebar"] .stRadio label p {{
    font-size: 0.95rem !important;
    font-weight: 500 !important;
    color: #8B949E !important;
}}

/* Nav Pill Styling */
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] > label {{
    padding: 0.5rem 1rem !important;
    border-radius: 8px !important;
    margin-bottom: 0.25rem !important;
    transition: all 0.2s ease !important;
    border-left: 3px solid transparent !important;
    background: transparent !important;
}}

[data-testid="stSidebar"] .stRadio div[role="radiogroup"] > label:hover {{
    background: rgba(255, 255, 255, 0.03) !important;
}}

/* Active State */
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] input:checked + div {{
    background: rgba(55, 138, 221, 0.15) !important;
    border-left: 3px solid #378ADD !important;
}}

[data-testid="stSidebar"] .stRadio div[role="radiogroup"] input:checked + div p {{
    color: white !important;
    font-weight: 600 !important;
}}

/* Section Labels */
.sidebar-section-label {{
    font-size: 0.65rem !important;
    font-weight: 800 !important;
    color: #484F58 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.2em !important;
    margin: 2rem 0 0.5rem 1rem !important;
}}

/* METRIC CARDS - GLASSMORPHISM */
[data-testid="stMetric"] {{
    background: rgba(255, 255, 255, 0.03) !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    border-radius: 12px !important;
    backdrop-filter: blur(10px) !important;
    padding: 1.25rem !important;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
}}

[data-testid="stMetricValue"] {{
    font-family: 'Manrope', sans-serif !important;
    font-weight: 700 !important;
    font-size: 1.8rem !important;
    color: white !important;
}}

[data-testid="stMetricLabel"] {{
    font-family: 'Inter', sans-serif !important;
    color: #8B949E !important;
    font-size: 0.8rem !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.05em !important;
}}

/* BUTTONS */
.stButton > button {{
    border-radius: 8px !important;
    font-family: 'Manrope', sans-serif !important;
    font-weight: 700 !important;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
}}

.stButton > button[kind="primary"] {{
    background-color: #378ADD !important;
    border: none !important;
    color: white !important;
    box-shadow: 0 4px 14px rgba(55, 138, 221, 0.2) !important;
}}

.stButton > button:hover {{
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 20px rgba(55, 138, 221, 0.3) !important;
}}

/* HEADERS */
h1, h2, h3, .page-header, .chart-title {{
    font-family: 'Manrope', sans-serif !important;
    color: white !important;
    font-weight: 700 !important;
    letter-spacing: -0.02em !important;
    margin-left: 0.5rem !important; /* Prevent cut-off */
}}

.page-header {{
    font-size: 2.2rem !important;
    margin-bottom: 1.5rem !important;
}}

.chart-title {{
    font-size: 1.2rem !important;
    color: #378ADD !important;
    margin-bottom: 0.75rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.05em !important;
}}

/* SKELETON LOADERS */
.nixtio-skeleton {{
    background: linear-gradient(90deg, #161B22 25%, #1C2128 50%, #161B22 75%);
    background-size: 200% 100%;
    animation: skeleton-loading 1.5s infinite;
    border-radius: 8px;
}}

@keyframes skeleton-loading {{
    0% {{ background-position: 200% 0; }}
    100% {{ background-position: -200% 0; }}
}}



/* METRICS GRID */
.metrics-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    gap: 20px;
    margin-bottom: 30px;
}}
</style>


"""
st.markdown(NIXTIO_CSS, unsafe_allow_html=True)



# ==============================================================================
# AUTHENTICATION ROUTING
# ==============================================================================

# The login page has been removed per approved SaaS and user guidelines.
# Everyone is granted access to view the NixTio dashboard directly.
# SaaS features like report generation are gated behind JWT auth in the sidebar.
st.session_state.logged_in = True

if True:
    # ---------------- MAIN APPLICATION ----------------
    
    def apply_layout(fig, height=350):
        fig.update_layout(
            title=None,
            font=dict(family="Inter, sans-serif", size=11, color="#8E8D92"),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=30, r=20, t=10, b=30), height=height,
            xaxis=dict(showgrid=False, linecolor="#2A1A4A", gridcolor="#2A1A4A"),
            yaxis=dict(showgrid=True, gridcolor="#2A1A4A", gridwidth=1, linecolor="#2A1A4A"),
            legend=dict(font=dict(family="Inter", size=11, color="#EEEDEB"), bgcolor="rgba(0,0,0,0)", orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
            hoverlabel=dict(bgcolor="#15111B", font_size=12, font_family="Inter", bordercolor="#B388FF", font_color="white"),
        )
        return fig

    # ---------------------------------------------------------------------------
    # Micro-interactions & Helpers
    # ---------------------------------------------------------------------------

    def render_typing_indicator():
        st.markdown("""
        <div style="display:flex; gap:4px; padding:10px; align-items:center;">
            <div class="typing-dot" style="width:6px; height:6px; background:#8B949E; border-radius:50%; animation: blink 1.4s infinite 0.2s;"></div>
            <div class="typing-dot" style="width:6px; height:6px; background:#8B949E; border-radius:50%; animation: blink 1.4s infinite 0.4s;"></div>
            <div class="typing-dot" style="width:6px; height:6px; background:#8B949E; border-radius:50%; animation: blink 1.4s infinite 0.6s;"></div>
        </div>
        <style>
        @keyframes blink { 0% { opacity: 0.2; } 20% { opacity: 1; } 100% { opacity: 0.2; } }
        </style>
        """, unsafe_allow_html=True)

    def render_onboarding():
        if not st.session_state.onboarded:
            st.markdown("""
            <div style="position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(13,17,23,0.95); z-index:99999; display:flex; align-items:center; justify-content:center; backdrop-filter:blur(8px);">
                <div style="background:#161B22; border:1px solid #30363D; border-radius:24px; padding:48px; max-width:600px; text-align:center; box-shadow:0 24px 64px rgba(0,0,0,0.5);">
                    <div style="width:64px; height:64px; background:#378ADD; border-radius:50%; margin:0 auto 24px auto; display:flex; align-items:center; justify-content:center; font-size:24px; color:white; font-weight:bold;">N•</div>
                    <h1 style="color:white; font-family:Manrope; margin-bottom:16px;">Welcome to NixTio</h1>
                    <p style="color:#8B949E; margin-bottom:32px;">Real-time sector intelligence at your fingertips. Let's get you set up.</p>
                    <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:12px; margin-bottom:40px;">
                        <div style="padding:16px; background:rgba(55,138,221,0.1); border-radius:12px; border:1px solid #378ADD;">
                            <div style="font-size:12px; color:#378ADD; font-weight:bold; margin-bottom:4px;">STEP 1</div>
                            <div style="color:white; font-size:14px;">Sector</div>
                        </div>
                        <div style="padding:16px; background:rgba(255,255,255,0.03); border-radius:12px; border:1px solid #30363D;">
                            <div style="font-size:12px; color:#8B949E; font-weight:bold; margin-bottom:4px;">STEP 2</div>
                            <div style="color:#C9D1D9; font-size:14px;">Analysis</div>
                        </div>
                        <div style="padding:16px; background:rgba(255,255,255,0.03); border-radius:12px; border:1px solid #30363D;">
                            <div style="font-size:12px; color:#8B949E; font-weight:bold; margin-bottom:4px;">STEP 3</div>
                            <div style="color:#C9D1D9; font-size:14px;">Go Live</div>
                        </div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Start Setup", key="onboard_start", use_container_width=True, type="primary"):
                st.session_state.onboarded = True
                st.rerun()

    def fetch_sector_data_with_progress(sector_key: str, news_api_key: str, demo_mode: bool = False):
        if demo_mode:
            from data.fallback_data import (
                get_fallback_trends, get_fallback_playstore, get_fallback_linkedin, 
                get_fallback_ambitionbox, get_fallback_news, get_fallback_sentiment
            )
            # Use mock data specifically for demo
            cos = SECTORS.get(sector_key, {}).get("companies", [])
            results = {
                "trends": {"data": get_fallback_trends(cos), "status": "ok"},
                "ratings": {"data": get_fallback_playstore(cos), "status": "ok"},
                "jobs": {"data": get_fallback_linkedin(cos), "status": "ok"},
                "employer": {"data": get_fallback_ambitionbox(cos), "status": "ok"},
                "news": {"data": get_fallback_news(cos), "status": "ok"},
                "sentiment": {"data": get_fallback_sentiment(cos), "status": "ok"}
            }
            return SectorData(results)
            
        progress_bar = st.progress(0, text="Connecting to NixTio Intelligence API...")
        
        try:
            import httpx
            api_url = "http://localhost:8000/analyze" # Should be configurable
            
            with httpx.Client(timeout=120.0) as client:
                progress_bar.progress(0.2, text="Requesting intelligence analysis...")
                headers = {}
                if "saas_token" in st.session_state and st.session_state.saas_token:
                    headers["Authorization"] = f"Bearer {st.session_state.saas_token}"
                resp = client.post(
                    api_url,
                    json={"sector": sector_key, "companies": SECTORS[sector_key]["companies"]},
                    headers=headers
                )
                resp.raise_for_status()
                progress_bar.progress(0.8, text="Parsing intelligence response...")
                results_raw = resp.json()
                results = results_raw.get("results", {})
                
                # Reconstruct DataFrames where necessary
                for key, val in results.items():
                    if isinstance(val.get("data"), list):
                        df = pd.DataFrame(val["data"])
                        if key == "trends" and "date" in df.columns:
                            df.set_index("date", inplace=True)
                        results[key]["data"] = df

                progress_bar.progress(1.0, text="Intelligence Sync Complete")
                time.sleep(0.5)
                progress_bar.empty()
                return SectorData(results)
                
        except Exception as e:
            st.error(f"Intelligence API connection failed: {str(e)}")
            st.info("Ensure the FastAPI backend is running on http://localhost:8000")
            return SectorData({})

    def render_data_health_banner(health_score):
        if health_score >= 100:
            color, text = "#3FB950", "All signals live"
        elif health_score >= 60:
            color, text = "#D29922", "Partial signals live — some data may be stale"
        else:
            color, text = "#F85149", "Limited data — showing cached intelligence"
        
        st.markdown(f"""
        <div style="display:flex; align-items:center; gap:12px; margin-bottom:1.5rem; background:rgba(255,255,255,0.02); padding:8px 16px; border-radius:8px; border: 1px solid rgba(255,255,255,0.05);">
            <span style="color:#8B949E; font-size:0.75rem; font-weight:700; text-transform:uppercase; letter-spacing:0.1em;">Intel Health</span>
            <div style="display:flex; align-items:center; gap:6px; background:{color}22; color:{color}; padding:4px 10px; border-radius:6px; border:1px solid {color}44; font-size:0.8rem; font-weight:600;">
                <div style="width:6px; height:6px; border-radius:50%; background:{color};"></div>
                {text}
            </div>
            {f'<div style="margin-left:auto"><a href="/" style="color:#8B949E; text-decoration:none; font-size:0.75rem;">Refresh System</a></div>' if health_score < 60 else ''}
        </div>
        """, unsafe_allow_html=True)
        
        if health_score < 60:
             if st.button("Force Global Refresh", key="global_refresh_btn", use_container_width=False):
                 st.cache_data.clear()
                 st.rerun()

    def color_map_for(companies):
        return {c: CHART_COLORS[i % len(CHART_COLORS)] for i, c in enumerate(companies)}

    def get_color_seq(df, color_column, base_cmap):
        """Return an ordered color list matching unique values in df[color_column].
        Uses color_discrete_sequence instead of color_discrete_map to avoid
        Plotly Express groupby key lookups that cause KeyErrors."""
        if df is None or df.empty or color_column not in df.columns:
            return list(CHART_COLORS)
        unique_vals = list(df[color_column].dropna().unique())
        return [base_cmap.get(v, CHART_COLORS[i % len(CHART_COLORS)]) for i, v in enumerate(unique_vals)]

    def render_nixtio_metrics_grid(metrics_list):
        """
        Renders premium glassmorphism metric cards using native Streamlit metrics.
        CSS already handles the premium styling.
        """
        cols = st.columns(len(metrics_list))
        for i, m in enumerate(metrics_list):
            with cols[i]:
                st.metric(label=m['label'], value=m['value'], delta=m.get('delta'))

    def render_skeleton_metrics():
        st.markdown(f"""
        <div class="metrics-grid">
            {'<div class="nixtio-skeleton" style="height: 140px; width: 100%;"></div>' * 4}
        </div>
        """, unsafe_allow_html=True)


    # Navigation Sidebar
    with st.sidebar:
        # 1. Branding
        st.markdown("""
        <div style="padding: 1rem 0; display: flex; align-items: center; gap: 12px; margin-bottom: 2rem;">
            <div style="width: 36px; height: 36px; background: #378ADD; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; color: white; font-size: 18px;">N•</div>
            <div style="font-family: 'Manrope', sans-serif; font-size: 22px; font-weight: 800; color: white; letter-spacing: -0.5px;">NixTio</div>
        </div>
        """, unsafe_allow_html=True)

        # 2. Sector Selector at Top
        st.markdown("<p style='font-size: 10px; color: #8B949E; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;'>ACTIVE SECTOR</p>", unsafe_allow_html=True)
        def get_sector_health_dot(s_key):
             # For now, simulate health dot
             return "🟢" if s_key == "Fintech Payments" else "🟡"
        
        sector_options = {f"{get_sector_health_dot(k)} {k}": k for k in list_sector_keys()}
        selected_sector_display = st.selectbox("Sector", options=list(sector_options.keys()), label_visibility="collapsed", key="sector_selector_sidebar")
        selected_sector = sector_options[selected_sector_display]
        st.session_state.sector_selector = selected_sector
        
        st.markdown("<div style='height: 1.5rem'></div>", unsafe_allow_html=True)

        # 3. Demo Mode Toggle
        with st.container(border=True):
            st.session_state.demo_mode = st.toggle("Demo Mode", value=st.session_state.demo_mode, help="Load mock data for presentation")
        
        st.markdown("<div style='height: 1.5rem'></div>", unsafe_allow_html=True)

        # 4. Navigation Sections
        st.markdown("<p style='font-size: 10px; color: #8B949E; font-weight: 700; text-transform: uppercase; letter-spacing: 1px;'>INTELLIGENCE</p>", unsafe_allow_html=True)
        intel_menu = st.radio("Intel", ["Dashboard", "Quantitative Momentum", "AI Analyst", "Competitor Intel"], label_visibility="collapsed")
        
        st.markdown("<div style='height: 1rem'></div>", unsafe_allow_html=True)
        st.markdown("<p style='font-size: 10px; color: #8B949E; font-weight: 700; text-transform: uppercase; letter-spacing: 1px;'>REPORTS</p>", unsafe_allow_html=True)
        report_menu = st.radio("Reports", ["Generate Report", "Report History"], label_visibility="collapsed")
        
        st.markdown("<div style='height: 1rem'></div>", unsafe_allow_html=True)
        st.markdown("<p style='font-size: 10px; color: #8B949E; font-weight: 700; text-transform: uppercase; letter-spacing: 1px;'>SYSTEM</p>", unsafe_allow_html=True)
        system_menu = ["About Product"]
        if st.secrets.get("IS_ADMIN", False):
            system_menu.append("Settings ⚙")
        sys_view = st.radio("System", system_menu, label_visibility="collapsed")

        # Map sub-radios to global view
        if "force_view" in st.session_state:
            view = st.session_state.pop("force_view")
        elif intel_menu == "Dashboard": view = "Overview"
        elif intel_menu == "Quantitative Momentum": view = "Quantitative Momentum"
        elif intel_menu == "AI Analyst": view = "AI Analyst"
        elif intel_menu == "Competitor Intel": view = "Brand Dashboard"
        elif report_menu == "Generate Report": view = "Generate Report"
        elif report_menu == "Report History": view = "Report History"
        else: view = sys_view

        # Sidebar clean footer per user guidelines
        st.markdown("""
        <div style="margin-top: auto; padding-top: 2rem; font-size: 11px; color: #484F58; text-align: center;">
            NixTio Enterprise Platform
        </div>
        """, unsafe_allow_html=True)

    # Demo Banner
    # Instant Sector Sync
    if st.session_state.last_sector != selected_sector:
        st.session_state.last_sector = selected_sector
        st.rerun()
            


    # Top Bar (Header) - Rebalanced Columns
    top1, top2, top3 = st.columns([1, 1.5, 2.5])

    with top1:
        st.markdown(f"<p class='header-logo' style='margin-top: 5px;'>N• <span>NixTio</span></p>", unsafe_allow_html=True)

    with top2:
        if view not in ["Report History", "About Product"]:
            selected_sector = st.selectbox("Sector Intelligence", list_sector_keys(), index=0, key="sector_selector", label_visibility="collapsed")
        else:
            selected_sector = "None"

    with top3:
        col_gen, col_prof = st.columns([1, 1.2])
        with col_gen:
            if st.button("Generate Report", key="top_gen_report", type="primary", use_container_width=True):
                st.session_state["force_view"] = "Generate Report"
                st.rerun()

        with col_prof:
            # Profile Avatar & Name
            st.markdown(f"""
            <div style='display:flex; justify-content:flex-end; align-items:center; gap: 12px;'>
                <div style='text-align:right'>
                    <div style='font-family:Manrope; font-weight:700; font-size:0.85rem; color:#FFF; line-height:1.1;'>Mrinmoy Banikya</div>
                    <div style='font-family:Inter; font-size:0.65rem; color:#378ADD; font-weight:600; text-transform:uppercase;'>Super Admin</div>
                </div>
                <div style='width:36px;height:36px;border-radius:50%;background:linear-gradient(135deg, #378ADD, #1E4D8C);display:flex;align-items:center;justify-content:center;color:#FFF;font-weight:bold;font-size:1rem;'>MB</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")

    # ---------------------------------------------------------------------------
    # Global Data Loading 
    # ---------------------------------------------------------------------------
    
    if view not in ["Report History", "About Product"]:
        sector_config = SECTORS[selected_sector]
        companies = sector_config["companies"]
        cmap = color_map_for(companies)

        try:
            sector_data = fetch_sector_data_with_progress(selected_sector, NEWS_API_KEY, demo_mode=st.session_state.demo_mode)
            
            # Unpack for easier access in the app
            ratings_data = sector_data.ratings
            trends_df = sector_data.trends
            news_data = sector_data.news
            jobs_data = sector_data.jobs
            employer_data = sector_data.employer
            sentiment_data = sector_data.sentiment
            
        except Exception as e:
            st.error(f"Intelligence collection failed: {str(e)}")
            from data.fallback_data import (
                get_fallback_trends, get_fallback_playstore, get_fallback_linkedin, 
                get_fallback_ambitionbox, get_fallback_news, get_fallback_sentiment
            )
            ratings_data = get_fallback_playstore(companies)
            trends_df = get_fallback_trends(companies)
            news_data = get_fallback_news(companies)
            jobs_data = get_fallback_linkedin(companies)
            employer_data = get_fallback_ambitionbox(companies)
            sentiment_data = get_fallback_sentiment(companies)
            sector_data = SectorData({})
            sector_data.health_score = 0

        # --- GLOBAL MOMENTUM SCORE CALCULATION ---
        trend_score = trends_df.mean().mean() if not trends_df.empty else 0
        rv = [v["rating"] for v in ratings_data.values() if v["rating"] > 0] if ratings_data else []
        rating_score = (sum(rv) / len(rv) * 20) if rv else 0
        hiring_score = min((sum(jobs_data.values()) / 500) * 100, 100) if jobs_data else 0
        avg_sent = sum([v.get("sentiment", 0) for v in sentiment_data.values() if v.get("sentiment")]) / len(sentiment_data) if sentiment_data else 0.75
        sentiment_score = (avg_sent + 1) * 50
        
        st.session_state.momentum_score = int((trend_score * 0.3) + (rating_score * 0.2) + (hiring_score * 0.25) + (sentiment_score * 0.25))

        # Health Banner below header
        render_data_health_banner(sector_data.health_score)

        with st.sidebar:
            data = {
                "ratings": ratings_data,
                "jobs": jobs_data,
                "news": news_data,
                "glassdoor": employer_data
            }
            meta = SECTOR_META.get(selected_sector, {})
            render_analyst_sidebar(selected_sector, companies, data, meta)

    # ---------------------------------------------------------------------------
    # Routing Views
    # ---------------------------------------------------------------------------

    enable_compare = st.session_state.get("enable_compare", False)
    company_a = st.session_state.get("company_a", None)
    company_b = st.session_state.get("company_b", None)

    if enable_compare and view not in ["Report History", "About Product"]:
        if company_a and company_b:
            from components.comparison import render_comparison
            render_comparison(company_a, company_b, ratings_data, jobs_data, news_data, employer_data, trends_df)
            st.stop()

    if view == "Overview":
        rv = [v["rating"] for v in ratings_data.values() if v["rating"] > 0] if ratings_data else []
        avg_rating = round(sum(rv) / len(rv), 1) if rv else 0.0
        top_hire_co = max(jobs_data, key=jobs_data.get) if jobs_data else "N/A"
        top_hire_n  = jobs_data[top_hire_co] if jobs_data else 0
        total_news = sum(news_data.values()) if news_data else 0

        # --- Executive Summary Calculation ---
        # Line 1: Momentum
        brand_lead = "N/A"
        trends_last = 0.0
        pct_above_avg = 0.0
        if not trends_df.empty:
            lasts = {}
            for co in companies:
                if co in trends_df.columns:
                    try: lasts[co] = float(trends_df[co].iloc[-1])
                    except: pass
            if lasts:
                brand_lead = max(lasts, key=lasts.get)
                trends_last = lasts[brand_lead]
                avg_trends = sum(lasts.values()) / len(lasts)
                pct_above_avg = ((trends_last - avg_trends) / avg_trends * 100) if avg_trends > 0 else 0

        # Line 2: Talent
        avg_jobs = sum(jobs_data.values()) / len(jobs_data) if jobs_data else 1
        pct_diff = ((top_hire_n - avg_jobs) / avg_jobs * 100) if avg_jobs > 0 else 0

        # Line 3: Risk
        max_j = max(jobs_data.values()) if jobs_data and any(jobs_data.values()) else 1
        risk_co = max(companies, key=lambda c: (jobs_data.get(c, 0)/max_j) - (employer_data.get(c, 5.0)/5.0))
        risk_jobs = jobs_data.get(risk_co, 0)
        risk_emp = employer_data.get(risk_co, 0.0)

        line1 = f"{brand_lead} is the dominant brand in {selected_sector} with a Google Trends index of {trends_last:.0f}/100 — {pct_above_avg:.0f}% above sector average."
        line2 = f"{top_hire_co} is in aggressive hiring mode with {format_large_number(top_hire_n)} open roles ({pct_diff:+.0f}% vs sector avg) — watch for a product launch signal."
        line3 = f"{risk_co} shows scaling stress: {format_large_number(risk_jobs)} open roles but only {risk_emp:.1f}/5 employer rating — attrition risk is elevated."

        momentum_score = st.session_state.momentum_score
        
        # Color and label for score
        if momentum_score >= 81: score_color, score_label = "#3FB950", "Surging"
        elif momentum_score >= 61: score_color, score_label = "#378ADD", "Growing"
        elif momentum_score >= 31: score_color, score_label = "#D29922", "Stable"
        else: score_color, score_label = "#F85149", "Declining"

        col_hero_1, col_hero_2 = st.columns([1, 2])
        with col_hero_1:
            fig_gauge = go.Figure(go.Indicator(
                mode = "gauge+number",
                value = momentum_score,
                domain = {'x': [0, 1], 'y': [0, 1]},
                title = {'text': f"Momentum: {score_label}", 'font': {'size': 18, 'family': 'Manrope', 'color': score_color}},
                number = {'font': {'size': 60, 'family': 'Manrope', 'color': 'white'}},
                gauge = {
                    'axis': {'range': [None, 100], 'tickwidth': 1, 'tickcolor': "#21262D"},
                    'bar': {'color': score_color},
                    'bgcolor': "rgba(255,255,255,0.03)",
                    'borderwidth': 2,
                    'bordercolor': "#21262D",
                    'steps': [
                        {'range': [0, 30], 'color': 'rgba(248,81,73,0.1)'},
                        {'range': [30, 60], 'color': 'rgba(210,153,34,0.1)'},
                        {'range': [60, 80], 'color': 'rgba(55,138,221,0.1)'},
                        {'range': [80, 100], 'color': 'rgba(63,185,80,0.1)'}
                    ],
                }
            ))
            fig_gauge.update_layout(height=280, margin=dict(t=50, b=20, l=30, r=30), paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_gauge, use_container_width=True, config={'displayModeBar': False})

        with col_hero_2:
            st.markdown(f"""
            <div style="font-size: 10px; color: #378ADD; font-weight: bold; letter-spacing: 1.5px; margin-bottom: 12px; margin-top: 20px;">EXECUTIVE SUMMARY</div>
            <div style="background: rgba(255,255,255,0.02); border: 1px solid #21262D; border-radius: 16px; padding: 24px; color: #C9D1D9; font-size: 14px; display: flex; flex-direction: column; gap: 12px;">
                <div style="display:flex; align-items:center; gap:12px;">
                    <div style="width:8px; height:8px; border-radius:50%; background:#378ADD;"></div>
                    <span>{line1}</span>
                </div>
                <div style="display:flex; align-items:center; gap:12px;">
                    <div style="width:8px; height:8px; border-radius:50%; background:#3FB950;"></div>
                    <span>{line2}</span>
                </div>
                <div style="display:flex; align-items:center; gap:12px;">
                    <div style="width:8px; height:8px; border-radius:50%; background:#FFB74D;"></div>
                    <span>{line3}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<div style='height: 2rem'></div>", unsafe_allow_html=True)
        
        # --- Sector Intelligence Metrics ---
        st.markdown("<p class='chart-title'>Sector Key Metrics</p>", unsafe_allow_html=True)
        if selected_sector in SECTOR_META:
            meta = SECTOR_META[selected_sector]
            
            # Use custom NixTio metrics grid
            render_nixtio_metrics_grid([
                {"label": "Total Addressable Market", "value": f"${meta['tam_usd_bn']}B", "delta": "Est. 2024"},
                {"label": "Sector CAGR", "value": f"{meta['cagr_pct']}%", "delta": "↑ Growth"},
                {"label": "Saturation", "value": f"{meta['saturation_score']}", "delta": "Score / 100"},
                {"label": "Market Stage", "value": meta['market_stage'], "delta": "Development"}
            ])
            
            st.markdown("<div style='height: 1rem'></div>", unsafe_allow_html=True)
            
            # 3 columns for lists
            tl1, tl2, tl3 = st.columns([1,1,1])
            with tl1:
                st.markdown("**Tailwinds**")
                for tw in meta['key_tailwinds']:
                    st.markdown(f"- {tw}")
            with tl2:
                st.markdown("**Unsolved Problems**")
                for up in meta['unsolved_problems']:
                    st.markdown(f"- {up}")
            with tl3:
                st.markdown("**Sector Risks**")
                for sr in meta['sector_risks']:
                    st.markdown(f"- {sr}")
            
            # --- Sector Opportunity Radar ---
            st.markdown("#### Sector Opportunity Radar")
            radar = meta.get("radar", {})
            categories = ["Saturation", "Capital Intensity", "Talent Scarcity", 
                          "Regulatory Risk", "Consumer Demand", "White Space Opp."]
            values = [
                radar.get("saturation", 50),
                radar.get("capital_intensity", 50),
                radar.get("talent_scarcity", 50),
                radar.get("regulatory_risk", 50),
                radar.get("consumer_demand", 50),
                radar.get("white_space", 50),
            ]
            values_closed = values + [values[0]]
            categories_closed = categories + [categories[0]]
            
            fig = go.Figure()
            fig.add_trace(go.Scatterpolar(
                r=values_closed,
                theta=categories_closed,
                fill='toself',
                fillcolor='rgba(55,138,221,0.15)',
                line=dict(color='#378ADD', width=2),
                name=selected_sector
            ))
            fig.update_layout(
                polar=dict(
                    bgcolor='#0D1117',
                    radialaxis=dict(visible=True, range=[0,100], 
                                   gridcolor='#21262D', tickcolor='#21262D',
                                   tickfont=dict(color='#8B949E', size=9)),
                    angularaxis=dict(gridcolor='#21262D', 
                                    tickfont=dict(color='#E6EDF3', size=11))
                ),
                paper_bgcolor='#161B22',
                plot_bgcolor='#161B22',
                showlegend=False,
                height=380,
                margin=dict(l=60, r=60, t=40, b=40)
            )
            
            col_radar, col_radar_text = st.columns([1, 1])
            with col_radar:
                apply_nixtio_theme(fig)
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
            with col_radar_text:
                st.markdown("**Reading the radar**")
                for cat, val in zip(categories, values):
                    color = "#3FB950" if val < 40 else ("#D29922" if val < 70 else "#F85149")
                    st.markdown(f"""
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 4px;">
                        <span style="font-size:12px; color:#8B949E;">{cat}</span>
                        <span style="font-size:12px; font-weight:bold; color:{color};">{val}/100</span>
                    </div>
                    <div style="width:100%; height:6px; background:#21262D; border-radius:3px; margin-bottom:12px;">
                        <div style="width:{val}%; height:100%; border-radius:3px; background:{color};"></div>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.markdown(f"""
                <div style='border-left: 3px solid #378ADD; padding-left: 12px; margin-top: 16px; font-size: 13px; color: #E6EDF3;'>
                    {meta.get('radar_insight','Strategic pattern analysis unavailable.')}
                </div>
                """, unsafe_allow_html=True)

            # Reddit Signal Card
            reddit_pts = "".join([f"<div style='border-left: 2px solid #FF4500; background: #1A1A1A; padding: 10px; margin-bottom: 8px; border-radius: 4px; color: #EEEDEB; font-size: 13px;'>{pt}</div>" for pt in meta['reddit_pain_points']])
            
            st.markdown(f"""
            <div style="background: #161B22; border: 1px solid #21262D; border-radius: 12px; padding: 16px 20px; margin-top: 1rem; margin-bottom: 1.5rem;">
                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 12px;">
                    <svg width="24" height="24" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
                        <circle cx="50" cy="50" r="50" fill="#FF4500"/>
                        <text x="50" y="70" font-family="Arial, sans-serif" font-weight="bold" font-size="60" fill="white" text-anchor="middle">R</text>
                    </svg>
                    <span style="font-family: 'Manrope', sans-serif; font-weight: 700; font-size: 1.1rem; color: #FFFFFF;">Reddit Signal</span>
                </div>
                {reddit_pts}
            </div>
            """, unsafe_allow_html=True)

            if st.button("View All Players in Sector", type="secondary"):
                st.session_state["show_players"] = not st.session_state.get("show_players", False)
                st.rerun()
                
            if st.session_state.get("show_players", False):
                with st.container():
                    st.markdown("### Sector Player Map")
                    players = meta.get("players", {})
                    tiers = ["public_companies", "private_giants", "rising_startups"]
                    tier_labels = {"public_companies": "Public Companies", 
                                   "private_giants": "Private Giants (>$500M)", 
                                   "rising_startups": "Rising Startups (<$500M)"}
                    tier_colors = {"public_companies": "#1D9E75", 
                                   "private_giants": "#378ADD", 
                                   "rising_startups": "#D85A30"}
                    
                    for tier in tiers:
                        tier_players = players.get(tier, [])
                        if not tier_players:
                            continue
                        st.markdown(f"<p style='border-left: 4px solid {tier_colors[tier]}; padding-left: 8px; font-family: Manrope; font-weight: 700; margin-top: 1.5rem;'>{tier_labels[tier]}</p>", unsafe_allow_html=True)
                        
                        cols = st.columns(max(min(len(tier_players), 4), 1))
                        for idx, p in enumerate(tier_players):
                            with cols[idx % 4]:
                                with st.container(border=True):
                                    st.markdown(f"**{p['name']}**")
                                    val_str = f"${p.get('market_cap_usd_bn') or p.get('valuation_usd_bn')}Bn" if (p.get('market_cap_usd_bn') or p.get('valuation_usd_bn')) else "Undisclosed"
                                    st.markdown(f"Valuation: {val_str}")
                                    stage = p.get('stage', 'Public')
                                    st.markdown(f"Stage: <span style='color:{tier_colors[tier]}'>{stage}</span>", unsafe_allow_html=True)
                                    st.markdown(f"HQ: {p.get('hq', 'Unknown')}")
                                    if st.button(f"Deep Dive: {p['name']}", key=f"dd_{tier}_{p['name']}"):
                                        st.session_state["selected_company"] = p['name']
                                        st.rerun()
            
            if st.session_state.get("selected_company"):
                try:
                    from components.company_drawer import render_company_drawer
                    all_data = {
                        "ratings": ratings_data,
                        "trends": trends_df,
                        "news": news_data,
                        "jobs": jobs_data,
                        "employer": employer_data,
                        "sentiment": sentiment_data
                    }
                    render_company_drawer(st.session_state["selected_company"], selected_sector, all_data)
                except ImportError:
                    st.warning("Company drawer component not yet integrated.")

        st.markdown("<div style='height: 2rem'></div>", unsafe_allow_html=True)
        st.markdown("<p class='chart-title'>Live Activity Pulse</p>", unsafe_allow_html=True)
        render_nixtio_metrics_grid([
            {"label": "Avg App Rating", "value": f"{avg_rating}", "delta": "★ Play Store"},
            {"label": "Hiring Leader", "value": top_hire_co, "delta": f"{top_hire_n} Openings"},
            {"label": "News Visibility", "value": format_large_number(total_news), "delta": "Mentions (30d)"}
        ])
        st.markdown("<div style='height: 1rem'></div>", unsafe_allow_html=True)
                
        # --- Company Health Scorecard ---
        import random
        max_jobs = max(list(jobs_data.values()) + [1]) if jobs_data else 1
        max_news = max(list(news_data.values()) + [1]) if news_data else 1
        
        score_data = []
        for co in companies:
            app_s = (ratings_data.get(co, {}).get("rating", 0) / 5.0) * 25
            hire_s = min((jobs_data.get(co, 0) / max_jobs) * 25, 25)
            
            brand_val = 0
            if not trends_df.empty and co in trends_df.columns:
                try: brand_val = float(trends_df[co].iloc[-1])
                except: pass
            brand_s = (brand_val / 100) * 20
            
            news_s = min((news_data.get(co, 0) / max_news) * 15, 15)
            
            emp_val = employer_data.get(co, 1.0)
            if emp_val < 1: emp_val = 1.0
            emp_s = ((emp_val - 1) / 4) * 15
            
            overall = round(app_s + hire_s + brand_s + news_s + emp_s, 1)
            
            rng = random.Random(co)
            trend_val = rng.choice(["Up ⬆", "Flat ➖", "Down ⬇"])
            
            score_data.append({
                "Company": co,
                "Overall Score": overall,
                "App": round(app_s, 1),
                "Hiring": round(hire_s, 1),
                "Brand": round(brand_s, 1),
                "News": round(news_s, 1),
                "Employer": round(emp_s, 1),
                "Trend": trend_val
            })
            
        score_df = pd.DataFrame(score_data).sort_values("Overall Score", ascending=False).reset_index(drop=True)
        score_df.index = score_df.index + 1
        score_df = score_df.reset_index().rename(columns={"index": "Rank"})
        # Convert all string columns to plain str to avoid LargeUtf8 Arrow serialization error
        # Works across pandas 1.x, 2.x, and 3.x
        for col in score_df.columns:
            if score_df[col].dtype == "object" or str(score_df[col].dtype) in ("string", "str"):
                score_df[col] = score_df[col].astype(str)
        
        st.markdown("<p class='chart-title'>Company Health Scorecard</p>", unsafe_allow_html=True)
        st.dataframe(score_df, use_container_width=True, hide_index=True)
        st.caption("Composite score across product, talent, brand, press and employer dimensions.")
        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown(f"""
        <div class='insight-box'>
            <h4>💡 Analyst Momentum Insight</h4>
            <p>{sector_config["insight"]}</p>
        </div>""", unsafe_allow_html=True)

        # --- Competitive Positioning Matrix ---
        scatter_data = []
        for co in companies:
            x_val = 0
            if not trends_df.empty and co in trends_df.columns:
                try:
                    x_val = float(trends_df[co].iloc[-1])
                except:
                    pass
            
            y_val = 0
            if ratings_data and co in ratings_data:
                y_val = (ratings_data[co].get("rating", 0) / 5) * 100
                
            size = jobs_data.get(co, 0) if jobs_data else 0
            
            scatter_data.append({
                "Company": co,
                "Brand Momentum": x_val,
                "Product Score": y_val,
                "Open Roles": max(size, 5),
                "Jobs": size
            })
            
        sdf = pd.DataFrame(scatter_data)
        
        st.markdown("<p class='chart-title'>Competitive Positioning Matrix</p>", unsafe_allow_html=True)
        st.markdown("<p class='chart-subtitle'>Bubble size = hiring velocity &nbsp;|&nbsp; X = brand momentum &nbsp;|&nbsp; Y = product quality</p>", unsafe_allow_html=True)
        with st.container(border=True):
            fig_scatter = px.scatter(
                sdf, x="Brand Momentum", y="Product Score", size="Open Roles",
                color="Company", color_discrete_sequence=get_color_seq(sdf, "Company", cmap), text="Company",
                hover_data={"Jobs": True, "Open Roles": False}
            )
            
            fig_scatter.add_vline(x=50, line_dash="dash", line_color="#2A1A4A", opacity=0.7)
            fig_scatter.add_hline(y=50, line_dash="dash", line_color="#2A1A4A", opacity=0.7)
            
            # Quadrant Labels
            fig_scatter.add_annotation(x=98, y=98, text="<b>Leaders</b>", showarrow=False, font=dict(color="#81C784", size=14), xanchor="right", yanchor="top")
            fig_scatter.add_annotation(x=2, y=98, text="<b>Hidden gems</b>", showarrow=False, font=dict(color="#B388FF", size=14), xanchor="left", yanchor="top")
            fig_scatter.add_annotation(x=98, y=2, text="<b>Hype vs reality</b>", showarrow=False, font=dict(color="#FFB74D", size=14), xanchor="right", yanchor="bottom")
            fig_scatter.add_annotation(x=2, y=2, text="<b>Watch list</b>", showarrow=False, font=dict(color="#E57373", size=14), xanchor="left", yanchor="bottom")
            
            fig_scatter.update_traces(
                textposition="top center", 
                textfont=dict(family="Inter", size=11, color="#EEEDEB"),
                marker=dict(sizemin=4, line=dict(width=1.5, color="#15111B"))
            )
            fig_scatter.update_xaxes(range=[-5, 105])
            fig_scatter.update_yaxes(range=[-5, 105])
            
            apply_layout(fig_scatter, 450)
            apply_nixtio_theme(fig_scatter)
            fig_scatter.update_layout(showlegend=False)
            st.plotly_chart(fig_scatter, use_container_width=True)
            
        st.markdown("<br>", unsafe_allow_html=True)

        # --- Funding Landscape ---
        funding_dict = sector_config.get("funding", {})
        if funding_dict:
            st.markdown("<p class='chart-title'>Funding Landscape</p>", unsafe_allow_html=True)
            
            funding_data = []
            for co in companies:
                if co in funding_dict:
                    f = funding_dict[co]
                    funding_data.append({
                        "Company": co,
                        "Last Round": f.get("last_round", ""),
                        "Amount ($M)": f.get("amount_usd_m", 0),
                        "Year": f.get("year", ""),
                        "Total Raised ($M)": f.get("total_raised_usd_m", 0),
                        "Valuation Tier": f.get("valuation_tier", "")
                    })
            
            if funding_data:
                fdf = pd.DataFrame(funding_data)
                total_sector_raised_m = fdf["Total Raised ($M)"].sum()
                total_sector_raised_bn = total_sector_raised_m / 1000.0
                
                with st.container(border=True):
                    render_nixtio_metrics_grid([{"label": "Total Capital Raised", "value": f"${total_sector_raised_bn:.2f}B", "delta": "Sector Total"}])
                    
                    fdf_sorted = fdf.sort_values("Total Raised ($M)", ascending=True)
                    tier_colors = {
                        "Bootstrapped": "#9E9E9E",
                        "Growth": "#81C784",
                        "Soonicorn": "#FFB74D",
                        "Unicorn": "#B388FF",
                        "Public": "#378ADD",
                        "Private Enterprise": "#5C6BC0"
                    }
                    
                    fig_fund = px.bar(
                        fdf_sorted, x="Total Raised ($M)", y="Company", 
                        color="Valuation Tier", color_discrete_map=tier_colors,
                        orientation="h", text="Total Raised ($M)"
                    )
                    fig_fund.update_traces(textposition="outside", textfont=dict(color="#FFF"))
                    apply_layout(fig_fund, 350)
                    apply_nixtio_theme(fig_fund)
                    st.plotly_chart(fig_fund, use_container_width=True)
                    
                    st.markdown("<p class='chart-subtitle' style='margin-top:1rem; margin-bottom:0.5rem;'>Cap Table & Latest Round Details</p>", unsafe_allow_html=True)
                    display_fdf = fdf.drop(columns=["Total Raised ($M)"]).sort_values("Amount ($M)", ascending=False).set_index("Company")
                    st.dataframe(display_fdf, use_container_width=True)
                    
            st.markdown("<br>", unsafe_allow_html=True)

        st.markdown("<p class='chart-title'>Search Interest Over Time</p>", unsafe_allow_html=True)
        with st.container(border=True):
            if not trends_df.empty:
                tdf = trends_df.drop(columns=["isPartial"], errors="ignore").reset_index()
                date_col = tdf.columns[0]
                val_cols = [c for c in tdf.columns if c != date_col]
                long = tdf.melt(id_vars=[date_col], value_vars=val_cols, var_name="Company", value_name="Interest")
                fig3 = px.line(long, x=date_col, y="Interest", color="Company", color_discrete_sequence=get_color_seq(long, "Company", cmap))
                fig3.update_traces(line=dict(width=3, shape="spline"), mode="lines")
                apply_layout(fig3, 300)
                apply_nixtio_theme(fig3)
                st.plotly_chart(fig3, use_container_width=True)
            else:
                st.info("Google Trends data unavailable.")

        # --- Analyst Intelligence Memo ---
        st.markdown("<br><p class='chart-title'>Analyst Intelligence Memo</p>", unsafe_allow_html=True)
        
        memo_key = f"memo_{selected_sector}"
        
        if st.button("Generate AI Memo"):
            with st.spinner("Compiling strategic intelligence..."):
                try:
                    import anthropic
                    from datetime import datetime
                    
                    # Compute dynamic metrics for the prompt
                    brand_leader = "N/A"
                    if not trends_df.empty:
                        lasts = []
                        for co in companies:
                            if co in trends_df.columns:
                                try:
                                    lasts.append((co, float(trends_df[co].iloc[-1])))
                                except: pass
                        if lasts:
                            brand_leader = max(lasts, key=lambda x: x[1])[0]

                    user_prompt = f"""
Sector: {selected_sector}
Companies: {', '.join(companies)}
Top hiring company: {top_hire_co} with {top_hire_n} open roles
Brand leader: {brand_leader}
App ratings: {ratings_data}
News mentions: {news_data}
Employer scores: {employer_data}

Write a 3-paragraph analyst memo:
Para 1: What is the single most important strategic signal in this data?
Para 2: Which company is best positioned for the next 12 months and why?
Para 3: What should the reader's company specifically watch out for?

Keep each paragraph to 3 sentences max. Start each with a bold headline.
"""
                    anthropic_api_key = st.secrets.get("ANTHROPIC_API_KEY", "")
                    if not anthropic_api_key or "paste_" in anthropic_api_key:
                        raise ValueError("Valid ANTHROPIC_API_KEY is missing from .streamlit/secrets.toml")
                        
                    client = anthropic.Anthropic(api_key=anthropic_api_key)
                    
                    response = client.messages.create(
                        model="claude-sonnet-4-20250514",
                        system="You are a senior strategy analyst at a top-tier consulting firm. Write in crisp, executive language. No fluff. Short paragraphs.",
                        messages=[{"role": "user", "content": user_prompt}],
                        max_tokens=800
                    )
                    
                    import datetime
                    st.session_state[memo_key] = {
                        "content": response.content[0].text,
                        "timestamp": datetime.datetime.now().strftime("%B %d, %Y - %H:%M")
                    }
                except Exception as e:
                    st.error(f"AI Memo generation failed: {e}")
                    
        if memo_key in st.session_state:
            memo_data = st.session_state[memo_key]
            # Replace newlines with <br> for HTML rendering, or just use markdown directly!
            # Since st.markdown allows both markdown syntax and HTML, let's wrap it in a container
            st.markdown(f"""
            <div style='border-left: 4px solid #378ADD; background: rgba(55,138,221,0.05); padding: 1.5rem; border-radius: 4px; margin-top: 1rem; font-family: Inter, sans-serif; font-size: 0.95rem; line-height: 1.6; color: #EEEDEB;'>
                {memo_data["content"].replace(chr(10), "<br>")}
            </div>
            <div style='font-size: 0.8rem; color: #8E8D92; margin-top: 0.5rem; text-align: right;'>
                Last updated: {memo_data["timestamp"]}
            </div>
            """, unsafe_allow_html=True)


    elif view == "Quantitative Momentum":
        st.markdown("<h2 class='page-header'>Quantitative Momentum</h2>", unsafe_allow_html=True)
        st.markdown("<p style='color:#8B949E; margin-left: 0.5rem;'>Advanced quantitative momentum scoring and ecosystem regime tracking designed for investment professionals and operational analysts.</p>", unsafe_allow_html=True)
        
        # 1. Fetch data from FastAPI backend (or simulate in demo mode)
        with st.spinner("Calculating quantitative momentum signals..."):
            momentum_data = None
            if st.session_state.demo_mode:
                # Local mock generator for demo mode
                now = datetime.date.today()
                mock_history = []
                for i in range(30):
                    date_str = (now - datetime.timedelta(days=30-i)).strftime("%Y-%m-%d")
                    mock_history.append({"date": date_str, "score": round(50.0 + i*0.5 + (i%3)*2, 1)})
                
                # Mock report
                mock_report = {
                    "sector": selected_sector,
                    "composite_score": 72.4,
                    "regime": "bull",
                    "signal_deltas": {
                        "trend_score": {"wow": 0.8, "mom": 1.2},
                        "news_sentiment": {"wow": -0.2, "mom": 0.5},
                        "hiring_velocity": {"wow": 1.5, "mom": 2.4},
                        "app_health": {"wow": 0.1, "mom": -0.3},
                        "employer_health": {"wow": 0.0, "mom": 0.1}
                    },
                    "divergence_flags": ["stealth_growth"],
                    "metrics": {
                        "trend_score": 7.5,
                        "news_sentiment": 6.8,
                        "hiring_velocity": 8.2,
                        "app_health": 7.1,
                        "employer_health": 6.4
                    }
                }
                momentum_data = {"report": mock_report, "backtest": mock_history}
            else:
                try:
                    import httpx
                    api_url = f"http://localhost:8000/analytics/momentum/{selected_sector}"
                    with httpx.Client(timeout=10.0) as client:
                        resp = client.get(api_url)
                        resp.raise_for_status()
                        momentum_data = resp.json()
                except Exception as e:
                    st.warning("Could not connect to live Momentum API. Using local high-fidelity fallback.")
                    # Safe fallback same as demo mode
                    now = datetime.date.today()
                    mock_history = []
                    for i in range(30):
                        date_str = (now - datetime.timedelta(days=30-i)).strftime("%Y-%m-%d")
                        mock_history.append({"date": date_str, "score": round(52.5 + i*0.4 + (i%4)*1.5, 1)})
                    
                    mock_report = {
                        "sector": selected_sector,
                        "composite_score": 68.5,
                        "regime": "bull",
                        "signal_deltas": {
                            "trend_score": {"wow": 0.5, "mom": 0.9},
                            "news_sentiment": {"wow": 0.2, "mom": 0.4},
                            "hiring_velocity": {"wow": 1.1, "mom": 1.8},
                            "app_health": {"wow": -0.1, "mom": -0.2},
                            "employer_health": {"wow": 0.0, "mom": 0.2}
                        },
                        "divergence_flags": ["stealth_growth"],
                        "metrics": {
                            "trend_score": 7.2,
                            "news_sentiment": 6.5,
                            "hiring_velocity": 7.8,
                            "app_health": 6.9,
                            "employer_health": 6.2
                        }
                    }
                    momentum_data = {"report": mock_report, "backtest": mock_history}

        # 2. Render Divergence Alerts
        report = momentum_data["report"]
        flags = report.get("divergence_flags", [])
        if flags:
            for flag in flags:
                if flag == "stealth_growth":
                    st.markdown("""
                    <div style="background: rgba(55,138,221,0.1); border-left: 5px solid #378ADD; padding: 16px; border-radius: 8px; margin-bottom: 20px;">
                        <h4 style="margin:0 0 6px 0; color:white; font-family:Manrope;">⚠️ Stealth Growth Divergence Detected</h4>
                        <p style="margin:0; color:#C9D1D9; font-size:13px;">High hiring velocity coupled with declining or flat public search interest suggests <b>under-the-radar scale</b>. The ecosystem is adding capacity and execution speed ahead of public marketing campaigns.</p>
                    </div>
                    """, unsafe_allow_html=True)
                elif flag == "hype_bubble":
                    st.markdown("""
                    <div style="background: rgba(248,81,73,0.1); border-left: 5px solid #F85149; padding: 16px; border-radius: 8px; margin-bottom: 20px;">
                        <h4 style="margin:0 0 6px 0; color:white; font-family:Manrope;">🚨 Speculative Hype Bubble Alert</h4>
                        <p style="margin:0; color:#C9D1D9; font-size:13px;">Ecosystem Google Search interest is surging extremely rapidly, but internal job postings and recruitment velocity have flattened. High consumer/market interest with limited organizational expansion indicates potential short-term speculative saturation.</p>
                    </div>
                    """, unsafe_allow_html=True)
                elif flag == "product_decay":
                    st.markdown("""
                    <div style="background: rgba(210,153,34,0.1); border-left: 5px solid #D29922; padding: 16px; border-radius: 8px; margin-bottom: 20px;">
                        <h4 style="margin:0 0 6px 0; color:white; font-family:Manrope;">%s Product Experience Decay Warning</h4>
                        <p style="margin:0; color:#C9D1D9; font-size:13px;">Customer satisfaction ratings on app stores are in steep decline (-WoW) while general brand volume and funding remains stable. Operational degradation is present; product quality needs immediate remediation.</p>
                    </div>
                    """ % "📉", unsafe_allow_html=True)
                elif flag == "toxic_scale":
                    st.markdown("""
                    <div style="background: rgba(248,81,73,0.1); border-left: 5px solid #F85149; padding: 16px; border-radius: 8px; margin-bottom: 20px;">
                        <h4 style="margin:0 0 6px 0; color:white; font-family:Manrope;">🔥 Toxic Scale Divergence Flagged</h4>
                        <p style="margin:0; color:#C9D1D9; font-size:13px;">High external ratings and growth but critical internal cultural/burnout warnings on employer tracking platforms. Operational disruption is a risk; high employee turnover could impact product velocity within 90-180 days.</p>
                    </div>
                    """, unsafe_allow_html=True)

        # 3. Main Dashboard Columns
        col_left, col_right = st.columns([1, 1.2])
        
        with col_left:
            # Gauge Plotly Indicator
            score = report["composite_score"]
            regime = report["regime"].upper()
            
            if regime == "BULL":
                r_color = "#3FB950"
            elif regime == "BEAR":
                r_color = "#F85149"
            else:
                r_color = "#D29922"
                
            fig_gauge = go.Figure(go.Indicator(
                mode = "gauge+number",
                value = score,
                domain = {'x': [0, 1], 'y': [0, 1]},
                title = {'text': f"REGIME: {regime}", 'font': {'size': 20, 'family': 'Manrope', 'color': r_color}},
                number = {'font': {'size': 64, 'family': 'Manrope', 'color': 'white'}},
                gauge = {
                    'axis': {'range': [None, 100], 'tickwidth': 1, 'tickcolor': "#21262D"},
                    'bar': {'color': r_color},
                    'bgcolor': "rgba(255,255,255,0.03)",
                    'borderwidth': 2,
                    'bordercolor': "#21262D",
                    'steps': [
                        {'range': [0, 45], 'color': 'rgba(248,81,73,0.1)'},
                        {'range': [45, 65], 'color': 'rgba(210,153,34,0.1)'},
                        {'range': [65, 100], 'color': 'rgba(63,185,80,0.1)'}
                    ],
                }
            ))
            fig_gauge.update_layout(height=320, margin=dict(t=50, b=20, l=30, r=30), paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_gauge, use_container_width=True, config={'displayModeBar': False})
            
            # Regime Description Card
            st.markdown(f"""
            <div style="background: rgba(255,255,255,0.02); border: 1px solid #21262D; border-radius: 12px; padding: 20px; text-align:center;">
                <div style="font-size:12px; color:#8B949E; text-transform:uppercase; letter-spacing:1px; margin-bottom:6px;">Current Regime Index</div>
                <div style="font-size:24px; font-weight:800; color:{r_color}; font-family:Manrope;">{regime} MODE</div>
                <div style="font-size:13px; color:#C9D1D9; margin-top:8px; line-height:1.5;">
                    {"Ecosystem is expanding sustainably with strong operational and search metrics." if regime == "BULL" else
                     "Ecosystem is retracting or showing operational strain. Capital and labor resources should be preserved." if regime == "BEAR" else
                     "Ecosystem is consolidating. Balanced metrics with horizontal movement."}
                </div>
            </div>
            """, unsafe_allow_html=True)

        with col_right:
            st.markdown("<p class='chart-title'>Ecosystem Signal Scorecard</p>", unsafe_allow_html=True)
            
            # Custom HTML table for signal deltas
            metrics_display = {
                "trend_score": "Search Interest (Trends)",
                "news_sentiment": "Media Coverage Sentiment",
                "hiring_velocity": "Recruitment & Job Openings",
                "app_health": "Consumer App Store Reviews",
                "employer_health": "Employee Satisfaction Score"
            }
            

            # Signal scorecard — rendered with native Streamlit so no raw HTML leaks
            def _delta_html(delta):
                if delta > 0:
                    return f"<span style='color:#3FB950;font-weight:600;'>▲ {abs(delta):.1f}</span>"
                elif delta < 0:
                    return f"<span style='color:#F85149;font-weight:600;'>▼ {abs(delta):.1f}</span>"
                else:
                    return "<span style='color:#8B949E;font-weight:600;'>—</span>"

            header_cols = st.columns([4, 2, 2, 2])
            header_cols[0].markdown("<span style='font-size:11px;color:#8B949E;text-transform:uppercase;letter-spacing:.5px;font-weight:600;'>Signal Name</span>", unsafe_allow_html=True)
            header_cols[1].markdown("<span style='font-size:11px;color:#8B949E;text-transform:uppercase;letter-spacing:.5px;font-weight:600;float:right;'>Score</span>", unsafe_allow_html=True)
            header_cols[2].markdown("<span style='font-size:11px;color:#8B949E;text-transform:uppercase;letter-spacing:.5px;font-weight:600;float:right;'>WoW</span>", unsafe_allow_html=True)
            header_cols[3].markdown("<span style='font-size:11px;color:#8B949E;text-transform:uppercase;letter-spacing:.5px;font-weight:600;float:right;'>MoM</span>", unsafe_allow_html=True)
            st.markdown("<hr style='margin:4px 0 8px 0;border-color:#30363D;'>", unsafe_allow_html=True)

            for metric_key, label in metrics_display.items():
                cur_val = report["metrics"][metric_key]
                wow     = report["signal_deltas"][metric_key]["wow"]
                mom     = report["signal_deltas"][metric_key]["mom"]

                row = st.columns([4, 2, 2, 2])
                row[0].markdown(f"<span style='font-weight:600;color:white;font-size:13px;'>{label}</span>", unsafe_allow_html=True)
                row[1].markdown(f"<div style='text-align:right;font-weight:700;color:#378ADD;font-size:14px;'>{cur_val:.1f}/10</div>", unsafe_allow_html=True)
                row[2].markdown(f"<div style='text-align:right;'>{_delta_html(wow)}</div>", unsafe_allow_html=True)
                row[3].markdown(f"<div style='text-align:right;'>{_delta_html(mom)}</div>", unsafe_allow_html=True)
                st.markdown("<hr style='margin:4px 0;border-color:#21262D;'>", unsafe_allow_html=True)

            st.caption("All signals are normalized to a 0–10 scale (10 = maximum performance).")

        # 4. Historical Backtest Chart
        st.markdown("<div style='height: 2.5rem'></div>", unsafe_allow_html=True)
        st.markdown("<p class='chart-title'>Ecosystem Backtest Performance (30-Day Index)</p>", unsafe_allow_html=True)
        
        backtest_df = pd.DataFrame(momentum_data["backtest"])
        if not backtest_df.empty:
            fig_backtest = px.area(backtest_df, x="date", y="score", color_discrete_sequence=["#378ADD"])
            fig_backtest.update_traces(line=dict(width=3, shape="spline"), mode="lines+markers")
            
            # NixTio premium formatting
            apply_layout(fig_backtest, 320)
            apply_nixtio_theme(fig_backtest)
            fig_backtest.update_yaxes(range=[0, 100])
            st.plotly_chart(fig_backtest, use_container_width=True)
        else:
            st.info("Ecosystem backtest data loading...")


    elif view == "Brand Dashboard":
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("<p class='chart-title'>News Mentions (Past 30 Days)</p>", unsafe_allow_html=True)
            with st.container(border=True):
                if news_data and any(v > 0 for v in news_data.values()):
                    ndf = pd.DataFrame([{"Company": k, "Mentions": v} for k, v in news_data.items()]).sort_values("Mentions", ascending=True)
                    fig_news = px.bar(ndf, x="Mentions", y="Company", color="Company", color_discrete_sequence=get_color_seq(ndf, "Company", cmap), orientation="h", text="Mentions")
                    fig_news.update_traces(textposition="outside", textfont=dict(color="#FFF"))
                    apply_layout(fig_news, 400)
                    apply_nixtio_theme(fig_news)
                    fig_news.update_layout(showlegend=False)
                    st.plotly_chart(fig_news, use_container_width=True)
                else:
                    st.info("No news data.")
        with c2:
            st.markdown("<p class='chart-title'>Brand Interest Distribution</p>", unsafe_allow_html=True)
            with st.container(border=True):
                if not trends_df.empty:
                    tcols = [c for c in trends_df.columns if c not in ("date", "isPartial")]
                    avgs = trends_df[tcols].mean().reset_index()
                    avgs.columns = ["Company", "Avg Interest"]
                    fig_pie = px.pie(avgs, names="Company", values="Avg Interest", color="Company", color_discrete_sequence=get_color_seq(avgs, "Company", cmap), hole=0.6)
                    fig_pie.update_traces(textposition='inside', textinfo='percent+label', marker=dict(line=dict(color='#15111B', width=2)))
                    apply_nixtio_theme(fig_pie)
                    fig_pie.update_layout(showlegend=False, height=400)
                    st.plotly_chart(fig_pie, use_container_width=True)
                else:
                    st.info("No trend data.")


    elif view == "Talent Pool & CX":
        colA, colB = st.columns([1, 1])
        with colA:
            st.markdown("<p class='chart-title'>Hiring Velocity</p>", unsafe_allow_html=True)
            with st.container(border=True):
                if jobs_data and any(v > 0 for v in jobs_data.values()):
                    jdf = pd.DataFrame([{"Company": k, "Open Roles": v} for k, v in jobs_data.items()]).sort_values("Open Roles", ascending=False)
                    fig2 = px.bar(jdf, x="Company", y="Open Roles", color="Company", color_discrete_sequence=get_color_seq(jdf, "Company", cmap), text="Open Roles")
                    fig2.update_traces(textposition="outside", textfont=dict(color="#FFF"))
                    apply_layout(fig2, 350)
                    apply_nixtio_theme(fig2)
                    fig2.update_layout(showlegend=False)
                    st.plotly_chart(fig2, use_container_width=True)
                else:
                    st.info("No hiring data.")
        with colB:
            st.markdown("<p class='chart-title'>CSAT & App Ratings</p>", unsafe_allow_html=True)
            with st.container(border=True):
                if ratings_data:
                    rdf = pd.DataFrame([{"Company": k, "Rating": v["rating"]} for k, v in ratings_data.items() if v["rating"] > 0])
                    if not rdf.empty:
                        fig1 = px.bar(rdf, x="Company", y="Rating", color="Company", color_discrete_sequence=get_color_seq(rdf, "Company", cmap), text="Rating")
                        fig1.update_traces(textposition="outside", textfont=dict(color="#FFF"), width=0.5)
                        fig1.update_yaxes(range=[0, 5])
                        apply_layout(fig1, 350)
                        apply_nixtio_theme(fig1)
                        fig1.update_layout(showlegend=False)
                        st.plotly_chart(fig1, use_container_width=True)
                    else:
                        st.info("No ratings.")
                else:
                    st.info("No ratings.")

        st.markdown("<br>", unsafe_allow_html=True)
        
        # --- Review Sentiment Analysis ---
        st.markdown("<p class='chart-title'>Review Sentiment</p>", unsafe_allow_html=True)
        if sentiment_data:
            s_list = []
            for co, v in sentiment_data.items():
                if v["review_count"] > 0:
                    s_list.append({"Company": co, "Sentiment": "Positive", "Percentage": v["positive_pct"]})
                    s_list.append({"Company": co, "Sentiment": "Neutral", "Percentage": v["neutral_pct"]})
                    s_list.append({"Company": co, "Sentiment": "Negative", "Percentage": v["negative_pct"]})
            
            if s_list:
                with st.container(border=True):
                    sdf = pd.DataFrame(s_list)
                    color_m = {"Positive": "#81C784", "Neutral": "#9E9E9E", "Negative": "#E57373"}
                    fig_s = px.bar(sdf, y="Company", x="Percentage", color="Sentiment", 
                                   orientation='h', barmode='stack', color_discrete_map=color_m)
                    apply_layout(fig_s, max(250, len(sentiment_data)*60))
                    apply_nixtio_theme(fig_s)
                    fig_s.update_traces()
                    # Show legend at the top
                    fig_s.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, title=None))
                    st.plotly_chart(fig_s, use_container_width=True)
                    
                    st.markdown("<div style='display:flex; flex-wrap:wrap; gap:20px; align-items:flex-start; margin-top:10px'>", unsafe_allow_html=True)
                    for co in sentiment_data:
                        if sentiment_data[co]["review_count"] > 0:
                            v = sentiment_data[co]
                            pills = "".join([f"<span style='background:#E57373; padding:2px 8px; border-radius:12px; font-size:0.75rem; color:#1A1A1A; font-family:Inter; font-weight:600; margin-right:4px;'>{w}</span>" for w in v["top_complaints"][:3]])
                            st.markdown(f"<div><span style='color:#EEEDEB; font-family:Inter; font-size:0.85rem; font-weight:600; margin-bottom:4px; display:inline-block'>🚨 {co} Complaints:</span><br>{pills}</div>", unsafe_allow_html=True)
                    st.markdown("</div>", unsafe_allow_html=True)
                    st.caption("Based on top 100 most relevant Play Store reviews")
            else:
                st.info("No sentiment data generated.")
        else:
            st.info("No Play Store apps available for this sector to analyse.")


    elif view == "Generate Report":
        st.markdown("<h2 class='page-header'>Generate Report</h2>", unsafe_allow_html=True)
        st.markdown("""
            <p style='color:#8E8D92; font-size:1.1rem; max-width:800px'>Compile latest intelligence, search momentum, 
            and talent velocity into a fully annotated executive PDF report.</p>
        """, unsafe_allow_html=True)
        
        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
        
        if "saas_token" not in st.session_state or not st.session_state.saas_token:
            st.warning("🔒 **SaaS Premium Feature Gated**\n\nReport generation is restricted to authenticated NixTio organizations. Please sign in or register your organization in the sidebar to generate custom executive PDF reports.")
        else:
            left, right = st.columns([1, 2])
            with left:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("📄 Generate Intelligence Report"):
                    with st.status("Requesting background generation...") as status:
                        try:
                            import httpx
                            api_url = "http://localhost:8000/report/generate"
                            
                            # Prepare data for report (convert DFs to dicts)
                            report_data = {}
                            for k, v in sector_data.results.items():
                                report_data[k] = v.copy()
                                if isinstance(v.get("data"), pd.DataFrame):
                                    report_data[k]["data"] = v["data"].to_dict(orient="records")
                            
                            headers = {"Authorization": f"Bearer {st.session_state.saas_token}"}
                            resp = httpx.post(api_url, json={
                                "sector": selected_sector,
                                "companies": companies,
                                "data": report_data
                            }, headers=headers)
                            resp.raise_for_status()
                            job_id = resp.json()["job_id"]
                            
                            # Poll for status
                            status.update(label=f"Job {job_id} queued...", state="running")
                            while True:
                                check = httpx.get(f"http://localhost:8000/report/status/{job_id}")
                                check_status = check.json()["status"]
                                if check_status == "done":
                                    status.update(label="Report ready!", state="complete")
                                    break
                                elif check_status == "failed":
                                    status.update(label="Generation failed", state="error")
                                    st.error("The background report generation job failed.")
                                    break
                                time.sleep(1)
                            
                            if check_status == "done":
                                # In a real app, we might download from a URL. 
                                # For now, we'll assume we can still generate locally or fetch the bytes.
                                # Since the user asked for BackgroundTasks, polling is correct.
                                st.success("Report generated successfully on backend.")
                                # Add download button if we have a way to fetch the file
                                # For now, simulate history log
                                ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                st.session_state.history.append({"time": ts, "sector": selected_sector, "type": "PDF Report (API)"})
                        except Exception as e:
                            st.error(f"API Report generation failed: {e}")


    elif view == "Report History":
        st.markdown("<div class='page-header'>Exported Reports History</div>", unsafe_allow_html=True)
        history = st.session_state.history
        
        if len(history) == 0:
            st.info("No reports generated during this session.")
        else:
            for item in reversed(history):
                st.markdown(f"""
                <div class='log-row'>
                    <div>
                        <span style='font-family:Manrope; font-weight:700'>{item['sector']}</span>
                        <div style='font-size:0.8rem; color:#8E8D92'>{item['type']}</div>
                    </div>
                    <div style='color:#D4E157; font-family:Inter; font-size:0.85rem'>{item['time']}</div>
                </div>
                """, unsafe_allow_html=True)


    elif view == "About Product":
        st.markdown("<div class='page-header'>About the Application</div>", unsafe_allow_html=True)
        st.markdown("""
        <div style='background:#15111B; border: 1px solid #2A1A4A; border-radius: 20px; padding: 2.5rem; text-align:center;'>
            <div style='margin: 0 auto 1rem auto; width: 80px; height: 80px;'>
                <svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
                    <defs><linearGradient id="g2" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" style="stop-color:#B388FF"/>
                        <stop offset="100%" style="stop-color:#7E57C2"/>
                    </linearGradient></defs>
                    <circle cx="40" cy="40" r="30" fill="url(#g2)" opacity="0.8"/>
                    <circle cx="60" cy="60" r="30" fill="#D4E157" opacity="0.9"/>
                    <circle cx="50" cy="50" r="15" fill="#15111B"/>
                </svg>
            </div>
            <h2 style='font-family:Manrope; color:#FFF; margin-bottom:0.5rem'>nix<span style='color:#B388FF'>tio</span> intelligence</h2>
            <p style='color:#8E8D92; max-width:600px; margin:0 auto; line-height:1.6'>
                An enterprise-grade competitive intelligence tracker compiling 
                market signals from Google Trends, LinkedIn Hiring Data, and Play Store Sentiment.
                Designed for high-performance executive analytics.
            </p>
            <br><br>
            <div style='display:inline-block; border-top: 1px solid #2A1A4A; padding-top:1.5rem'>
                <span style='color:#8E8D92; font-size:0.85rem'>Engineered & Managed by</span><br>
                <strong style='color:#FFF; font-size:1.1rem'>Mrinmoy Banikya</strong>
        </div>
        """, unsafe_allow_html=True)

    elif view == "AI Analyst":
        st.markdown("<p class='page-header'>AI Strategy Analyst</p>", unsafe_allow_html=True)
        
        groq_key = st.secrets.get("GROQ_API_KEY")
        if not groq_key:
            st.markdown("""
            <div style='background: rgba(255,183,77,0.1); border: 1px solid #FFB74D; border-radius: 12px; padding: 2rem; text-align: center;'>
                <p style='color: #FFB74D; font-size: 1.1rem; font-weight: 600;'>Configure your Groq API key in Settings to unlock AI analysis</p>
                <p style='color: #8E8D92; font-size: 0.9rem;'>The AI Analyst requires a valid Groq API key to process sector intelligence.</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            # Sector data dict for the analyst
            sector_data = {
                "metrics": SECTOR_META.get(selected_sector, {}),
                "companies": companies,
                "news": news_data,
                "jobs": jobs_data,
                "ratings": ratings_data
            }
            
            col_an_1, col_an_2 = st.columns([2, 1])
            with col_an_1:
                st.markdown(f"**Target Sector:** {selected_sector}")
                st.markdown(f"**Data Points:** {len(companies)} companies, {sum(news_data.values())} news items, {sum(jobs_data.values())} open roles.")
            with col_an_2:
                generate = st.button("Generate Sector Intelligence Analysis", type="primary", use_container_width=True)
            
            if generate:
                render_typing_indicator()
                with st.spinner("Llama-3.3-70b-versatile is processing data..."):
                    analysis = generate_sector_analysis(selected_sector, sector_data)
                    if "error" in analysis:
                        st.error(analysis["error"])
                    else:
                        st.session_state["current_analysis"] = analysis
            
            if "current_analysis" in st.session_state:
                analysis = st.session_state["current_analysis"]
                
                # CSS for analysis cards
                st.markdown("""
                <style>
                .analysis-card { background: #1A1525; border-left: 4px solid #378ADD; padding: 15px; border-radius: 8px; margin-bottom: 10px; }
                .analysis-title { color: #378ADD; font-weight: bold; margin-bottom: 5px; font-size: 0.9rem; text-transform: uppercase; }
                .analysis-content { color: #EEEDEB; font-size: 0.95rem; line-height: 1.4; }
                </style>
                """, unsafe_allow_html=True)

                with st.expander("📊 Market Momentum", expanded=True):
                    st.markdown(f"<div class='analysis-card'><div class='analysis-content'>{analysis.get('momentum', 'N/A')}</div></div>", unsafe_allow_html=True)
                with st.expander("⚔️ Competitive Positioning"):
                    st.markdown(f"<div class='analysis-card'><div class='analysis-content'>{analysis.get('competitive_position', 'N/A')}</div></div>", unsafe_allow_html=True)
                with st.expander("🧬 Talent & Roadmap Signals"):
                    st.markdown(f"<div class='analysis-card'><div class='analysis-content'>{analysis.get('talent_signal', 'N/A')}</div></div>", unsafe_allow_html=True)
                with st.expander("⚠️ Risk Assessment"):
                    st.markdown(f"<div class='analysis-card'><div class='analysis-content'>{analysis.get('risk_factors', 'N/A')}</div></div>", unsafe_allow_html=True)
                with st.expander("💡 Strategic Recommendations"):
                    st.markdown(f"<div class='analysis-card'><div class='analysis-content'>{analysis.get('recommendations', 'N/A')}</div></div>", unsafe_allow_html=True)
                
                st.markdown("---")
                st.markdown("### Ask follow-up questions")
                
                if "ai_chat_history" not in st.session_state:
                    st.session_state.ai_chat_history = []
                
                for chat in st.session_state.ai_chat_history:
                    with st.chat_message(chat["role"]):
                        st.markdown(chat["content"])
                
                if chat_prompt := st.chat_input("Ask the analyst about this sector..."):
                    st.session_state.ai_chat_history.append({"role": "user", "content": chat_prompt})
                    with st.chat_message("user"):
                        st.markdown(chat_prompt)
                    
                    with st.chat_message("assistant"):
                        context = f"Sector: {selected_sector}\nAnalysis Overview: {analysis.get('momentum', '')} {analysis.get('recommendations', '')}"
                        response = st.write_stream(stream_analyst_response(chat_prompt, context))
                        st.session_state.ai_chat_history.append({"role": "assistant", "content": response})

    elif view == "Settings ⚙":
        st.markdown("<p class='page-header'>System Settings</p>", unsafe_allow_html=True)
        
        st.markdown("### API Configuration")
        st.info("Settings are saved to .streamlit/secrets.toml")
        
        with st.form("settings_form"):
            new_groq_key = st.text_input("Groq API Key", value=st.secrets.get("GROQ_API_KEY", ""), type="password")
            new_news_key = st.text_input("News API Key", value=st.secrets.get("NEWS_API_KEY", ""), type="password")
            
            save = st.form_submit_button("Save Configuration", type="primary")
            
            if save:
                try:
                    secrets_path = ".streamlit/secrets.toml"
                    # Preserve existing structure
                    content = f'NEWS_API_KEY = "{new_news_key}"\n'
                    content += f'GROQ_API_KEY = "{new_groq_key}"\n'
                    content += f'IS_ADMIN = true\n\n'
                    content += '[credentials]\n'
                    content += f'email = "{st.secrets["credentials"]["email"]}"\n'
                    content += f'password = "{st.secrets["credentials"]["password"]}"\n'
                    
                    with open(secrets_path, "w") as f:
                        f.write(content)
                    st.success("Settings saved successfully! Streamlit will reload automatically.")
                except Exception as e:
                    st.error(f"Failed to save settings: {e}")


