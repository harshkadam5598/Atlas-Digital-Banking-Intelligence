"""
Atlas ETL – Run Context
Single object threaded through every pipeline stage.
Accumulates metrics, audit log, warnings, errors.
Produces the final ETL execution report.
"""

import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class StageMetrics:
    stage:         str
    rows_in:       int   = 0
    rows_out:      int   = 0
    rows_rejected: int   = 0
    duration_s:    float = 0.0
    warnings:      List[str] = field(default_factory=list)
    errors:        List[str] = field(default_factory=list)
    checks_passed: int   = 0
    checks_failed: int   = 0

    @property
    def rejection_rate(self) -> float:
        return round(self.rows_rejected / self.rows_in, 4) if self.rows_in else 0.0

    @property
    def passed(self) -> bool:
        return not self.errors


@dataclass
class ETLContext:
    run_id:         str
    source_version: str
    raw_dir:        Path
    staging_dir:    Path
    started_at:     datetime = field(default_factory=datetime.utcnow)

    stages:              Dict[str, StageMetrics] = field(default_factory=dict)
    total_extracted:     int = 0
    total_transformed:   int = 0
    total_loaded:        int = 0
    total_rejected:      int = 0
    dq_checks_passed:    int = 0
    dq_checks_failed:    int = 0
    warnings:            List[str] = field(default_factory=list)
    errors:              List[str] = field(default_factory=list)
    audit_log:           List[Dict[str, Any]] = field(default_factory=list)

    _timers: Dict[str, float] = field(default_factory=dict, repr=False)

    # ── Stage lifecycle ───────────────────────────────────────────────────────

    def begin_stage(self, name: str) -> StageMetrics:
        m = StageMetrics(stage=name)
        self.stages[name] = m
        self._timers[name] = time.perf_counter()
        return m

    def end_stage(self, name: str) -> None:
        if name in self._timers:
            self.stages[name].duration_s = round(
                time.perf_counter() - self._timers[name], 3)

    # ── Logging helpers ───────────────────────────────────────────────────────

    def warn(self, msg: str, stage: Optional[str] = None) -> None:
        self.warnings.append(msg)
        if stage and stage in self.stages:
            self.stages[stage].warnings.append(msg)

    def error(self, msg: str, stage: Optional[str] = None) -> None:
        self.errors.append(msg)
        if stage and stage in self.stages:
            self.stages[stage].errors.append(msg)

    def log_audit(self, table: str, action: str, rows: int,
                  detail: str = "") -> None:
        self.audit_log.append({
            "ts": datetime.utcnow().isoformat(),
            "table": table, "action": action,
            "rows": rows, "detail": detail,
        })

    def record_dq(self, passed: bool, stage: Optional[str] = None) -> None:
        if passed:
            self.dq_checks_passed += 1
            if stage and stage in self.stages:
                self.stages[stage].checks_passed += 1
        else:
            self.dq_checks_failed += 1
            if stage and stage in self.stages:
                self.stages[stage].checks_failed += 1

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def data_quality_score(self) -> float:
        total = self.dq_checks_passed + self.dq_checks_failed
        return round(100 * self.dq_checks_passed / total, 1) if total else 0.0

    @property
    def elapsed_seconds(self) -> float:
        return round((datetime.utcnow() - self.started_at).total_seconds(), 2)

    @property
    def overall_status(self) -> str:
        if self.errors:           return "FAILED"
        if self.warnings:         return "PASS_WITH_WARNINGS"
        return "PASSED"

    # ── Report ────────────────────────────────────────────────────────────────

    def build_report(self) -> Dict[str, Any]:
        return {
            "run_id":              self.run_id,
            "source_version":      self.source_version,
            "started_at":          self.started_at.isoformat(),
            "elapsed_seconds":     self.elapsed_seconds,
            "overall_status":      self.overall_status,
            "data_quality_score":  self.data_quality_score,
            "summary": {
                "rows_extracted":    self.total_extracted,
                "rows_transformed":  self.total_transformed,
                "rows_loaded":       self.total_loaded,
                "rows_rejected":     self.total_rejected,
                "dq_checks_passed":  self.dq_checks_passed,
                "dq_checks_failed":  self.dq_checks_failed,
            },
            "stages": {
                name: {
                    "rows_in":       m.rows_in,
                    "rows_out":      m.rows_out,
                    "rows_rejected": m.rows_rejected,
                    "duration_s":    m.duration_s,
                    "status":        "PASS" if m.passed else "FAIL",
                    "warnings":      m.warnings,
                    "errors":        m.errors,
                    "checks_passed": m.checks_passed,
                    "checks_failed": m.checks_failed,
                }
                for name, m in self.stages.items()
            },
            "warnings": self.warnings,
            "errors":   self.errors,
            "audit_log": self.audit_log,
        }

    def write_report(self, output_dir: Path) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        report = self.build_report()
        path = output_dir / f"etl_report_{self.run_id}.json"
        path.write_text(json.dumps(report, indent=2, default=str))
        return path
