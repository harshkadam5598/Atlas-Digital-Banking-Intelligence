"""
Atlas ETL – Execution Report Generator
Produces structured JSON and human-readable text report after each ETL run.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from loguru import logger

from etl.core.context import ETLContext

REPORTS_DIR = Path("etl/reports/runs")


def generate_report(ctx: ETLContext, output_dir: str = "data/staging") -> Dict[str, Any]:
    """
    Build the complete ETL execution report dict and write JSON + text files.
    """
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    stage_summary = {}
    for name, s in ctx.stages.items():
        stage_summary[name] = {
            "rows_in":       s.rows_in,
            "rows_out":      s.rows_out,
            "rows_rejected": s.rows_rejected,
            "rejection_rate":s.rejection_rate,
            "duration_s":    s.duration_s,
            "passed":        s.passed,
            "warnings":      s.warnings,
            "errors":        s.errors,
        }

    report = {
        "run_id":              ctx.run_id,
        "source_version":      ctx.source_version,
        "status":              ctx.status,
        "started_at":          ctx.started_at.isoformat(),
        "completed_at":        datetime.utcnow().isoformat(),
        "elapsed_seconds":     ctx.elapsed_s,

        "pipeline_metrics": {
            "rows_extracted":   ctx.total_extracted,
            "rows_transformed": ctx.total_transformed,
            "rows_loaded":      ctx.total_loaded,
            "rows_rejected":    ctx.total_rejected,
        },

        "data_quality": {
            "score":          ctx.data_quality_score,
            "checks_passed":  ctx.dq_checks_passed,
            "checks_failed":  ctx.dq_checks_failed,
            "total_checks":   ctx.dq_checks_passed + ctx.dq_checks_failed,
        },

        "stages":    stage_summary,
        "warnings":  ctx.warnings,
        "errors":    ctx.errors,
        "audit_log": ctx.audit_log[-50:],   # last 50 entries to keep file manageable
    }

    # Write JSON
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    json_path = REPORTS_DIR / f"etl_report_{ts}.json"
    json_path.write_text(json.dumps(report, indent=2, default=str))

    # Write to staging dir too
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    (Path(output_dir) / "etl_execution_report.json").write_text(
        json.dumps(report, indent=2, default=str))

    # Write text summary
    txt = _build_text_report(report)
    txt_path = REPORTS_DIR / f"etl_report_{ts}.txt"
    txt_path.write_text(txt)
    (Path(output_dir) / "etl_execution_report.txt").write_text(txt)

    logger.success(f"ETL report written → {json_path}")
    print("\n" + txt)
    return report


def _build_text_report(r: Dict[str, Any]) -> str:
    s   = r["status"]
    pm  = r["pipeline_metrics"]
    dq  = r["data_quality"]
    status_icon = {"PASSED": "✅", "PASS_WITH_WARNINGS": "⚠️", "FAILED": "❌"}.get(s, "?")

    lines = [
        "=" * 66,
        "  ATLAS ETL — EXECUTION REPORT",
        "=" * 66,
        f"  Run ID:          {r['run_id']}",
        f"  Source Version:  {r['source_version']}",
        f"  Status:          {status_icon}  {s}",
        f"  Started:         {r['started_at'][:19]}",
        f"  Elapsed:         {r['elapsed_seconds']}s",
        "",
        "  ── Pipeline Metrics ─────────────────────────────────────",
        f"  Rows Extracted:   {pm['rows_extracted']:>10,}",
        f"  Rows Transformed: {pm['rows_transformed']:>10,}",
        f"  Rows Loaded:      {pm['rows_loaded']:>10,}",
        f"  Rows Rejected:    {pm['rows_rejected']:>10,}",
        "",
        "  ── Data Quality ─────────────────────────────────────────",
        f"  DQ Score:         {dq['score']:>9.1f} / 100",
        f"  Checks Passed:    {dq['checks_passed']:>10,}",
        f"  Checks Failed:    {dq['checks_failed']:>10,}",
        "",
        "  ── Stage Breakdown ──────────────────────────────────────",
        f"  {'Stage':<28} {'In':>8} {'Out':>8} {'Rej':>6} {'Sec':>6} {'OK?'}",
        "  " + "-" * 62,
    ]

    for name, st in r["stages"].items():
        ok = "✓" if st["passed"] else "✗"
        lines.append(
            f"  {name:<28} {st['rows_in']:>8,} {st['rows_out']:>8,} "
            f"{st['rows_rejected']:>6,} {st['duration_s']:>5.1f}s  {ok}"
        )

    if r["warnings"]:
        lines += ["", "  ── Warnings ─────────────────────────────────────────────"]
        for w in r["warnings"][:15]:
            lines.append(f"  ⚠  {w}")
        if len(r["warnings"]) > 15:
            lines.append(f"  ... and {len(r['warnings'])-15} more")

    if r["errors"]:
        lines += ["", "  ── Errors ───────────────────────────────────────────────"]
        for e in r["errors"]:
            lines.append(f"  ✗  {e}")

    lines += ["", "=" * 66]
    return "\n".join(lines)
