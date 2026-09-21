"""
Atlas – Production Secret Guard Tests (Phase 1A)

Covers backend.app.main.check_production_secrets(), extracted from the
FastAPI lifespan() startup hook specifically so it could be unit-tested
without mocking an async context manager or a live database.

Uses a lightweight stand-in settings object rather than the real
AtlasSettings singleton, so these tests never depend on environment
variables or a live PostgreSQL connection.
"""

from types import SimpleNamespace

from backend.app.main import check_production_secrets


def _fake_settings(
    secret_key="a-real-secret",
    jwt_secret_key="a-real-jwt-secret",
    api_key="a-real-api-key",
    db_password="a-real-db-password",
):
    return SimpleNamespace(
        secret_key=secret_key,
        jwt=SimpleNamespace(secret_key=jwt_secret_key),
        api_key=api_key,
        db=SimpleNamespace(password=db_password),
    )


class TestProductionSecretGuard:
    """All four secrets covered: ATLAS_SECRET_KEY, JWT_SECRET_KEY, ATLAS_API_KEY, POSTGRES_PASSWORD."""

    def test_all_secrets_set_returns_empty_list(self):
        assert check_production_secrets(_fake_settings()) == []

    def test_default_atlas_secret_key_detected(self):
        s = _fake_settings(secret_key="insecure-dev-key-change-in-production")
        assert check_production_secrets(s) == ["ATLAS_SECRET_KEY"]

    def test_default_jwt_secret_key_detected(self):
        s = _fake_settings(jwt_secret_key="insecure-dev-key-change-in-production")
        assert check_production_secrets(s) == ["JWT_SECRET_KEY"]

    def test_default_api_key_detected(self):
        s = _fake_settings(api_key="insecure-dev-key-change-in-production")
        assert check_production_secrets(s) == ["ATLAS_API_KEY"]

    def test_default_postgres_password_detected(self):
        """Phase 1A addition — previously not checked at all (audit finding)."""
        s = _fake_settings(db_password="atlas_password")
        assert check_production_secrets(s) == ["POSTGRES_PASSWORD"]

    def test_multiple_defaults_all_reported(self):
        s = _fake_settings(
            secret_key="insecure-dev-key-change-in-production",
            db_password="atlas_password",
        )
        result = check_production_secrets(s)
        assert set(result) == {"ATLAS_SECRET_KEY", "POSTGRES_PASSWORD"}

    def test_postgres_password_default_is_not_confused_with_other_secrets_default(self):
        """POSTGRES_PASSWORD has its own sentinel ('atlas_password'), distinct
        from the other three secrets' shared default string. Setting a
        secret to the *other* sentinel by mistake should not mask this one,
        and vice versa."""
        s = _fake_settings(db_password="insecure-dev-key-change-in-production")
        # Not "atlas_password", so POSTGRES_PASSWORD should NOT be flagged
        # even though it happens to match the *other* secrets' default.
        assert "POSTGRES_PASSWORD" not in check_production_secrets(s)
