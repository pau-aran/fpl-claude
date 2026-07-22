#!/bin/bash
# SessionStart hook for Claude Code on the web: install everything the test
# suite and the model/optimizer layers need. Idempotent; pip no-ops fast when
# already satisfied. PyPI is reachable even under restrictive network policies.
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "$CLAUDE_PROJECT_DIR"

pip install -e ".[dev,models,optimize]"

# penaltyblog's PyPI metadata pins a broken `socks` package (see pyproject.toml),
# so it goes in without deps; these are the packages it actually imports at
# import time that the extras above don't already cover.
pip install --no-deps penaltyblog
pip install tabulate typing_extensions fsspec networkx lxml plotly matplotlib
