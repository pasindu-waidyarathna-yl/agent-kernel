#!/bin/bash

set -euo pipefail
uv venv --allow-existing

if [[ ${1-} != "local" ]]; then
  uv sync --all-extras
else
  # For local development of agentkernel, build and install from local source
  cd ../../../ak-py && uv build --wheel && cd -
  uv sync --all-extras
  uv pip install --reinstall --no-deps ../../../ak-py/dist/agentkernel-0.2.6-py3-none-any.whl
fi

echo ""
echo "To run the server:"
echo "  source .venv/bin/activate && python server.py"
echo ""
echo "Or use: uv run --no-sync server.py"
