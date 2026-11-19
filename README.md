# ⚡ DataFix – Autonomous Data Quality and Repair Engine
**INNOVEDGE Hackathon 2026 | Official Problem Statement 01**  
*Domain: Data Science & Data Engineering · Automated Data Quality & Repair*

---

## 1. Project Overview

**DataFix** is an enterprise-grade, automated data-quality and repair platform engineered to inspect tabular datasets, identify anomalies across syntax and semantics, diagnose root causes using pattern inference, recommend and apply safe non-destructive repairs, and formally validate data integrity with a full cryptographic audit trail.

Unlike conventional rule-based scripts, **DataFix** preserves relationship integrity, explains why each modification was proposed with confidence scoring, and prevents unintended data drift.

---

## 2. Core Capabilities (The 6 Pillars)

- **DETECT**: Identifies missing values, duplicate records, primary key collisions, date format variations, malformed email domains, non-standard phone numbers, casing drift, extra whitespace, categorical typos, and numerical outliers ($z\text{-score} > 3.0$ and Tukey IQR bounds).
- **DIAGNOSE**: Infers probable causal drivers behind error patterns (e.g., regional date convention divergence, unstripped UI currency symbols, double submission during ingest, OCR/keyboard typos) with confirmed vs. suspected classifications.
- **REPAIR**: Provides two execution pipelines:
  - **Automatic Safe Repair**: Whitespace trimming, title casing, synonym reconciliation, ISO-8601 date normalization, and negative sign inversion.
  - **Guided Manual Review**: Statistical median/mode imputation, entity deduplication, and outlier review requiring human approval.
- **VALIDATE**: Re-evaluates repaired datasets across 5 dimensions (**Completeness**, **Uniqueness**, **Validity**, **Consistency**, **Accuracy**), computing before-and-after quality score improvements.
- **EXPLAIN**: Every proposed and applied repair provides row/column context, original value, corrected value, diagnosed root cause, rationale, and confidence score.
- **TRACK**: Complete immutable modification history with timestamped entries, user action types, and fine-grained undo / restore capabilities.

---

## 3. Technology Stack

- **Frontend & UI**: Streamlit with custom CSS (modern blue, white, and light-gray SaaS theme).
- **Backend & Algorithms**: Python 3.
- **Visual Analytics**: Plotly Express & Plotly Graph Objects (interactive 5-Pillar Quality Radar chart, Severity Donut chart, Issues by Category, Missing Value Matrix, and Before/After Lift Bar chart).
- **File & Excel Support**: OpenPyXL, CSV, JSON.
- **Testing**: Pytest test suite ($100\%$ pass rate across detection, repair, and validation).

---

## 4. Application Architecture & Navigation

The platform features 10 dedicated modules accessible via sidebar navigation:

1. **🏠 Dashboard**: Executive KPI cards, 5-Pillar Quality Radar, Severity Donut, Issue distributions, and recent processing history.
2. **📤 Upload Dataset**: Drag & drop support for CSV, XLSX, and JSON with schema detection, dimensions, and quick "Load Demo Dataset" button.
3. **🔍 Data Exploration**: Interactive data table, statistical summary for numeric metrics, categorical frequency distributions, and missingness heatmap.
4. **⚠️ Issue Detection**: Categorized issue cards with severity badges (Critical, High, Medium, Low), affected row lists, and problematic sample values.
5. **🔬 Root Cause Analysis**: Causal inference cards distinguishing confirmed vs. suspected drivers with evidence and confidence bars.
6. **🔧 Data Repair**: Two tabs separating safe automatic fixes from manual approval workflows, with diff tables and dataset restore options.
7. **✅ Data Validation**: Comparative before-and-after score lift, verification badges, and executive validation summary.
8. **📋 Modification History**: Full audit trail table with action filtering and CSV/JSON export.
9. **📊 Quality Reports**: Self-contained executive HTML report generation with embedded styles and instant download.
10. **💾 Export Dataset**: Download suite for Cleaned CSV, Cleaned Excel, Audit Logs, and Validation JSON summaries.

---

## 5. Installation & Quick Start

### Step 1: Navigate to the DataFix Directory
```bash
cd "c:\Users\pavan kalyan\New folder (3)\CareerAI\DataFix"
```

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Launch the Application
```bash
streamlit run app.py
```

Open your browser at **`http://localhost:8501`** to interact with the platform.

---

## 6. Running Automated Tests

Run the full pytest suite:
```bash
pytest tests/
```

All 14 tests across detection, repair, and validation execute and pass in under 2 seconds.

---

## 7. Pre-loaded Demonstration Dataset

DataFix includes a built-in realistic HR dataset at `sample_data/demo_dataset.csv` with 46 employee records containing deliberate real-world anomalies:
- Missing emails, phones, and salaries
- Exact duplicate rows and duplicate employee ID collisions
- Mixed date formats (`YYYY-MM-DD`, `MM/DD/YYYY`, `DD-Mon-YYYY`, `Month DD, YYYY`)
- Inconsistent department casing (`Engineering`, `engineering`, `ENGINEERING`, `Eng.`)
- Domain typos in emails (`@gmial.com`, missing `@`)
- Raw phone numbers and non-standard syntax
- Negative salary entries and outlier salaries

Judges can click **"↻ Reload Demo Dataset"** in the sidebar at any time to immediately test all features.
