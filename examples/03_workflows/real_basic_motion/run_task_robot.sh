#!/usr/bin/env bash
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "${here}/../../../.venv/bin/python" "${here}/../../../../../forge_runtime/packages/nodes/task_robot/main.py" "$@"
