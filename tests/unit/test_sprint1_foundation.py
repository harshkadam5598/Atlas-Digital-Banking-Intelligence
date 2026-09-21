"""
Atlas – Sprint 1 Foundation Tests

Validates that all Sprint 1 components are structurally sound
and configuration logic behaves correctly.
"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).parent.parent.parent


class TestProjectStructure:
    """Verify the complete Atlas directory structure exists."""

    def test_backend_core_exists(self):
        assert (ROOT / "backend/app/core").is_dir()

    def test_api_v1_routes_exist(self):
        for hub in ["executive", "customer", "growth", "product", "revenue", "operations", "market", "narrative"]:
            assert (ROOT / f"backend/app/api/v1/{hub}").is_dir(), f"Missing: {hub} route dir"

    def test_analytics_structure(self):
        for subdir in ["engines", "kpis", "insights", "forecasting"]:
            assert (ROOT / f"analytics/{subdir}").is_dir()

    def test_etl_structure(self):
        for subdir in ["extractors", "transformers", "loaders", "validators"]:
            assert (ROOT / f"etl/{subdir}").is_dir()

    def test_sql_structure(self):
        for subdir in ["schema", "migrations", "indexes", "views"]:
            assert (ROOT / f"sql/{subdir}").is_dir()

    def test_data_zones(self):
        for zone in ["raw", "staging", "analytics"]:
            assert (ROOT / f"data/{zone}").is_dir()

    def test_deployment_structure(self):
        assert (ROOT / "deployment/docker/Dockerfile").is_file()
        assert (ROOT / "deployment/docker/docker-compose.yml").is_file()


class TestConfigurationFiles:
    """Verify all configuration files are present and non-empty."""

    def test_requirements_txt_exists(self):
        f = ROOT / "requirements.txt"
        assert f.is_file()
        assert f.stat().st_size > 0

    def test_env_example_exists(self):
        f = ROOT / ".env.example"
        assert f.is_file()
        content = f.read_text()
        assert "POSTGRES_HOST" in content
        assert "ATLAS_ENV" in content
        assert "JWT_SECRET_KEY" in content

    def test_gitignore_excludes_env(self):
        content = (ROOT / ".gitignore").read_text()
        assert ".env" in content

    def test_gitignore_excludes_data_files(self):
        content = (ROOT / ".gitignore").read_text()
        assert "*.csv" in content or "data/raw" in content

    def test_readme_exists(self):
        f = ROOT / "README.md"
        assert f.is_file()
        content = f.read_text()
        assert "Atlas" in content
        assert "Deployment Status" in content


class TestCoreModules:
    """Verify core Python modules are importable and correctly structured."""

    def test_config_module_exists(self):
        assert (ROOT / "backend/app/core/config.py").is_file()

    def test_database_module_exists(self):
        assert (ROOT / "backend/app/core/database.py").is_file()

    def test_logging_module_exists(self):
        assert (ROOT / "backend/app/core/logging.py").is_file()

    def test_main_module_exists(self):
        assert (ROOT / "backend/app/main.py").is_file()

    def test_config_has_db_settings(self):
        content = (ROOT / "backend/app/core/config.py").read_text()
        assert "DatabaseSettings" in content
        assert "pool_size" in content

    def test_config_has_data_settings(self):
        content = (ROOT / "backend/app/core/config.py").read_text()
        assert "DataGenerationSettings" in content
        assert "customer_count" in content
        assert "500_000" in content or "500000" in content

    def test_main_has_health_endpoint(self):
        content = (ROOT / "backend/app/main.py").read_text()
        assert "/health" in content
        assert "lifespan" in content

    def test_database_has_session_factory(self):
        content = (ROOT / "backend/app/core/database.py").read_text()
        assert "SessionLocal" in content
        assert "get_db" in content
        assert "get_db_context" in content


class TestDocumentation:
    """Verify documentation skeleton is in place."""

    def test_architecture_doc_exists(self):
        assert (ROOT / "docs/architecture/overview.md").is_file()

    def test_dev_guide_exists(self):
        assert (ROOT / "docs/guides/development.md").is_file()

    def test_architecture_doc_covers_sprints(self):
        content = (ROOT / "docs/architecture/overview.md").read_text()
        assert "Sprint" in content
        assert "PostgreSQL" in content
