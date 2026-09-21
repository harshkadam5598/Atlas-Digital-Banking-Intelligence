"""
Atlas – Dataset Versioning System
Snapshot-based versioning: every generation run creates an immutable
versioned directory. data/raw/ always reflects the latest promoted version.

Directory layout:
  data/
    versions/
      v001_20240115_143022_seed42/
        metadata.json
        dim_customer.parquet
        fact_transactions.parquet  ...
      v002_20240116_090011_seed42/
        ...
    raw/                 ← stable read path; reflects latest promoted version
      .version_pointer.json
      *.parquet
"""

import json
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

DATA_ROOT    = Path("data")
VERSIONS_DIR = DATA_ROOT / "versions"
RAW_DIR      = DATA_ROOT / "raw"


# ── Helpers ────────────────────────────────────────────────────────────────────

def _next_version_number() -> int:
    VERSIONS_DIR.mkdir(parents=True, exist_ok=True)
    existing = [
        d for d in VERSIONS_DIR.iterdir()
        if d.is_dir() and re.match(r"v\d{3}_", d.name)
    ]
    if not existing:
        return 1
    return max(int(re.match(r"v(\d{3})_", d.name).group(1)) for d in existing) + 1


def make_version_id(seed: int, label: str = "") -> str:
    ts  = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    num = _next_version_number()
    base = f"v{num:03d}_{ts}_seed{seed}"
    return f"{base}_{label}" if label else base


# ── Public API ─────────────────────────────────────────────────────────────────

def create_version_dir(seed: int, label: str = "") -> Path:
    vid  = make_version_id(seed, label)
    vdir = VERSIONS_DIR / vid
    vdir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Dataset version created: {vid}")
    return vdir


def write_version_metadata(vdir: Path, metadata: Dict[str, Any]) -> None:
    meta = {
        "version_id":        vdir.name,
        "created_at":        datetime.utcnow().isoformat(),
        "generator_version": "1.2",
        **metadata,
    }
    (vdir / "metadata.json").write_text(json.dumps(meta, indent=2, default=str))


def read_version_metadata(vdir: Path) -> Dict[str, Any]:
    p = vdir / "metadata.json"
    return json.loads(p.read_text()) if p.exists() else {}


def list_versions() -> List[Dict[str, Any]]:
    VERSIONS_DIR.mkdir(parents=True, exist_ok=True)
    versions = []
    for d in sorted(VERSIONS_DIR.iterdir(), reverse=True):
        if d.is_dir() and re.match(r"v\d{3}_", d.name):
            versions.append({"version_id": d.name, "path": str(d),
                             **read_version_metadata(d)})
    return versions


def get_latest_version() -> Optional[Path]:
    VERSIONS_DIR.mkdir(parents=True, exist_ok=True)
    dirs = sorted(
        [d for d in VERSIONS_DIR.iterdir()
         if d.is_dir() and re.match(r"v\d{3}_", d.name)],
        reverse=True
    )
    return dirs[0] if dirs else None


def get_version_by_id(version_id: str) -> Optional[Path]:
    p = VERSIONS_DIR / version_id
    return p if p.exists() else None


def promote_to_raw(vdir: Path) -> None:
    """Copy parquet files from version dir into data/raw/ (stable ETL read path)."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    parquets = list(vdir.glob("*.parquet"))
    if not parquets:
        logger.warning(f"No parquet files to promote in {vdir}")
        return
    for src in parquets:
        shutil.copy2(src, RAW_DIR / src.name)
    pointer = {
        "source_version": vdir.name,
        "promoted_at":    datetime.utcnow().isoformat(),
        "files":          [f.name for f in parquets],
    }
    (RAW_DIR / ".version_pointer.json").write_text(json.dumps(pointer, indent=2))
    logger.success(f"Promoted {len(parquets)} files from {vdir.name} → data/raw/")


def snapshot_raw_to_version(seed: int = 42, label: str = "snapshot") -> Path:
    """
    Snapshot current data/raw/ contents into a new versioned directory.
    Call this after generation to preserve the dataset before ETL modifies raw/.
    """
    vdir = create_version_dir(seed, label)
    parquets = list(RAW_DIR.glob("*.parquet"))
    for src in parquets:
        shutil.copy2(src, vdir / src.name)
    # Copy reproducibility proof if present
    for extra in ["reproducibility_proof.json", "validation_report.json"]:
        src = RAW_DIR / extra
        if src.exists():
            shutil.copy2(src, vdir / extra)
    row_counts = {}
    try:
        import pandas as pd
        for f in vdir.glob("*.parquet"):
            row_counts[f.stem] = len(pd.read_parquet(f))
    except Exception:
        pass
    write_version_metadata(vdir, {"seed": seed, "row_counts": row_counts,
                                   "source": "snapshot_raw"})
    logger.success(f"Snapshotted {len(parquets)} files into {vdir.name}")
    return vdir


def get_raw_version() -> Optional[str]:
    p = RAW_DIR / ".version_pointer.json"
    return json.loads(p.read_text()).get("source_version") if p.exists() else None
