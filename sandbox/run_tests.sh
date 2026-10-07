#!/usr/bin/env bash

set -e

PROJECT_ROOT="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"

cd "$PROJECT_ROOT"

echo "========================================"
echo " AI PROJECT TESTER - TEST SUITE"
echo "========================================"

echo ""
echo "[1/4] Checking Python..."

python3 --version

echo ""
echo "[2/4] Checking pytest..."

python3 -m pytest --version

echo ""
echo "[3/4] Checking Python syntax..."

python3 -m compileall -q core

if [ -f app.py ]; then
    python3 -m py_compile app.py
fi

echo "Syntax check passed."

echo ""
echo "[4/4] Running unit tests..."

python3 -m pytest -q

echo ""
echo "========================================"
echo " ALL TESTS PASSED"
echo "========================================"