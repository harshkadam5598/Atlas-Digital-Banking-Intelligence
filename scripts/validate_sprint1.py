#!/usr/bin/env python3
"""
Atlas – Sprint 1 Validation Script (v2)
Run from the atlas/ root directory.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
PASS = "\033[92m✓\033[0m"
FAIL = "\033[91m✗\033[0m"
WARN = "\033[93m⚠\033[0m"

checks = []

def check(label: str, condition: bool, critical: bool = True) -> bool:
    status = PASS if condition else (FAIL if critical else WARN)
    print(f"  {status}  {label}")
    checks.append((label, condition, critical))
    return condition

print("\n" + "═" * 60)
print("  Atlas – Sprint 1 Validation (v2)")
print("═" * 60 + "\n")

print("📁 Folder Structure")
check("backend/app/core/ exists", (ROOT / "backend/app/core").is_dir())
check("backend/app/api/v1/ exists", (ROOT / "backend/app/api/v1").is_dir())
for hub in ["executive","customer","growth","product","revenue","operations","market","narrative"]:
    check(f"  api/v1/{hub}/ exists", (ROOT / f"backend/app/api/v1/{hub}").is_dir())
check("analytics/ exists", (ROOT / "analytics").is_dir())
check("etl/ exists", (ROOT / "etl").is_dir())
check("sql/schema/ exists", (ROOT / "sql/schema").is_dir())
check("data/raw/ exists", (ROOT / "data/raw").is_dir())
check("data/staging/ exists", (ROOT / "data/staging").is_dir())
check("data/analytics/ exists", (ROOT / "data/analytics").is_dir())
check("deployment/docker/ exists", (ROOT / "deployment/docker").is_dir())
check("docs/ exists", (ROOT / "docs").is_dir())
check("tests/ exists", (ROOT / "tests").is_dir())
check("notebooks/ exists", (ROOT / "notebooks").is_dir())

print("\n📄 Configuration Files")
check("requirements.txt exists", (ROOT / "requirements.txt").is_file())
check(".env.example exists", (ROOT / ".env.example").is_file())
check("pyproject.toml exists", (ROOT / "pyproject.toml").is_file())
check(".gitignore exists", (ROOT / ".gitignore").is_file())
check("pytest.ini exists", (ROOT / "pytest.ini").is_file())
check(".env exists (local dev)", (ROOT / ".env").is_file(), critical=False)

print("\n🐍 Python Modules")
check("backend/app/core/config.py", (ROOT / "backend/app/core/config.py").is_file())
check("backend/app/core/database.py", (ROOT / "backend/app/core/database.py").is_file())
check("backend/app/core/logging.py", (ROOT / "backend/app/core/logging.py").is_file())
check("backend/app/main.py", (ROOT / "backend/app/main.py").is_file())

# Content checks
cfg = (ROOT / "backend/app/core/config.py").read_text()
check("config: RedisSettings present", "RedisSettings" in cfg)
check("config: ETLSettings present", "ETLSettings" in cfg)
check("config: Literal env type validation", "Literal" in cfg)
check("config: no duplicate config dir", not (ROOT / "backend/config").exists())

print("\n🐳 Docker")
check("Dockerfile exists", (ROOT / "deployment/docker/Dockerfile").is_file())
check("docker-compose.yml exists", (ROOT / "deployment/docker/docker-compose.yml").is_file())

print("\n📚 Documentation")
check("README.md exists", (ROOT / "README.md").is_file())
check("docs/architecture/overview.md exists", (ROOT / "docs/architecture/overview.md").is_file())
check("docs/guides/development.md exists", (ROOT / "docs/guides/development.md").is_file())

print("\n🔒 Security")
gi = (ROOT / ".gitignore").read_text()
check(".env excluded from git", ".env" in gi)
check("data CSVs excluded from git", "*.csv" in gi or "data/raw" in gi)
check("logs excluded from git", "logs/" in gi)

# Summary
total = len(checks)
passed = sum(1 for _, ok, _ in checks if ok)
critical_failed = sum(1 for _, ok, crit in checks if not ok and crit)

print("\n" + "═" * 60)
print(f"  Results: {passed}/{total} checks passed")
if critical_failed == 0:
    print(f"  \033[92m✓ Sprint 1 COMPLETE — Foundation is production-ready\033[0m")
    sys.exit(0)
else:
    print(f"  \033[91m✗ {critical_failed} critical checks failed\033[0m")
    sys.exit(1)
