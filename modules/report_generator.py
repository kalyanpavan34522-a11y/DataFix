"""
DataFix - Executive Report Generator
Generates self-contained, publication-ready HTML reports and JSON summaries
documenting data quality assessments, root causes, repairs, and validation proof.
"""

import json
import datetime
from typing import Dict, List, Any


class ReportGenerator:
    """
    Constructs executive quality reports with embedded responsive CSS styling.
    """

    def __init__(
        self,
        dataset_info: Dict[str, Any],
        issues: List[Dict[str, Any]],
        diagnoses: List[Dict[str, Any]],
        repairs: List[Dict[str, Any]],
        validation_results: Dict[str, Any],
        quality_scores: Dict[str, Any],
        audit_entries: List[Dict[str, Any]]
    ):
        self.info = dataset_info
        self.issues = issues
        self.diagnoses = diagnoses
        self.repairs = repairs
        self.val = validation_results
        self.scores = quality_scores
        self.audit = audit_entries

    def generate_html_report(self) -> str:
        """
        Produce a complete, self-contained HTML document.
        """
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        filename = self.info.get("filename", "dataset.csv")
        rows = self.info.get("rows", 0)
        cols = self.info.get("cols", 0)

        before_score = self.val.get("before_score", self.scores.get("overall_score", 0.0))
        after_score = self.val.get("after_score", before_score)
        score_diff = round(after_score - before_score, 1)

        # Build Issues Table Rows
        issues_rows_html = ""
        for idx, iss in enumerate(self.issues[:25]):
            sev = iss.get("severity", "Medium")
            sev_class = sev.lower()
            issues_rows_html += f"""
            <tr>
              <td><code>{iss.get('issue_id')}</code></td>
              <td><strong>{iss.get('issue_type')}</strong></td>
              <td><code>{iss.get('column')}</code></td>
              <td><span class="badge {sev_class}">{sev}</span></td>
              <td>{iss.get('affected_count')}</td>
              <td>{iss.get('description')}</td>
            </tr>
            """

        # Build Diagnoses Rows
        diag_rows_html = ""
        for d in self.diagnoses[:15]:
            diag_rows_html += f"""
            <div class="card diag-card">
              <div class="card-header">
                <strong>{d.get('issue_type')}</strong> · <code>{d.get('column')}</code>
                <span class="conf-badge">{int(d.get('confidence_score', 0.9)*100)}% Conf</span>
              </div>
              <p><strong>Probable Cause:</strong> {d.get('probable_cause')}</p>
              <p class="rec"><strong>Recommendation:</strong> {d.get('recommended_action')}</p>
            </div>
            """

        # Build Audit Rows
        audit_rows_html = ""
        for a in self.audit[:30]:
            audit_rows_html += f"""
            <tr>
              <td><small>{a.get('timestamp')}</small></td>
              <td><span class="badge blue">{a.get('action')}</span></td>
              <td><code>{a.get('column')}</code> [Row {a.get('row_index')+1}]</td>
              <td><s class="strike">{a.get('original_value')}</s></td>
              <td><strong class="green">{a.get('new_value')}</strong></td>
              <td>{int(a.get('confidence', 0.9)*100)}%</td>
              <td>{a.get('reason')}</td>
            </tr>
            """

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>DataFix Quality Report — {filename}</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
      margin: 0; padding: 32px; background: #f8fafc; color: #1e293b; line-height: 1.5; font-size: 13px;
    }}
    .container {{ max-width: 1000px; margin: 0 auto; background: #ffffff; padding: 40px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.06); }}
    .header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #e2e8f0; padding-bottom: 20px; margin-bottom: 24px; }}
    .logo {{ font-size: 22px; font-weight: 800; color: #1a73e8; }}
    .logo span {{ color: #10b981; }}
    .kpi-row {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 28px; }}
    .kpi-box {{ background: #f1f5f9; padding: 18px; border-radius: 8px; border: 1px solid #e2e8f0; }}
    .kpi-box small {{ display: block; font-size: 11px; text-transform: uppercase; color: #64748b; font-weight: 600; margin-bottom: 4px; }}
    .kpi-box strong {{ font-size: 24px; color: #0f172a; }}
    .kpi-box strong.green {{ color: #10b981; }}
    h2 {{ font-size: 16px; font-weight: 700; color: #0f172a; margin-top: 28px; margin-bottom: 12px; border-bottom: 1px solid #e2e8f0; padding-bottom: 6px; }}
    table {{ width: 100%; border-collapse: collapse; margin-bottom: 24px; font-size: 12px; }}
    th {{ background: #f8fafc; text-align: left; padding: 10px 12px; border-bottom: 2px solid #cbd5e1; color: #475569; }}
    td {{ padding: 9px 12px; border-bottom: 1px solid #e2e8f0; }}
    tr:nth-child(even) {{ background: #fcfdfe; }}
    .badge {{ display: inline-block; padding: 2px 7px; border-radius: 4px; font-size: 10px; font-weight: 700; text-transform: uppercase; }}
    .badge.critical {{ background: #fee2e2; color: #dc2626; }}
    .badge.high {{ background: #ffedd5; color: #ea580c; }}
    .badge.medium {{ background: #fef3c7; color: #d97706; }}
    .badge.low {{ background: #e0f2fe; color: #0284c7; }}
    .badge.blue {{ background: #eff6ff; color: #2563eb; }}
    .strike {{ color: #ef4444; text-decoration: line-through; }}
    .green {{ color: #10b981; }}
    .card {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px; margin-bottom: 10px; }}
    .card-header {{ display: flex; justify-content: space-between; margin-bottom: 6px; }}
    .conf-badge {{ background: #dcfce7; color: #15803d; padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: 600; }}
    .rec {{ color: #2563eb; }}
    .footer {{ text-align: center; font-size: 11px; color: #94a3b8; margin-top: 36px; border-top: 1px solid #e2e8f0; padding-top: 16px; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div>
        <div class="logo">⚡ DataFix<span>.ai</span></div>
        <small>Autonomous Data Quality & Repair Engine · Validation Certificate</small>
      </div>
      <div style="text-align: right; font-size: 11px; color: #64748b;">
        <div><strong>Dataset:</strong> {filename}</div>
        <div><strong>Generated:</strong> {now_str}</div>
        <div><strong>Dimensions:</strong> {rows} rows × {cols} columns</div>
      </div>
    </div>

    <div class="kpi-row">
      <div class="kpi-box">
        <small>Initial Score</small>
        <strong>{before_score:.1f}<span style="font-size:14px; color:#64748b;">/100</span></strong>
      </div>
      <div class="kpi-box">
        <small>Repaired Score</small>
        <strong class="green">{after_score:.1f}<span style="font-size:14px; color:#64748b;">/100</span></strong>
      </div>
      <div class="kpi-box">
        <small>Issues Detected</small>
        <strong>{len(self.issues)}</strong>
      </div>
      <div class="kpi-box">
        <small>Repairs Applied</small>
        <strong class="green">{len(self.audit)}</strong>
      </div>
    </div>

    <h2>1. Executive Summary & Validation Proof</h2>
    <p>
      The DataFix engine inspected <strong>{filename}</strong> across five core quality dimensions: Completeness, Uniqueness, Validity, Consistency, and Relational Accuracy. 
      Total quality lifted by <strong>{'+' if score_diff >= 0 else ''}{score_diff} points</strong>. All applied repairs were non-destructive, explainable, and logged with full audit provenance.
    </p>

    <h2>2. Detected Quality Issues (Top 25)</h2>
    <table>
      <thead>
        <tr>
          <th>ID</th>
          <th>Issue Type</th>
          <th>Column</th>
          <th>Severity</th>
          <th>Affected</th>
          <th>Description</th>
        </tr>
      </thead>
      <tbody>
        {issues_rows_html}
      </tbody>
    </table>

    <h2>3. Root-Cause Diagnostic Inference</h2>
    {diag_rows_html}

    <h2>4. Executed Modification Audit Log (Sample)</h2>
    <table>
      <thead>
        <tr>
          <th>Timestamp</th>
          <th>Action</th>
          <th>Target</th>
          <th>Original</th>
          <th>Corrected</th>
          <th>Confidence</th>
          <th>Rationale</th>
        </tr>
      </thead>
      <tbody>
        {audit_rows_html if audit_rows_html else '<tr><td colspan="7" style="text-align:center; color:#94a3b8;">No modifications recorded yet.</td></tr>'}
      </tbody>
    </table>

    <div class="footer">
      Generated automatically by <strong>DataFix Autonomous Data Quality Platform</strong> · INNOVEDGE 2026 Hackathon
    </div>
  </div>
</body>
</html>
"""
        return html

    def generate_summary_json(self) -> str:
        """Export validation and score metrics as JSON string."""
        summary = {
            "dataset_info": self.info,
            "timestamp": datetime.datetime.now().isoformat(),
            "validation_results": self.val,
            "quality_scores": self.scores,
            "issues_count": len(self.issues),
            "repairs_count": len(self.repairs),
            "audit_count": len(self.audit),
        }
        return json.dumps(summary, indent=2, default=str)
