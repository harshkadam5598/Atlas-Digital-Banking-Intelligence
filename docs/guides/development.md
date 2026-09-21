# Atlas Development Guide

## Prerequisites

- Python 3.11+
- PostgreSQL 16+
- Docker + Docker Compose (recommended for local DB)
- Git

## Local Setup

```bash
# Clone repository
git clone https://github.com/your-username/atlas.git
cd atlas

# Run setup script
bash scripts/setup.sh

# Or manually:
python -m venv .venv
source .venv/bin/activate           # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                # Edit .env with your values

# Start database (Docker)
docker-compose -f deployment/docker/docker-compose.yml up -d postgres

# Start API server
uvicorn backend.app.main:app --reload

# Validate Sprint 1
python scripts/validate_sprint1.py
```

## Environment Variables

See `.env.example` for the full list. Critical variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `DB_HOST` | PostgreSQL host | `localhost` |
| `DB_NAME` | Database name | `atlas_db` |
| `DB_USER` | Database user | `atlas_user` |
| `DB_PASSWORD` | Database password | `atlas_password` |
| `ATLAS_ENV` | Environment | `development` |

## Running Tests

```bash
pytest                         # All tests
pytest tests/unit/             # Unit tests only
pytest -k "test_config"        # Specific test
pytest --cov-report=html       # Coverage HTML report
```

## Code Style

```bash
black .                        # Format code
isort .                        # Sort imports
flake8 .                       # Lint
mypy backend/                  # Type check
```
