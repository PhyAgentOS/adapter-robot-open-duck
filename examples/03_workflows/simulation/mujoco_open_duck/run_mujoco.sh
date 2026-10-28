#!/usr/bin/env bash
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH="${here}/../../../../../../simulators/mujoco_sim/src${PYTHONPATH:+:${PYTHONPATH}}"
exec "${here}/.venv/bin/python" -m mujoco_sim "$@"
