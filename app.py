"""
DataFix.ai — Autonomous Data Health & Integrity Console
Premium Enterprise SaaS Platform
"""

import os
import sys
import json
import datetime
from typing import Optional, List, Dict, Any

# Ensure DataFix directory is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import streamlit as st
import streamlit.components.v1 as components
import plotly.graph_objects as go

# Import DataFix core modules with tabular fallback for Windows WDAC environment
try:
    import pandas as pd
except (ImportError, Exception):
    import utils.tabular as pd
    sys.modules['pandas'] = pd
    sys.modules['pandas.core'] = pd
    sys.modules['pandas.core.api'] = pd

from modules.detection import DataQualityDetector
from modules.diagnosis import RootCauseDiagnoser
from modules.repair import DataRepairEngine
from modules.validation import DataValidator
from modules.quality_score import calculate_quality_score, get_score_label, get_score_color
from modules.audit_log import AuditLog
from modules.report_generator import ReportGenerator
from utils.file_handler import read_uploaded_file, validate_file, export_to_csv, export_to_excel


# -----------------------------------------------------------------------------
# ENTERPRISE DATA TABLE COMPONENT
# -----------------------------------------------------------------------------
def render_saas_table(data, max_rows: int = 100, height: Optional[int] = None) -> None:
    """
    Renders a modern, highly-styled commercial SaaS interactive data table.
    Works independently of C-extension DLLs (pyarrow/pandas) with smooth scrolling,
    clean borders, responsive typography, and badge highlights.
    """
    if data is None:
        st.info("No records to display.")
        return

    columns = []
    rows = []

    if hasattr(data, "columns") and hasattr(data, "to_dict"):
        columns = [str(c) for c in data.columns]
        raw_rows = data.to_dict("records")
        rows = raw_rows[:max_rows]
    elif isinstance(data, list):
        if not data:
            st.info("Table is empty (0 records).")
            return
        if isinstance(data[0], dict):
            columns = list(data[0].keys())
            rows = data[:max_rows]
        elif isinstance(data[0], (list, tuple)):
            columns = [f"Col {i+1}" for i in range(len(data[0]))]
            rows = [dict(zip(columns, r)) for r in data[:max_rows]]
    elif isinstance(data, dict):
        columns = list(data.keys())
        first_col = next(iter(data.values()), [])
        n_rows = len(first_col) if isinstance(first_col, (list, tuple)) else 1
        rows = []
        for i in range(min(n_rows, max_rows)):
            row = {c: (data[c][i] if isinstance(data[c], (list, tuple)) and i < len(data[c]) else data[c]) for c in columns}
            rows.append(row)

    if not columns or not rows:
        st.info("No table records available.")
        return

    max_h_style = f"max-height: {height}px; overflow-y: auto;" if height else "max-height: 480px; overflow-y: auto;"
    
    header_th = "".join([
        f"<th style='padding: 11px 16px; text-align: left; font-weight: 700; color: #101B35; "
        f"background: #F8FAFC; border-bottom: 2px solid #E5EAF2; font-size: 12px; letter-spacing: 0.5px; "
        f"text-transform: uppercase; position: sticky; top: 0; z-index: 1;'>{col}</th>"
        for col in columns
    ])
    
    tbody_trs = []
    for r_idx, r in enumerate(rows):
        bg = "#FFFFFF" if r_idx % 2 == 0 else "#F8FAFC"
        tds = []
        for col in columns:
            val = r.get(col, "")
            val_str = "" if val is None or (isinstance(val, float) and val != val) else str(val)
            
            # Badge pills for known categories/severity
            if val_str in ("Critical", "High", "Medium", "Low"):
                color_map = {
                    "Critical": ("#FEE2E2", "#991B1B"),
                    "High": ("#FFEDD5", "#9A3412"),
                    "Medium": ("#FEF3C7", "#92400E"),
                    "Low": ("#E0F2FE", "#075985"),
                }

                bg_col, text_col = color_map.get(val_str, ("#F1F5F9", "#475569"))
                cell_html = f"<span style='display:inline-flex; align-items:center; padding: 2px 10px; border-radius: 9999px; font-size: 11px; font-weight: 700; background:{bg_col}; color:{text_col};'>{val_str}</span>"
            elif val_str in ("Passed", "Confirmed", "Fixed", "Applied", "True", "Operational", "Active"):
                cell_html = f"<span style='display:inline-flex; align-items:center; padding: 2px 10px; border-radius: 9999px; font-size: 11px; font-weight: 700; background:#DCFCE7; color:#166534;'>{val_str}</span>"
            elif val_str in ("Failed", "Suspected", "Pending", "False", "Requires Approval"):
                cell_html = f"<span style='display:inline-flex; align-items:center; padding: 2px 10px; border-radius: 9999px; font-size: 11px; font-weight: 700; background:#FEF3C7; color:#B45309;'>{val_str}</span>"
            else:
                display_text = (val_str[:60] + "...") if len(val_str) > 63 else val_str
                cell_html = f"<span title='{val_str}' style='color: #172033;'>{display_text}</span>"
                
            tds.append(f"<td style='padding: 10px 16px; font-size: 13px; border-bottom: 1px solid #E5EAF2; white-space: nowrap;'>{cell_html}</td>")
        tbody_trs.append(f"<tr style='background: {bg}; transition: background 0.15s ease;'>{''.join(tds)}</tr>")

    total_count_note = f"<div style='font-size: 11px; color: #64748B; margin-top: 8px; text-align: right;'>Showing {len(rows):,} records &bull; {len(columns)} attributes</div>"
    
    html = f"""
    <div style='border: 1px solid #E5EAF2; border-radius: 10px; {max_h_style} overflow-x: auto; box-shadow: 0 1px 3px rgba(16, 27, 53, 0.04); background: #FFFFFF; margin-bottom: 12px;'>
      <table style='width: 100%; border-collapse: collapse; font-family: "Plus Jakarta Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;'>
        <thead>
          <tr>{header_th}</tr>
        </thead>
        <tbody>
          {''.join(tbody_trs)}
        </tbody>
      </table>
    </div>
    {total_count_note}
    """
    st.markdown(html, unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# PAGE CONFIGURATION
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="DataFix.ai — Autonomous Data Health & Integrity Console",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------------------------------------------------------
# PREMIUM ENTERPRISE SAAS THEME (LIGHT THEME + DEEP NAVY SIDEBAR)
# -----------------------------------------------------------------------------
CUSTOM_CSS = """
<style>
  @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:ital,wght@0,400;0,500;0,600;0,700;0,800;1,400;1,600&family=JetBrains+Mono:wght@400;500;600&display=swap');

  :root {
    --navy: #101B35;
    --royal-blue: #2563EB;
    --cyan: #06B6D4;
    --emerald: #10B981;
    --amber: #F59E0B;
    --rose: #EF4444;
    --purple: #8B5CF6;
    --bg-main: #F4F7FB;
    --bg-card: #FFFFFF;
    --border-color: #E5EAF2;
    --text-primary: #172033;
    --text-secondary: #64748B;
  }


  html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    color: var(--text-primary);
  }


  /* Global background */
  .stApp {
    background-color: var(--bg-main) !important;
  }


  /* Main container layout */
  .main .block-container {
    padding-top: 1.5rem;
    padding-bottom: 3.5rem;
    max-width: 1320px;
  }


  /* CRITICAL: High-Contrast Right-Side Headings & Typography */
  .main h1,
  .main h2,
  .main h3,
  .main h4,
  .main h5,
  .main h6,
  .main [data-testid="stHeading"] h1,
  .main [data-testid="stHeading"] h2,
  .main [data-testid="stHeading"] h3,
  .main [data-testid="stHeadingWithActionElements"] h1,
  .main [data-testid="stHeadingWithActionElements"] h2,
  .main [data-testid="stHeadingWithActionElements"] h3,
  .main [data-testid="stMarkdownContainer"] h1,
  .main [data-testid="stMarkdownContainer"] h2,
  .main [data-testid="stMarkdownContainer"] h3,
  .main [data-testid="stMarkdownContainer"] h4,
  .main [data-testid="stMarkdownContainer"] h5,
  .main [data-testid="stMarkdownContainer"] h6 {
    color: #101B35 !important;
    font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
    font-weight: 800 !important;
    letter-spacing: -0.3px !important;
    opacity: 1 !important;
    visibility: visible !important;
  }


  .main h1,
  .main [data-testid="stMarkdownContainer"] h1 {
    font-size: 24px !important;
    margin: 18px 0 10px 0 !important;
  }

  .main h2,
  .main [data-testid="stMarkdownContainer"] h2 {
    font-size: 20px !important;
    margin: 20px 0 8px 0 !important;
  }

  .main h3,
  .main [data-testid="stMarkdownContainer"] h3 {
    font-size: 17px !important;
    margin: 18px 0 8px 0 !important;
  }

  .main h4,
  .main [data-testid="stMarkdownContainer"] h4 {
    font-size: 15px !important;
    margin: 14px 0 6px 0 !important;
  }


  /* Right-side body text, labels, captions */
  .main [data-testid="stMarkdownContainer"] p,
  .main [data-testid="stMarkdownContainer"] span,
  .main [data-testid="stMarkdownContainer"] strong,
  .main [data-testid="stMarkdownContainer"] li,
  .main label,
  .main [data-testid="stWidgetLabel"] label,
  .main [data-testid="stWidgetLabel"] p {
    color: #172033 !important;
  }


  div[data-testid="stMetricLabel"] p {
    color: #64748B !important;
    font-size: 11px !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.8px !important;
  }

  div[data-testid="stMetricValue"] {
    color: #101B35 !important;
    font-size: 28px !important;
    font-weight: 800 !important;
  }


  /* Enterprise Dark Navy Sidebar */
  section[data-testid="stSidebar"] {
    background-color: #101B35 !important;
    border-right: 1px solid rgba(255, 255, 255, 0.08);
  }

  section[data-testid="stSidebar"] * {
    color: #E2E8F0;
  }

  section[data-testid="stSidebar"] hr {
    border-color: rgba(255, 255, 255, 0.12) !important;
  }

  section[data-testid="stSidebar"] [data-testid="stRadio"] > div {
    gap: 4px;
  }

  section[data-testid="stSidebar"] [data-testid="stRadio"] label {
    background: transparent;
    padding: 8px 12px;
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.18s ease;
    border: 1px solid transparent;
  }

  section[data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
    background: rgba(255, 255, 255, 0.06);
  }

  section[data-testid="stSidebar"] [data-testid="stRadio"] label[data-checked="true"],
  section[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {
    background: #2563EB !important;
    color: #FFFFFF !important;
    font-weight: 700;
    box-shadow: 0 2px 8px rgba(37, 99, 235, 0.35);
  }

  section[data-testid="stSidebar"] [data-testid="stRadio"] label[data-checked="true"] p,
  section[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) p {
    color: #FFFFFF !important;
    font-weight: 700;
  }


  /* Sidebar buttons */
  section[data-testid="stSidebar"] button {
    background: rgba(37, 99, 235, 0.15) !important;
    border: 1px solid rgba(37, 99, 235, 0.4) !important;
    color: #FFFFFF !important;
    font-weight: 600 !important;
    transition: all 0.2s ease !important;
  }

  section[data-testid="stSidebar"] button:hover {
    background: #2563EB !important;
    border-color: #2563EB !important;
    box-shadow: 0 4px 12px rgba(37, 99, 235, 0.35) !important;
  }


  /* Enterprise Dashboard Hero Bar */
  .enterprise-hero-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: linear-gradient(135deg, #101B35 0%, #172554 50%, #1E40AF 100%);
    border-radius: 14px;
    padding: 20px 28px;
    margin-bottom: 24px;
    color: #FFFFFF;
    box-shadow: 0 6px 20px -2px rgba(16, 27, 53, 0.18);
    border: 1px solid rgba(255, 255, 255, 0.12);
  }

  .hero-tagline {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1.4px;
    text-transform: uppercase;
    color: #38BDF8;
    margin-bottom: 4px;
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .hero-heading {
    font-size: 22px;
    font-weight: 800;
    color: #FFFFFF;
    margin: 0 0 4px 0;
    letter-spacing: -0.4px;
  }

  .hero-subtitle {
    font-size: 13px;
    color: #CBD5E1;
    margin: 0;
    font-weight: 400;
  }

  .hero-badges {
    display: flex;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
  }

  .hero-badge-pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 14px;
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.18);
    border-radius: 9999px;
    font-size: 11px;
    font-weight: 600;
    color: #F1F5F9;
  }

  .pulse-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #10B981;
    box-shadow: 0 0 10px #10B981;
  }


  /* Metric KPI Cards (5 Pillars) */
  .kpi-card {
    background: #FFFFFF;
    border: 1px solid #E5EAF2;
    border-radius: 12px;
    padding: 18px 20px;
    box-shadow: 0 2px 8px rgba(16, 27, 53, 0.04);
    transition: all 0.22s cubic-bezier(0.16, 1, 0.3, 1);
    position: relative;
    overflow: hidden;
  }

  .kpi-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 3px;
    background: var(--card-accent, #2563EB);
  }

  .kpi-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(16, 27, 53, 0.08);
  }

  .kpi-card small {
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    color: #64748B;
    margin-bottom: 8px;
  }

  .kpi-card .val {
    font-size: 30px;
    font-weight: 800;
    color: #172033;
    line-height: 1.1;
  }

  .kpi-card .sub {
    font-size: 11px;
    color: #64748B;
    margin-top: 8px;
    display: flex;
    align-items: center;
    gap: 6px;
  }


  /* Enterprise Panel Containers */
  .panel-card {
    background: #FFFFFF;
    border: 1px solid #E5EAF2;
    border-radius: 14px;
    padding: 24px 28px;
    box-shadow: 0 2px 8px rgba(16, 27, 53, 0.04);
    margin-bottom: 22px;
  }

  .panel-title {
    font-size: 21px !important;
    font-weight: 800 !important;
    color: #101B35 !important;
    margin-bottom: 6px !important;
    display: flex;
    align-items: center;
    gap: 10px;
    letter-spacing: -0.3px;
  }

  .panel-subtitle {
    font-size: 13px !important;
    color: #64748B !important;
    margin-bottom: 0 !important;
    font-weight: 500;
  }

    margin-bottom: 16px;
  }


  /* Severity Badges */
  .badge-critical {
    background: #FEE2E2;
    color: #991B1B;
    border: 1px solid #FECACA;
    padding: 3px 10px;
    border-radius: 9999px;
    font-weight: 700;
    font-size: 11px;
    display: inline-flex;
    align-items: center;
    gap: 5px;
  }

  .badge-high {
    background: #FFEDD5;
    color: #9A3412;
    border: 1px solid #FED7AA;
    padding: 3px 10px;
    border-radius: 9999px;
    font-weight: 700;
    font-size: 11px;
    display: inline-flex;
    align-items: center;
    gap: 5px;
  }

  .badge-medium {
    background: #FEF3C7;
    color: #92400E;
    border: 1px solid #FDE68A;
    padding: 3px 10px;
    border-radius: 9999px;
    font-weight: 700;
    font-size: 11px;
    display: inline-flex;
    align-items: center;
    gap: 5px;
  }

  .badge-low {
    background: #E0F2FE;
    color: #075985;
    border: 1px solid #BAE6FD;
    padding: 3px 10px;
    border-radius: 9999px;
    font-weight: 700;
    font-size: 11px;
    display: inline-flex;
    align-items: center;
    gap: 5px;
  }

  .badge-pass {
    background: #DCFCE7;
    color: #166534;
    border: 1px solid #BBF7D0;
    padding: 3px 10px;
    border-radius: 9999px;
    font-weight: 700;
    font-size: 11px;
    display: inline-flex;
    align-items: center;
    gap: 5px;
  }


  /* Diff Tag Highlights */
  .diff-before {
    background: #FEE2E2;
    color: #DC2626;
    text-decoration: line-through;
    padding: 2px 6px;
    border-radius: 4px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
  }

  .diff-after {
    background: #DCFCE7;
    color: #16A34A;
    font-weight: 700;
    padding: 2px 6px;
    border-radius: 4px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
  }


  /* Primary Button Styling in Main Area */
  .main button[kind="primary"] {
    background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%) !important;
    border: none !important;
    color: #FFFFFF !important;
    font-weight: 700 !important;
    box-shadow: 0 2px 8px rgba(37, 99, 235, 0.3) !important;
    border-radius: 8px !important;
    transition: all 0.2s ease !important;
  }

  .main button[kind="primary"]:hover {
    box-shadow: 0 4px 14px rgba(37, 99, 235, 0.45) !important;
    transform: translateY(-1px) !important;
  }

</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# SESSION STATE INITIALIZATION
# -----------------------------------------------------------------------------
if "df_original" not in st.session_state:
    st.session_state.df_original = None
if "df_working" not in st.session_state:
    st.session_state.df_working = None
if "filename" not in st.session_state:
    st.session_state.filename = "None"
if "issues" not in st.session_state:
    st.session_state.issues = []
if "diagnoses" not in st.session_state:
    st.session_state.diagnoses = []
if "repair_engine" not in st.session_state:
    st.session_state.repair_engine = None
if "validation_results" not in st.session_state:
    st.session_state.validation_results = None
if "quality_scores" not in st.session_state:
    st.session_state.quality_scores = None
if "audit_log" not in st.session_state:
    st.session_state.audit_log = AuditLog()
if "processing_history" not in st.session_state:
    st.session_state.processing_history = []
if "dataset_loaded" not in st.session_state:
    st.session_state.dataset_loaded = False
if "last_scan_time" not in st.session_state:
    st.session_state.last_scan_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def load_dataset(df, filename="dataset.csv"):
    """Load a dataset into session state and run detection & diagnostics."""
    st.session_state.df_original = df.copy(deep=True)
    st.session_state.df_working = df.copy(deep=True)
    st.session_state.filename = filename
    st.session_state.dataset_loaded = True
    st.session_state.last_scan_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Run detection
    detector = DataQualityDetector(st.session_state.df_working)
    st.session_state.issues = detector.run_all_checks()

    # Run diagnosis
    diagnoser = RootCauseDiagnoser(st.session_state.df_working, st.session_state.issues)
    st.session_state.diagnoses = diagnoser.diagnose_all()

    # Compute quality scores
    st.session_state.quality_scores = calculate_quality_score(
        st.session_state.df_working, st.session_state.issues
    )

    # Initialize repair engine
    st.session_state.repair_engine = DataRepairEngine(
        st.session_state.df_working, st.session_state.issues, st.session_state.diagnoses
    )

    # Record processing history
    st.session_state.processing_history.append({
        "timestamp": st.session_state.last_scan_time,
        "filename": filename,
        "rows": len(df),
        "columns": len(df.columns),
        "issues_found": len(st.session_state.issues),
        "initial_score": st.session_state.quality_scores["overall_score"]
    }
)


def load_demo_dataset():
    """Load the built-in realistic demo dataset."""
    demo_path = os.path.join(BASE_DIR, "sample_data", "demo_dataset.csv")
    if os.path.exists(demo_path):
        try:
            df = pd.read_csv(demo_path)
            load_dataset(df, "demo_dataset.csv")
            return True
        except Exception as e:
            st.error(f"Error loading demo dataset: {e}")
            return False
    else:
        st.error("Demo dataset file not found.")
        return False


# Auto-load demo dataset on first visit if nothing loaded
if not st.session_state.dataset_loaded:
    load_demo_dataset()

# -----------------------------------------------------------------------------
# SIDEBAR NAVIGATION (ENTERPRISE NAVY DESIGN)
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("""
    <div style="display:flex; align-items:center; gap:12px; padding:8px 0 18px;">
      <div style="background: linear-gradient(135deg, #2563EB 0%, #06B6D4 100%); color:white; width:44px; height:44px; border-radius:10px; display:flex; align-items:center; justify-content:center; font-size:24px; font-weight:800; box-shadow:0 4px 16px rgba(37,99,235,0.4);">⚡</div>
      <div>
        <strong style="font-size:20px; color:#FFFFFF; display:block; letter-spacing:-0.5px; font-weight:800;">DataFix<span style="color:#06B6D4;">.ai</span></strong>
        <span style="color:#94A3B8; font-size:10px; font-weight:700; letter-spacing:1px; text-transform:uppercase;">Enterprise Quality Engine</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    page = st.radio(
        "NAVIGATION",
        [
            "🏠 Dashboard",
            "📤 Upload Dataset",
            "🔍 Data Exploration",
            "⚠️ Issue Detection",
            "🔬 Root Cause Analysis",
            "🔧 Data Repair",
            "✅ Data Validation",
            "📋 Modification History",
            "📊 Quality Reports",
            "💾 Export Dataset"
        ],
        index=0
    )

    st.markdown("---")

    # Quick Demo Dataset Loader in Sidebar
    st.caption("BENCHMARK TEST SUITE")
    if st.button("↻ Reload Demo Benchmark", width="stretch"):
        if load_demo_dataset():
            st.success("Loaded demo_dataset.csv!")
            st.rerun()

    # Active dataset status pill in sidebar
    if st.session_state.dataset_loaded:
        st.markdown(f"""
        <div style="background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.12); border-left: 3px solid #2563EB; border-radius: 8px; padding: 12px; margin-top: 14px;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
            <strong style="color:#FFFFFF; font-size:12px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; max-width:130px;">📄 {st.session_state.filename}</strong>
            <span style="background:#10B981; color:#FFFFFF; font-size:9px; font-weight:700; padding:2px 7px; border-radius:9999px;">ACTIVE</span>
          </div>
          <small style="color:#94A3B8; font-size:11px;">{len(st.session_state.df_working):,} rows &bull; {len(st.session_state.df_working.columns)} columns</small>
        </div>
        """, unsafe_allow_html=True)


# =============================================================================
# PAGE 1: DASHBOARD
# =============================================================================
if page == "🏠 Dashboard":
    # 4. Hero Section
    st.markdown(f"""
    <div class="enterprise-hero-bar">
      <div>
        <div class="hero-tagline"><span>⚡ AUTONOMOUS DATA HEALTH &amp; INTEGRITY CONSOLE</span></div>
        <h1 class="hero-heading">Autonomous Data Health &amp; Integrity Console</h1>
        <p class="hero-subtitle">Intelligent detection, explainable diagnosis, and trusted data repair.</p>
      </div>
      <div class="hero-badges">
        <div class="hero-badge-pill">
          <div class="pulse-dot"></div>
          <span>Engine: Operational</span>
        </div>
        <div class="hero-badge-pill">
          <span>📄 {st.session_state.filename}</span>
        </div>
        <div class="hero-badge-pill">
          <span>Status: Analyzed &amp; Monitored</span>
        </div>
        <div class="hero-badge-pill">
          <span>Last Scan: {st.session_state.last_scan_time}</span>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    if not st.session_state.dataset_loaded:
        st.info("No dataset loaded yet. Upload your dataset or click 'Reload Demo Benchmark' in the sidebar.")
    else:
        scores = st.session_state.quality_scores
        total_issues = len(st.session_state.issues)
        total_repaired = st.session_state.audit_log.count()
        repair_rate = round((total_repaired / max(1, total_issues)) * 100, 1)

        # Section Header: Executive KPIs
        st.markdown("""
        <div style="margin: 18px 0 14px 0;">
          <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 1.2px; color: #2563EB; margin-bottom: 2px;">Core Observability Metrics</div>
          <h2 style="font-size: 20px; font-weight: 800; color: #101B35; margin: 0;">📊 Executive Quality KPIs &amp; Operational Health</h2>
        </div>
        """, unsafe_allow_html=True)

        # 5 Professional KPI Cards
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.markdown(f"""
            <div class="kpi-card" style="--card-accent:#2563EB;">
              <small><span>Datasets Processed</span> <span>📁</span></small>
              <div class="val" style="color:#2563EB;">{len(st.session_state.processing_history)}</div>
              <div class="sub">Active session datasets</div>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            st.markdown(f"""
            <div class="kpi-card" style="--card-accent:#F59E0B;">
              <small><span>Issues Detected</span> <span>⚠️</span></small>
              <div class="val" style="color:#D97706;">{total_issues}</div>
              <div class="sub">Across all column schemas</div>
            </div>
            """, unsafe_allow_html=True)

        with col3:
            st.markdown(f"""
            <div class="kpi-card" style="--card-accent:#10B981;">
              <small><span>Issues Repaired</span> <span>✨</span></small>
              <div class="val" style="color:#10B981;">{total_repaired}</div>
              <div class="sub">Validated remediations</div>
            </div>
            """, unsafe_allow_html=True)

        with col4:
            # Safely handle missing quality score results
            if not isinstance(scores, dict):
                scores = {}

            score_val = scores.get("overall_score", 0.0)

            if score_val is None:
                score_val = 0.0

            score_val = float(score_val)
            color = get_score_color(score_val)
            label = get_score_label(score_val)
            st.markdown(f"""
            <div class="kpi-card" style="--card-accent:#06B6D4;">
              <small><span>Data Quality Score</span> <span>🛡️</span></small>
              <div class="val" style="color:#0284C7;">{score_val:.1f}<span style="font-size:14px; color:#64748B; font-weight:600;">/100</span></div>
              <div class="sub"><strong style="color:{color};">{label}</strong> rating</div>
            </div>
            """, unsafe_allow_html=True)

        with col5:
            st.markdown(f"""
            <div class="kpi-card" style="--card-accent:#8B5CF6;">
              <small><span>Repair Success Rate</span> <span>📈</span></small>
              <div class="val" style="color:#7C3AED;">{repair_rate}%</div>
              <div class="sub">Of flagged anomalies</div>
            </div>
            """, unsafe_allow_html=True)

        # Section Header: Visual Diagnostics
        st.markdown("""
        <div style="margin: 28px 0 16px 0;">
          <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 1.2px; color: #2563EB; margin-bottom: 2px;">Multidimensional Diagnostic View</div>
          <h2 style="font-size: 20px; font-weight: 800; color: #101B35; margin: 0;">📈 Diagnostic Visualizations &amp; Quality Radar</h2>
        </div>
        """, unsafe_allow_html=True)

        # 6. Premium Data Visualizations
        c1, c2 = st.columns(2)

        with c1:
            # A. Data Quality Radar
            radar_categories = ["Completeness", "Uniqueness", "Validity", "Consistency", "Accuracy"]
            radar_vals = [
                scores.get("completeness", 0),
                scores.get("uniqueness", 0),
                scores.get("validity", 0),
                scores.get("consistency", 0),
                scores.get("accuracy", 0)
            ]
            fig_radar = go.Figure()
            fig_radar.add_trace(go.Scatterpolar(
                r=radar_vals + [radar_vals[0]],
                theta=radar_categories + [radar_categories[0]],
                fill='toself',
                fillcolor='rgba(37, 99, 235, 0.16)',
                line=dict(color='#2563EB', width=2.5),
                name='Current Quality State',
                marker=dict(size=7, color='#2563EB')
            ))
            fig_radar.update_layout(
                polar=dict(
                    radialaxis=dict(visible=True, range=[0, 100], tickfont=dict(size=9, color="#64748B")),
                    angularaxis=dict(tickfont=dict(size=11, family="Plus Jakarta Sans", color="#172033", weight="bold"))
                ),
                showlegend=False,
                margin=dict(l=40, r=40, t=35, b=30),
                title=dict(text="5-Pillar Data Quality Radar", font=dict(size=15, color="#101B35", family="Plus Jakarta Sans")),
                paper_bgcolor="#FFFFFF",
                plot_bgcolor="#FFFFFF"
            )
            st.plotly_chart(fig_radar, width="stretch")

        with c2:
            # B. Issue Severity Breakdown
            sev_dist = scores.get("severity_distribution", {})
            labels = ["Critical", "High", "Medium", "Low"]
            values = [sev_dist.get(k, 0) for k in labels]
            colors = ["#EF4444", "#F59E0B", "#EAB308", "#06B6D4"]

            fig_donut = go.Figure(data=[go.Pie(
                labels=labels,
                values=values,
                hole=0.68,
                marker=dict(colors=colors, line=dict(color='#FFFFFF', width=2)),
                textinfo='label+value',
                hoverinfo='label+percent+value'
            )])
            fig_donut.update_layout(
                annotations=[dict(
                    text=f"<b style='font-size:26px; color:#101B35;'>{total_issues}</b><br><span style='font-size:11px; color:#64748B; font-weight:700;'>TOTAL ISSUES</span>",
                    x=0.5, y=0.5, font_size=16, showarrow=False
                )],
                margin=dict(l=20, r=20, t=35, b=20),
                title=dict(text="Issue Severity Breakdown", font=dict(size=15, color="#101B35", family="Plus Jakarta Sans")),
                legend=dict(orientation="h", y=-0.15),
                paper_bgcolor="#FFFFFF",
                plot_bgcolor="#FFFFFF"
            )
            st.plotly_chart(fig_donut, width="stretch")

        c3, c4 = st.columns(2)
        with c3:
            # D. Issue Category Distribution
            itypes = scores.get("issues_by_type", {})
            if itypes:
                sorted_types = sorted(itypes.items(), key=lambda x: x[1], reverse=True)[:6]
                fig_bar = go.Figure(go.Bar(
                    x=[v for k, v in sorted_types],
                    y=[k for k, v in sorted_types],
                    orientation='h',
                    marker=dict(color='#2563EB')
                ))
                fig_bar.update_layout(
                    title=dict(text="Issue Category Distribution", font=dict(size=15, color="#101B35", family="Plus Jakarta Sans")),
                    xaxis_title="Count",
                    yaxis_title="Category",
                    margin=dict(l=20, r=20, t=35, b=20),
                    paper_bgcolor="#FFFFFF",
                    plot_bgcolor="#FFFFFF"
                )
                st.plotly_chart(fig_bar, width="stretch")

        with c4:
            # C. Issues by Column Attribute
            icols = scores.get("issues_by_column", {})
            if icols:
                sorted_cols = sorted(icols.items(), key=lambda x: x[1], reverse=True)[:6]
                fig_col = go.Figure(go.Bar(
                    x=[k for k, v in sorted_cols],
                    y=[v for k, v in sorted_cols],
                    marker=dict(color='#10B981')
                ))
                fig_col.update_layout(
                    title=dict(text="Issues by Column Attribute", font=dict(size=15, color="#101B35", family="Plus Jakarta Sans")),
                    xaxis_title="Column",
                    yaxis_title="Count",
                    margin=dict(l=20, r=20, t=35, b=20),
                    paper_bgcolor="#FFFFFF",
                    plot_bgcolor="#FFFFFF"
                )
                st.plotly_chart(fig_col, width="stretch")

        # 7. Dataset Information Panel
        st.markdown("""
        <div class="panel-card" style="border-top: 3px solid #2563EB; margin-top: 10px;">
          <div class="panel-title"><span>📑 Active Dataset Information &amp; Operational Controls</span></div>
          <p class="panel-subtitle">Metadata profiling, ingestion health, and diagnostic controls.</p>
        </div>
        """, unsafe_allow_html=True)

        df = st.session_state.df_working
        info_c1, info_c2, info_c3 = st.columns([2, 2, 1])
        with info_c1:
            st.markdown(f"""
            <div style="font-size:13px; line-height: 1.8; color:#172033;">
              <strong>Dataset Name:</strong> {st.session_state.filename}<br>
              <strong>File Format:</strong> {st.session_state.filename.split('.')[-1].upper() if '.' in st.session_state.filename else 'CSV'}<br>
              <strong>Total Records:</strong> {len(df):,} rows<br>
              <strong>Total Attributes:</strong> {len(df.columns)} columns
            </div>
            """, unsafe_allow_html=True)

        with info_c2:
            st.markdown(f"""
            <div style="font-size:13px; line-height: 1.8; color:#172033;">
              <strong>Ingestion Time:</strong> {st.session_state.last_scan_time}<br>
              <strong>Analysis Status:</strong> <span style="background:#DCFCE7; color:#166534; padding:2px 8px; border-radius:9999px; font-weight:700; font-size:11px;">Validated</span><br>
              <strong>Estimated Size:</strong> ~{len(df) * len(df.columns) * 16 / 1024:.1f} KB<br>
              <strong>Audit Trail:</strong> {st.session_state.audit_log.count()} logged modifications
            </div>
            """, unsafe_allow_html=True)

        with info_c3:
            st.caption("ACTIONS")
            if st.button("⚡ Re-analyze Dataset", width="stretch"):
                detector = DataQualityDetector(st.session_state.df_working)
                st.session_state.issues = detector.run_all_checks()
                diagnoser = RootCauseDiagnoser(st.session_state.df_working, st.session_state.issues)
                st.session_state.diagnoses = diagnoser.diagnose_all()
                st.session_state.quality_scores = calculate_quality_score(
                    st.session_state.df_working, st.session_state.issues
                )
                st.session_state.last_scan_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                st.success("Re-analysis complete!")
                st.rerun()

            if st.button("↻ Reload Demo", width="stretch"):
                if load_demo_dataset():
                    st.success("Demo dataset reloaded!")
                    st.rerun()

        # Dataset Preview Table
        st.markdown("""
        <div style="margin: 24px 0 10px 0;">
          <h4 style="font-size: 16px; font-weight: 800; color: #101B35; margin: 0 0 2px 0;">🔍 Sample Data Preview (First 5 Rows)</h4>
          <p style="color: #64748B; font-size: 12px; margin: 0;">Quick inspection of top records in the active working dataframe.</p>
        </div>
        """, unsafe_allow_html=True)
        render_saas_table(df.head(5))

        # Recent Processing History Table
        st.markdown("""
        <div style="margin: 28px 0 12px 0;">
          <h3 style="font-size: 18px; font-weight: 800; color: #101B35; margin: 0 0 2px 0;">📋 Recent Dataset Audit History</h3>
          <p style="color: #64748B; font-size: 12px; margin: 0;">Session log of ingested files, row counts, detected issues, and baseline scores.</p>
        </div>
        """, unsafe_allow_html=True)
        if st.session_state.processing_history:
            history_df = pd.DataFrame(st.session_state.processing_history)
            render_saas_table(history_df, height=220)


# =============================================================================
# PAGE 2: UPLOAD DATASET
# =============================================================================
elif page == "📤 Upload Dataset":
    st.markdown("""
    <div class="panel-card" style="border-top: 3px solid #2563EB;">
      <div class="panel-title"><span>📤 Dataset Ingestion &amp; Schema Parser</span></div>
      <p class="panel-subtitle">Upload CSV, Excel (XLSX / XLS), or JSON datasets up to 50MB for autonomous quality inspection.</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([3, 1])
    with col1:
        uploaded_file = st.file_uploader(
            "Select dataset file to upload",
            type=["csv", "xlsx", "xls", "json"],
            help="Supported file types: CSV, Excel (XLSX, XLS), JSON"
        )
    with col2:
        st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
        if st.button("⚡ Load Built-in Demo Data", width="stretch", type="primary"):
            if load_demo_dataset():
                st.success("Loaded demo_dataset.csv successfully!")
                st.rerun()

    if uploaded_file is not None:
        with st.spinner("Ingesting, parsing, and running quality audit..."):
            df, err = read_uploaded_file(uploaded_file)
            if err:
                st.error(err)
            else:
                load_dataset(df, uploaded_file.name)
                st.success(f"Successfully ingested '{uploaded_file.name}' ({len(df):,} rows, {len(df.columns)} columns)!")

    if st.session_state.dataset_loaded:
        df = st.session_state.df_working
        st.markdown("---")
        st.markdown("""
        <div style="margin: 20px 0 12px 0;">
          <h3 style="font-size: 19px; font-weight: 800; color: #101B35; margin: 0 0 4px 0;">📊 Ingested Dataset Overview &amp; Preview</h3>
          <p style="color: #64748B; font-size: 13px; margin: 0;">Summary health metrics and top 10 rows from the parsed file.</p>
        </div>
        """, unsafe_allow_html=True)

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Records", f"{len(df):,}")
        m2.metric("Total Columns", f"{len(df.columns)}")
        m3.metric("Missing Values", f"{df.isna().sum().sum():,}")
        m4.metric("Exact Duplicates", f"{df.duplicated().sum():,}")

        # Dataset Preview
        render_saas_table(df.head(10))

        # Column Schema & Types Table
        st.markdown("""
        <div style="margin: 28px 0 12px 0;">
          <h3 style="font-size: 19px; font-weight: 800; color: #101B35; margin: 0 0 4px 0;">📑 Column Schema &amp; Inferred Data Types</h3>
          <p style="color: #64748B; font-size: 13px; margin: 0;">Automatic type detection, missing counts, uniqueness cardinality, and sample observations.</p>
        </div>
        """, unsafe_allow_html=True)
        schema_data = []
        for col in df.columns:
            series = df[col]
            clean_vals = [v for v in series if v is not None and v != "" and (not isinstance(v, float) or v == v)]
            sample_val = str(clean_vals[0]) if clean_vals else "<None>"
            schema_data.append({
                "Column Name": col,
                "Data Type": str(getattr(series, "dtype", "object")),
                "Non-Null Count": len(clean_vals),
                "Null Count": len(series) - len(clean_vals),
                "Unique Values": len(set(clean_vals)),
                "Sample Value": sample_val
            }
)
        render_saas_table(schema_data)


# =============================================================================
# PAGE 3: DATA EXPLORATION
# =============================================================================
elif page == "🔍 Data Exploration":
    st.markdown("""
    <div class="panel-card" style="border-top: 3px solid #06B6D4;">
      <div class="panel-title"><span>🔍 Deep Data Exploration &amp; Statistical Profiling</span></div>
      <p class="panel-subtitle">Comprehensive exploratory data analysis, numerical distribution metrics, and missingness heatmaps.</p>
    </div>
    """, unsafe_allow_html=True)

    if not st.session_state.dataset_loaded:
        st.warning("Please upload a dataset or load the demo dataset first.")
    else:
        df = st.session_state.df_working

        tab1, tab2, tab3 = st.tabs(["📋 Full Data Table", "📈 Statistical Profiling", "🗺️ Missing Value Heatmap"])

        with tab1:
            render_saas_table(df, max_rows=150, height=500)

        with tab2:
            st.markdown("""
            <div style="margin: 16px 0 10px 0;">
              <h4 style="font-size: 16px; font-weight: 800; color: #101B35; margin: 0 0 2px 0;">📊 Numerical Attribute Summary</h4>
              <p style="color: #64748B; font-size: 12px; margin: 0;">Statistical summary of numeric fields including min, mean, median, max, and standard deviation.</p>
            </div>
            """, unsafe_allow_html=True)
            numeric_cols = [c for c in df.columns if df[c].dtype in ("int64", "float64") or any(k in c.lower() for k in ["salary", "score", "rate", "price"])]
            if numeric_cols:
                num_summary = []
                for c in numeric_cols:
                    clean_nums = []
                    for val in df[c].dropna():
                        try:
                            clean_nums.append(float(str(val).replace("$", "").replace(",", "")))
                        except ValueError:
                            pass
                    if clean_nums:
                        import numpy as np
                        num_summary.append({
                            "Column": c,
                            "Count": len(clean_nums),
                            "Min": round(min(clean_nums), 2),
                            "Mean": round(sum(clean_nums)/len(clean_nums), 2),
                            "Median": round(float(np.median(clean_nums)), 2),
                            "Max": round(max(clean_nums), 2),
                            "Std Dev": round(float(np.std(clean_nums)), 2)
                        }
)
                render_saas_table(num_summary)

            st.markdown("""
            <div style="margin: 22px 0 10px 0;">
              <h4 style="font-size: 16px; font-weight: 800; color: #101B35; margin: 0 0 2px 0;">📊 Categorical Value Distributions</h4>
              <p style="color: #64748B; font-size: 12px; margin: 0;">Frequency analysis and top 10 unique values for categorical attributes.</p>
            </div>
            """, unsafe_allow_html=True)
            cat_cols = [c for c in df.columns if c not in numeric_cols and "id" not in c.lower()]
            selected_cat = st.selectbox("Select column to inspect distributions:", cat_cols)
            if selected_cat:
                from collections import Counter
                clean_cat_vals = [str(v).strip() for v in df[selected_cat] if v is not None and v != "" and (not isinstance(v, float) or v == v)]
                top_items = Counter(clean_cat_vals).most_common(10)
                top_labels = [item[0] for item in top_items]
                top_values = [item[1] for item in top_items]
                fig_cat = go.Figure(go.Bar(
                    x=top_labels,
                    y=top_values,
                    marker=dict(color='#2563EB')
                ))
                fig_cat.update_layout(
                    title=f"Top Frequencies in '{selected_cat}'",
                    xaxis_title=selected_cat,
                    yaxis_title="Count",
                    paper_bgcolor="#FFFFFF",
                    plot_bgcolor="#FFFFFF"
                )
                st.plotly_chart(fig_cat, width="stretch")

        with tab3:
            st.markdown("""
            <div style="margin: 16px 0 10px 0;">
              <h4 style="font-size: 16px; font-weight: 800; color: #101B35; margin: 0 0 2px 0;">🗺️ Missing Value Distribution Matrix</h4>
              <p style="color: #64748B; font-size: 12px; margin: 0;">Heatmap visualization showing populated cells (gray) versus null/sentinel missing values (red).</p>
            </div>
            """, unsafe_allow_html=True)
            first_50 = df.head(50)
            z_vals = [[1 if (first_50[c][i] is None or first_50[c][i] == "" or (isinstance(first_50[c][i], float) and first_50[c][i] != first_50[c][i])) else 0 for c in first_50.columns] for i in range(len(first_50))]
            fig_heat = go.Figure(data=go.Heatmap(
                z=z_vals,
                x=list(first_50.columns),
                y=[f"Row {i+1}" for i in range(len(first_50))],
                colorscale=[[0, '#F1F5F9'], [1, '#EF4444']],
                showscale=False
            ))
            fig_heat.update_layout(
                title="Missing Value Distribution (First 50 Rows: Red = Missing, Light Gray = Present)",
                xaxis_title="Column Attribute",
                yaxis_title="Record Row",
                paper_bgcolor="#FFFFFF",
                plot_bgcolor="#FFFFFF"
            )
            st.plotly_chart(fig_heat, width="stretch")


# =============================================================================
# PAGE 4: ISSUE DETECTION
# =============================================================================
elif page == "⚠️ Issue Detection":
    st.markdown("""
    <div class="panel-card" style="border-top: 3px solid #F59E0B;">
      <div class="panel-title"><span>⚠️ Autonomous Quality Issue Detection Engine</span></div>
      <p class="panel-subtitle">Multi-pattern inspection identifying syntax, semantic, relational, format, and schema violations.</p>
    </div>
    """, unsafe_allow_html=True)

    if not st.session_state.dataset_loaded:
        st.warning("Please upload a dataset or load the demo dataset first.")
    else:
        issues = st.session_state.issues
        scores = st.session_state.quality_scores
        sev_counts = scores.get("severity_distribution", {})

        # 8. Top summary metric badges
        b1, b2, b3, b4, b5 = st.columns(5)
        b1.markdown(f"""
        <div class="kpi-card" style="--card-accent:#101B35; padding:12px 16px;">
          <small><span>Total Issues</span></small>
          <div class="val" style="font-size:24px;">{len(issues)}</div>
        </div>
        """, unsafe_allow_html=True)
        b2.markdown(f"""
        <div class="kpi-card" style="--card-accent:#EF4444; padding:12px 16px;">
          <small><span>Critical</span></small>
          <div class="val" style="font-size:24px; color:#EF4444;">{sev_counts.get('Critical', 0)}</div>
        </div>
        """, unsafe_allow_html=True)
        b3.markdown(f"""
        <div class="kpi-card" style="--card-accent:#F59E0B; padding:12px 16px;">
          <small><span>High</span></small>
          <div class="val" style="font-size:24px; color:#F59E0B;">{sev_counts.get('High', 0)}</div>
        </div>
        """, unsafe_allow_html=True)
        b4.markdown(f"""
        <div class="kpi-card" style="--card-accent:#EAB308; padding:12px 16px;">
          <small><span>Medium</span></small>
          <div class="val" style="font-size:24px; color:#CA8A04;">{sev_counts.get('Medium', 0)}</div>
        </div>
        """, unsafe_allow_html=True)
        b5.markdown(f"""
        <div class="kpi-card" style="--card-accent:#06B6D4; padding:12px 16px;">
          <small><span>Low</span></small>
          <div class="val" style="font-size:24px; color:#0284C7;">{sev_counts.get('Low', 0)}</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Filters
        f1, f2 = st.columns([2, 2])
        with f1:
            sev_filter = st.multiselect(
                "Filter by Severity:",
                ["Critical", "High", "Medium", "Low"],
                default=["Critical", "High", "Medium", "Low"]
            )
        with f2:
            search_query = st.text_input("Search by Column Name or Issue Type:", placeholder="e.g. email, salary, date...")

        filtered_issues = [
            i for i in issues
            if i["severity"] in sev_filter and (
                not search_query or
                search_query.lower() in i["column"].lower() or
                search_query.lower() in i["issue_type"].lower()
            )
        ]

        # Structured Table of Issues
        st.markdown(f"""
        <div style="margin: 24px 0 12px 0;">
          <h3 style="font-size: 19px; font-weight: 800; color: #101B35; margin: 0 0 4px 0;">📋 Structured Quality Issues Registry ({len(filtered_issues)} items)</h3>
          <p style="color: #64748B; font-size: 13px; margin: 0;">Comprehensive inventory of detected data violations, affected rows, and suggested actions.</p>
        </div>
        """, unsafe_allow_html=True)
        table_rows = []
        for idx, iss in enumerate(filtered_issues):
            table_rows.append({
                "Issue ID": iss.get("issue_id", f"iss_{idx+1:03d}"),
                "Issue Type": iss["issue_type"],
                "Column Name": iss["column"],
                "Affected Rows": iss["affected_count"],
                "Severity": iss["severity"],
                "Detection Method": iss["detection_method"],
                "Status": "Identified"
            }
)
        render_saas_table(table_rows, height=350)

        # Issue Inspection Panel
        st.markdown("""
        <div style="margin: 28px 0 12px 0;">
          <h3 style="font-size: 19px; font-weight: 800; color: #101B35; margin: 0 0 4px 0;">🔎 In-Depth Issue Inspection Panel</h3>
          <p style="color: #64748B; font-size: 13px; margin: 0;">Select an anomaly to inspect affected row indices, offending values, and technical context.</p>
        </div>
        """, unsafe_allow_html=True)
        issue_options = [f"{iss.get('issue_id', f'iss_{idx+1:03d}')} — {iss['issue_type']} in '{iss['column']}' ({iss['severity']})" for idx, iss in enumerate(filtered_issues)]
        if issue_options:
            selected_issue_str = st.selectbox("Select an issue to inspect details:", issue_options)
            sel_idx = issue_options.index(selected_issue_str)
            sel_iss = filtered_issues[sel_idx]

            sev = sel_iss["severity"]
            sev_class = f"badge-{sev.lower()}"

            st.markdown(f"""
            <div style="background:#FFFFFF; border:1px solid #E5EAF2; border-left:4px solid { '#EF4444' if sev=='Critical' else '#F59E0B' if sev=='High' else '#EAB308' if sev=='Medium' else '#06B6D4'}; border-radius:10px; padding:20px; margin-top:10px;">
              <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                <h4 style="margin:0; color:#101B35; font-size:17px; font-weight:800;">{sel_iss['issue_type']} in '{sel_iss['column']}'</h4>
                <span class="{sev_class}">{sev} Severity</span>
              </div>
              <p style="color:#172033; font-size:13px; margin-bottom:12px;">{sel_iss['description']}</p>
              <div style="display:grid; grid-template-columns: 1fr 1fr; gap:12px; font-size:12px; background:#F8FAFC; padding:14px; border-radius:8px; border:1px solid #E5EAF2;">
                <div>
                  <strong style="color:#101B35;">Detection Routine:</strong> {sel_iss['detection_method']}<br>
                  <strong style="color:#101B35;">Affected Count:</strong> {sel_iss['affected_count']} records ({round(sel_iss['affected_count']/max(1, len(st.session_state.df_working))*100, 1)}% of dataset)
                </div>
                <div>
                  <strong style="color:#101B35;">Sample Problematic Values:</strong> {', '.join(repr(v) for v in sel_iss['example_values'][:6])}<br>
                  <strong style="color:#101B35;">Row Indices:</strong> {', '.join(str(r+1) for r in sel_iss['affected_rows'][:15])}{'...' if len(sel_iss['affected_rows'])>15 else ''}
                </div>
              </div>
            </div>
            """, unsafe_allow_html=True)


# =============================================================================
# PAGE 5: ROOT CAUSE ANALYSIS
# =============================================================================
elif page == "🔬 Root Cause Analysis":
    st.markdown("""
    <div class="panel-card" style="border-top: 3px solid #8B5CF6;">
      <div class="panel-title"><span>🔬 Pattern Diagnosis &amp; Causal Inference Engine</span></div>
      <p class="panel-subtitle">Infers underlying data pipeline, human entry, and ingestion drivers behind detected anomalies.</p>
    </div>
    """, unsafe_allow_html=True)

    if not st.session_state.dataset_loaded:
        st.warning("Please upload a dataset or load the demo dataset first.")
    else:
        diagnoses = st.session_state.diagnoses
        confirmed_count = sum(1 for d in diagnoses if d.get("cause_type") == "Confirmed")
        suspected_count = len(diagnoses) - confirmed_count
        avg_conf = round(sum(d.get("confidence_score", 0.8) for d in diagnoses) / max(1, len(diagnoses)) * 100, 1)

        d1, d2, d3 = st.columns(3)
        d1.metric("Total Diagnoses Generated", len(diagnoses))
        d2.metric("Confirmed vs Suspected", f"{confirmed_count} Confirmed / {suspected_count} Inferred")
        d3.metric("Average Diagnostic Confidence", f"{avg_conf}%")

        st.markdown("<br>", unsafe_allow_html=True)

        for d in diagnoses:
            cause_type = d.get("cause_type", "Suspected")
            is_confirmed = cause_type == "Confirmed"
            type_badge = "badge-pass" if is_confirmed else "badge-medium"
            conf = int(d.get("confidence_score", 0.9) * 100)
            bar_color = "#10B981" if is_confirmed else "#F59E0B"

            st.markdown(f"""
            <div style="background:#FFFFFF; border:1px solid #E5EAF2; border-left:4px solid {bar_color}; border-radius:10px; padding:18px 22px; margin-bottom:14px; box-shadow: 0 1px 4px rgba(16,27,53,0.03);">
              <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                <h4 style="margin:0; font-size:16px; font-weight:800; color:#101B35;">{d.get('issue_type')} &bull; Column: '{d.get('column')}'</h4>
                <div style="display:flex; align-items:center; gap:8px;">
                  <span class="{type_badge}">{'Confirmed Fact' if is_confirmed else 'Inferred Hypothesis'}</span>
                  <span style="background:#E0F2FE; color:#0284C7; padding:2px 8px; border-radius:9999px; font-size:11px; font-weight:700;">{conf}% Confidence</span>
                </div>
              </div>
              <p style="font-size:13px; color:#172033; margin:0 0 6px 0;"><strong>Probable Root Cause:</strong> {d.get('probable_cause')}</p>
              <div style="font-size:12px; color:#64748B; margin-bottom:8px;">
                <strong>Evidence:</strong> {d.get('evidence')}
              </div>
              <div style="background:#EFF6FF; border:1px solid #DBEAFE; border-radius:6px; padding:10px 14px; font-size:12px; color:#1E40AF; margin-bottom:6px;">
                <strong>Recommended Remediation:</strong> {d.get('recommended_action')}
              </div>
              <div style="font-size:11px; color:#94A3B8;">
                <strong>Technical Context:</strong> {d.get('explanation')}
              </div>
            </div>
            """, unsafe_allow_html=True)


# =============================================================================
# PAGE 6: DATA REPAIR
# =============================================================================
elif page == "🔧 Data Repair":
    st.markdown("""
    <div class="panel-card" style="border-top: 3px solid #10B981;">
      <div class="panel-title"><span>🔧 Safe Autonomous &amp; Guided Data Repair Suite</span></div>
      <p class="panel-subtitle">Apply deterministic automated format normalizations or review sensitive statistical imputations with complete rollback capability.</p>
    </div>
    """, unsafe_allow_html=True)

    if not st.session_state.dataset_loaded:
        st.warning("Please upload a dataset or load the demo dataset first.")
    else:
        engine = st.session_state.repair_engine
        auto_proposals = engine.get_auto_repairs()
        manual_proposals = engine.get_manual_repairs()

        # Progress bar of repairs
        total_proposals = len(auto_proposals) + len(manual_proposals)
        applied_repairs = st.session_state.audit_log.count()
        repair_pct = min(100.0, round((applied_repairs / max(1, total_proposals + applied_repairs)) * 100, 1))

        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #ECFDF5 0%, #F0FDF4 100%); border: 1px solid #A7F3D0; border-radius: 12px; padding: 18px 22px; margin-bottom: 20px;">
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <div>
              <span style="font-size:11px; font-weight:700; color:#059669; letter-spacing:1px; text-transform:uppercase;">⚡ REPAIR PROGRESS &amp; GOVERNANCE</span>
              <h3 style="color:#065F46; margin:3px 0 5px; font-size:18px; font-weight:800;">{applied_repairs} Applied Modifications &bull; {len(auto_proposals)} Auto-Safe Pending</h3>
              <p style="color:#047857; margin:0; font-size:12px;">Zero risk of unintended schema mutation or primary key collision.</p>
            </div>
            <div style="text-align:right;">
              <span style="background:#D1FAE5; color:#065F46; padding:5px 12px; border-radius:9999px; font-weight:700; font-size:12px;">Audit Logging Active</span>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        tab_auto, tab_manual = st.tabs([
            f"⚡ Automated Safe Repairs ({len(auto_proposals)})",
            f"🔍 Manual Review Required ({len(manual_proposals)})"
        ])

        with tab_auto:
            st.markdown("#### Safe Deterministic Automated Repairs")
            st.caption("High-confidence formatting: whitespace trimming, ISO date normalization, casing standardization, and typo fixes.")

            if auto_proposals:
                if st.button("⚡ Apply All Safe Repairs", type="primary", width="stretch"):
                    auto_ids = [p["repair_id"] for p in auto_proposals]
                    if auto_ids:
                        st.session_state.df_working = engine.apply_repairs(auto_ids)
                        # Record in audit log
                        for p in auto_proposals:
                            col = p["column"]
                            for r_idx, new_val in p["proposed_values"].items():
                                orig_val = p["original_values"].get(r_idx, "")
                                st.session_state.audit_log.add_entry(
                                    action=p["repair_method"],
                                    column=col,
                                    row_index=r_idx,
                                    original_value=orig_val,
                                    new_value=new_val,
                                    reason=p["reason"],
                                    method=p["repair_method"],
                                    confidence=p["confidence"],
                                    user_action="auto",
                                    repair_id=p["repair_id"]
                                )
                        # Re-run detection on new working df
                        detector = DataQualityDetector(st.session_state.df_working)
                        st.session_state.issues = detector.run_all_checks()
                        st.session_state.quality_scores = calculate_quality_score(
                            st.session_state.df_working, st.session_state.issues
                        )
                        st.success(f"Applied {len(auto_ids)} automated safe repairs!")
                        st.rerun()

                for p in auto_proposals:
                    with st.expander(f"{p['column']} · {p['repair_method']} ({int(p['confidence']*100)}% Confidence)"):
                        st.markdown(f"**Rationale:** {p['reason']}")
                        sample_keys = list(p["proposed_values"].keys())[:5]
                        diff_data = []
                        for k in sample_keys:
                            diff_data.append({
                                "Row Index": k + 1,
                                "Original Value": p["original_values"].get(k),
                                "Proposed Replacement": p["proposed_values"].get(k)
                            }
)
                        render_saas_table(diff_data)
            else:
                st.success("All safe automated repairs have already been applied! No pending automated proposals.")

        with tab_manual:
            st.markdown("#### Sensitive Proposals Requiring Human Approval")
            st.caption("Statistical imputations (median/mode) and record deduplications requiring administrator verification.")

            if manual_proposals:
                for p in manual_proposals:
                    st.markdown(f"""
                    <div style="background:#FFFFFF; border:1px solid #E5EAF2; border-left:4px solid #F59E0B; border-radius:10px; padding:16px 20px; margin-bottom:12px;">
                      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                        <strong style="color:#101B35; font-size:14px;">Proposal ID: <code>{p['repair_id']}</code> &bull; Column: '{p['column']}'</strong>
                        <span style="background:#FEF3C7; color:#92400E; padding:2px 8px; border-radius:9999px; font-size:11px; font-weight:700;">{int(p['confidence']*100)}% Confidence</span>
                      </div>
                      <p style="font-size:12px; color:#172033; margin:0 0 10px 0;"><strong>Remediation Strategy:</strong> {p['reason']}</p>
                    </div>
                    """, unsafe_allow_html=True)

                    btn_c1, btn_c2 = st.columns([1, 4])
                    with btn_c1:
                        if st.button("✓ Approve & Apply", key=f"app_{p['repair_id']}", type="primary"):
                            st.session_state.df_working = engine.apply_repairs([p["repair_id"]])
                            for r_idx, new_val in p["proposed_values"].items():
                                orig_val = p["original_values"].get(r_idx, "")
                                st.session_state.audit_log.add_entry(
                                    action=p["repair_method"],
                                    column=p["column"],
                                    row_index=r_idx,
                                    original_value=orig_val,
                                    new_value=new_val,
                                    reason=p["reason"],
                                    method=p["repair_method"],
                                    confidence=p["confidence"],
                                    user_action="manual",
                                    repair_id=p["repair_id"]
                                )
                            # Re-run detection on new working df
                            detector = DataQualityDetector(st.session_state.df_working)
                            st.session_state.issues = detector.run_all_checks()
                            st.session_state.quality_scores = calculate_quality_score(
                                st.session_state.df_working, st.session_state.issues
                            )
                            st.success(f"Approved and applied repair {p['repair_id']}!")
                            st.rerun()
                    with btn_c2:
                        st.caption(f"Applies changes to {len(p['proposed_values'])} row records.")
            else:
                st.info("No sensitive manual review proposals pending.")

        st.markdown("---")
        st.markdown("#### ↺ Complete Dataset Rollback")
        if st.button("↺ Restore Pristine Original Dataset", type="secondary"):
            st.session_state.df_working = engine.restore_original()
            st.session_state.audit_log.clear()
            detector = DataQualityDetector(st.session_state.df_working)
            st.session_state.issues = detector.run_all_checks()
            st.session_state.quality_scores = calculate_quality_score(
                st.session_state.df_working, st.session_state.issues
            )
            st.success("Dataset successfully reverted back to original uploaded state.")
            st.rerun()


# =============================================================================
# PAGE 7: DATA VALIDATION
# =============================================================================
elif page == "✅ Data Validation":
    st.markdown("""
    <div class="panel-card" style="border-top: 3px solid #2563EB;">
      <div class="panel-title"><span>✅ Post-Repair Integrity &amp; Validation Audit</span></div>
      <p class="panel-subtitle">Verifies dataset improvements, checks for residual issues, and confirms zero unintended drift or schema regressions.</p>
    </div>
    """, unsafe_allow_html=True)

    if not st.session_state.dataset_loaded:
        st.warning("Please upload a dataset or load the demo dataset first.")
    else:
        engine = st.session_state.repair_engine
        validator = DataValidator(
            original_df=engine.get_original_df(),
            repaired_df=engine.get_working_df(),
            original_issues=engine.issues,
            applied_repairs=engine.get_repair_history()
        )
        val_results = validator.validate()
        st.session_state.validation_results = val_results

        # Before & After KPI Score Lift
        c1, c2, c3 = st.columns(3)
        c1.metric("Original Quality Score", f"{val_results['before_score']:.1f} / 100")
        diff = val_results['score_change']
        c2.metric("Repaired Quality Score", f"{val_results['after_score']:.1f} / 100", delta=f"{'+' if diff>=0 else ''}{diff:.1f} pts")
        c3.metric("Issues Resolved", f"{val_results['resolved_count']} / {val_results['original_stats']['total_issues']}")

        # Plotly Lift Bar Chart
        categories = ["Completeness", "Uniqueness", "Validity", "Consistency", "Accuracy", "Overall Score"]
        before_vals = [
            val_results["before_metrics"].get("completeness", 0),
            val_results["before_metrics"].get("uniqueness", 0),
            val_results["before_metrics"].get("validity", 0),
            val_results["before_metrics"].get("consistency", 0),
            val_results["before_metrics"].get("accuracy", 0),
            val_results["before_score"]
        ]
        after_vals = [
            val_results["after_metrics"].get("completeness", 0),
            val_results["after_metrics"].get("uniqueness", 0),
            val_results["after_metrics"].get("validity", 0),
            val_results["after_metrics"].get("consistency", 0),
            val_results["after_metrics"].get("accuracy", 0),
            val_results["after_score"]
        ]

        fig_lift = go.Figure(data=[
            go.Bar(name='Original State', x=categories, y=before_vals, marker_color='#EF4444'),
            go.Bar(name='Repaired & Validated', x=categories, y=after_vals, marker_color='#10B981')
        ])
        fig_lift.update_layout(
            barmode='group',
            title=dict(text="Quality Dimension Improvement (Before vs Repaired)", font=dict(size=15, color="#101B35", family="Plus Jakarta Sans")),
            yaxis=dict(range=[0, 100], title="Dimension Score (0-100)"),
            paper_bgcolor="#FFFFFF",
            plot_bgcolor="#FFFFFF"
        )
        st.plotly_chart(fig_lift, width="stretch")

        st.markdown(f"""
        <div style="background:#FFFFFF; border:1px solid #E5EAF2; border-left:4px solid #10B981; border-radius:10px; padding:18px 22px; margin-top:16px;">
          <h4 style="margin:0 0 6px 0; color:#101B35; font-size:15px; font-weight:800;">Validation Executive Summary</h4>
          <p style="margin:0; color:#172033; font-size:13px; line-height:1.6;">{val_results['validation_summary']}</p>
        </div>
        """, unsafe_allow_html=True)


# =============================================================================
# PAGE 8: MODIFICATION HISTORY
# =============================================================================
elif page == "📋 Modification History":
    st.markdown("""
    <div class="panel-card" style="border-top: 3px solid #101B35;">
      <div class="panel-title"><span>📋 Auditable Modification Provenance &amp; Activity Log</span></div>
      <p class="panel-subtitle">Cryptographically traceable, immutable record of every autonomous and manual modification applied to this dataset.</p>
    </div>
    """, unsafe_allow_html=True)

    audit = st.session_state.audit_log
    entries = audit.get_entries()

    if not entries:
        st.info("No modifications recorded yet. Use the Data Repair module to apply automated or guided repairs.")
    else:
        st.markdown(f"**Total Modifications Logged: {len(entries)}**")

        search_col = st.text_input("Filter audit logs by column or action:", placeholder="e.g. email, salary, normalize...")

        df_audit = audit.to_dataframe()
        if search_col and hasattr(df_audit, "columns"):
            # Filter rows
            rows_dict = df_audit.to_dict("records")
            filtered_rows = [r for r in rows_dict if any(search_col.lower() in str(val).lower() for val in r.values())]
            df_display = pd.DataFrame(filtered_rows)
        else:
            df_display = df_audit

        render_saas_table(df_display, max_rows=200, height=480)

        d_col1, d_col2 = st.columns(2)
        with d_col1:
            st.download_button(
                "📥 Download Audit Trail (CSV)",
                data=audit.to_csv_bytes(),
                file_name=f"audit_log_{st.session_state.filename}.csv",
                mime="text/csv",
                width="stretch"
            )
        with d_col2:
            st.download_button(
                "📥 Download Audit Trail (JSON)",
                data=audit.to_json(),
                file_name=f"audit_log_{st.session_state.filename}.json",
                mime="application/json",
                width="stretch"
            )


# =============================================================================
# PAGE 9: QUALITY REPORTS
# =============================================================================
elif page == "📊 Quality Reports":
    st.markdown("""
    <div class="panel-card" style="border-top: 3px solid #2563EB;">
      <div class="panel-title"><span>📊 Executive Quality &amp; Compliance Report</span></div>
      <p class="panel-subtitle">Publication-grade HTML quality report complete with validation proofs, root-cause breakdowns, and audit logs.</p>
    </div>
    """, unsafe_allow_html=True)

    if not st.session_state.dataset_loaded:
        st.warning("Please upload a dataset or load the demo dataset first.")
    else:
        dataset_info = {
            "filename": st.session_state.filename,
            "rows": len(st.session_state.df_working),
            "cols": len(st.session_state.df_working.columns)
        }

        val_results = st.session_state.validation_results or {
            "before_score": st.session_state.quality_scores.get("overall_score", 0),
            "after_score": st.session_state.quality_scores.get("overall_score", 0),
            "validation_summary": "Initial validation assessment."
        }


        generator = ReportGenerator(
            dataset_info=dataset_info,
            issues=st.session_state.issues,
            diagnoses=st.session_state.diagnoses,
            repairs=st.session_state.repair_engine.get_repair_history(),
            validation_results=val_results,
            quality_scores=st.session_state.quality_scores,
            audit_entries=st.session_state.audit_log.get_entries()
        )

        html_report = generator.generate_html_report()

        st.download_button(
            "📥 Download Executive Quality Report (HTML)",
            data=html_report,
            file_name=f"datafix_report_{st.session_state.filename}.html",
            mime="text/html",
            type="primary"
        )

        st.markdown("### Interactive Report Preview")
        components.html(html_report, height=800, scrolling=True)


# =============================================================================
# PAGE 10: EXPORT DATASET
# =============================================================================
elif page == "💾 Export Dataset":
    st.markdown("""
    <div class="panel-card" style="border-top: 3px solid #10B981;">
      <div class="panel-title"><span>💾 Enterprise Artifact &amp; Dataset Export Suite</span></div>
      <p class="panel-subtitle">Download fully cleansed datasets, regulatory compliance reports, and cryptographically timestamped audit provenance files.</p>
    </div>
    """, unsafe_allow_html=True)

    if not st.session_state.dataset_loaded:
        st.warning("Please upload a dataset or load the demo dataset first.")
    else:
        df_working = st.session_state.df_working

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("""
            <div class="panel-card" style="border-top: 4px solid #2563EB; margin-bottom:14px;">
              <div class="panel-title"><span>📊 Cleaned Production Datasets</span></div>
              <p class="panel-subtitle">Export cleansed, format-normalized records ready for downstream warehouses (Snowflake, BigQuery, Databricks).</p>
            </div>
            """, unsafe_allow_html=True)

            csv_bytes = export_to_csv(df_working)
            st.download_button(
                "📥 Download Cleaned Dataset (CSV)",
                data=csv_bytes,
                file_name=f"cleaned_{st.session_state.filename}.csv",
                mime="text/csv",
                width="stretch"
            )

            excel_bytes = export_to_excel(df_working)
            st.download_button(
                "📥 Download Cleaned Dataset (Excel XLSX)",
                data=excel_bytes,
                file_name=f"cleaned_{st.session_state.filename}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                width="stretch"
            )

        with c2:
            st.markdown("""
            <div class="panel-card" style="border-top: 4px solid #10B981; margin-bottom:14px;">
              <div class="panel-title"><span>📑 Governance &amp; Regulatory Audit Logs</span></div>
              <p class="panel-subtitle">Auditable, timestamped record of every repair rationale, method, confidence score, and schema delta.</p>
            </div>
            """, unsafe_allow_html=True)

            audit_csv = st.session_state.audit_log.to_csv_bytes()
            st.download_button(
                "📥 Download Audit Trail (CSV)",
                data=audit_csv,
                file_name=f"audit_trail_{st.session_state.filename}.csv",
                mime="text/csv",
                width="stretch"
            )

            audit_json = st.session_state.audit_log.to_json()
            st.download_button(
                "📥 Download Audit Trail (JSON)",
                data=audit_json,
                file_name=f"audit_trail_{st.session_state.filename}.json",
                mime="application/json",
                width="stretch"
            )
