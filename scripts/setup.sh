#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_PATH="${PROJECT_ROOT}/.venv"

python3 -m venv "${VENV_PATH}"
# shellcheck disable=SC1091
source "${VENV_PATH}/bin/activate"
python -m pip install --upgrade pip
pip install -r "${PROJECT_ROOT}/requirements.txt"

printf 'Environment ready.\nRun the services with:\n  source %s/bin/activate\n  uvicorn gateway:app --reload --port 8000\nRun tests with:\n  pytest -q\n' "${VENV_PATH}"
