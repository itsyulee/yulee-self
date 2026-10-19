#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
exec "${YULEESELF_PYTHON:-python3}" setup.py "$@"
