#!/usr/bin/env bash
# Idempotent bootstrap for the Rukn-Eg content/docs repository.
# This repo ships WordPress content-import CSVs and an audit doc; there is no
# app to build. The environment only needs Python data tooling so agents can
# parse, validate, and analyze the CSVs.
set -euo pipefail

cd "$(dirname "$0")/.."

python3 -m pip install \
  --user \
  --break-system-packages \
  --disable-pip-version-check \
  --upgrade-strategy only-if-needed \
  -r .cursor/requirements.txt

python3 - <<'PY'
import chardet, pandas
print(f"pandas {pandas.__version__}, chardet {chardet.__version__} ready")
PY
