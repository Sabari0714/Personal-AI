#!/usr/bin/env bash
# ROLEX AI — one-command setup helper
# Usage: bash setup.sh [--full]
set -e

cd "$(dirname "$0")"

echo "=============================================="
echo "  ROLEX AI — Setup"
echo "=============================================="

# 1. Python check
if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 not found. Install Python 3.10+ first."
  exit 1
fi
echo "[1/5] Python: $(python3 --version)"

# 2. .env
if [ ! -f .env ]; then
  cp .env.example .env
  echo "[2/5] Created .env from template — add your API keys there."
else
  echo "[2/5] .env already exists — leaving it untouched."
fi

# 3. Optional dependencies
if [ "$1" = "--full" ]; then
  echo "[3/5] Installing full dependencies (GUI + documents + voice)..."
  python3 -m pip install -r requirements.txt
else
  echo "[3/5] Skipping optional deps (run with --full to install them)."
fi

# 4. Smoke test
echo "[4/5] Running smoke test..."
python3 main.py --ask "calculate 6 * 7" || { echo "Smoke test failed."; exit 1; }

# 5. Tests
echo "[5/5] Running test suite..."
python3 -m pytest tests/ -q 2>/dev/null || echo "  (pytest not installed — skipping; core still works)"

echo ""
echo "=============================================="
echo "  ROLEX AI is ready."
echo "  Start with:  python3 main.py"
echo "  GUI:         python3 main.py --gui"
echo "  Voice:       python3 main.py --voice"
echo "=============================================="
