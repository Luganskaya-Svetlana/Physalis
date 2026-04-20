#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT_DIR="$ROOT_DIR/physalisproject"
VENV_DIR="${VENV_DIR:-$ROOT_DIR/venv}"
PYTHON_BIN="${PYTHON_BIN:-$VENV_DIR/bin/python}"
PIP_BIN="${PIP_BIN:-$VENV_DIR/bin/pip}"
GUNICORN_SERVICE="${GUNICORN_SERVICE:-gunicorn}"

if [[ ! -x "$PYTHON_BIN" ]]; then
    echo "Python not found at $PYTHON_BIN"
    echo "Set PYTHON_BIN or VENV_DIR before running deploy."
    exit 1
fi

cd "$ROOT_DIR"
"$PIP_BIN" install -r requirements.txt

cd "$PROJECT_DIR"
"$PYTHON_BIN" manage.py migrate --noinput
"$PYTHON_BIN" manage.py collectstatic --noinput

sudo systemctl restart "$GUNICORN_SERVICE"
sudo systemctl --no-pager --full status "$GUNICORN_SERVICE"
