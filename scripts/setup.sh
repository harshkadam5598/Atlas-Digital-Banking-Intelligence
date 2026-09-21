#!/usr/bin/env bash
# ============================================================
# Atlas – Digital Banking Intelligence Platform
# Local Development Setup Script
# ============================================================
set -euo pipefail

BLUE='\033[0;34m'
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════╗"
echo "║     Atlas Digital Banking Intelligence Platform      ║"
echo "║                   Setup Script                       ║"
echo "╚══════════════════════════════════════════════════════╝"
echo -e "${NC}"

# ─── Check Python version ─────────────────────────────────────
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
REQUIRED="3.11"
if [[ "$(printf '%s\n' "$REQUIRED" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED" ]]; then
    echo -e "${RED}ERROR: Python $REQUIRED+ required. Found $PYTHON_VERSION${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python $PYTHON_VERSION${NC}"

# ─── Create virtual environment ───────────────────────────────
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi
source .venv/bin/activate
echo -e "${GREEN}✓ Virtual environment activated${NC}"

# ─── Install dependencies ─────────────────────────────────────
echo "Installing dependencies..."
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo -e "${GREEN}✓ Dependencies installed${NC}"

# ─── Create .env if missing ───────────────────────────────────
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo -e "${YELLOW}⚠  Created .env from .env.example — please review and update values${NC}"
else
    echo -e "${GREEN}✓ .env exists${NC}"
fi

# ─── Create data directories ──────────────────────────────────
mkdir -p data/raw data/staging data/analytics logs
echo -e "${GREEN}✓ Data directories created${NC}"

# ─── Verify PostgreSQL connection ─────────────────────────────
echo "Checking PostgreSQL connection..."
python3 -c "
from backend.app.core.database import verify_connection
if verify_connection():
    print('\033[0;32m✓ Database connection verified\033[0m')
else:
    print('\033[1;33m⚠  Database not reachable — start PostgreSQL or use Docker Compose\033[0m')
    print('  Run: docker-compose -f deployment/docker/docker-compose.yml up -d postgres')
" 2>/dev/null || echo -e "${YELLOW}⚠  Could not verify DB (install deps first or start Docker)${NC}"

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  Atlas setup complete.${NC}"
echo -e "${GREEN}  Start API:  uvicorn backend.app.main:app --reload${NC}"
echo -e "${GREEN}  Docs:       http://localhost:8000/docs${NC}"
echo -e "${GREEN}  Health:     http://localhost:8000/health${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
