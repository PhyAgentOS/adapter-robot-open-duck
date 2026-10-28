#!/usr/bin/env bash
set -euo pipefail

workflow_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${workflow_dir}/../../../.." && pwd)"
runtime_root="$(cd "${repo_root}/../../forge_runtime" && pwd)"
viewer_root="$(cd "${repo_root}/../../tools/viewers/image_viewer" && pwd)"

cd "${workflow_dir}"
uv sync
uv run python "${repo_root}/scripts/generate_configs.py" --workflow-dir .
export FORGE_VIEWER_BIN="${FORGE_VIEWER_BIN:-${viewer_root}/target/release}"
cargo build --manifest-path "${viewer_root}/Cargo.toml" --release --locked --bin image_viewer
export FORGE_RUNTIME_BIN="${FORGE_RUNTIME_BIN:-${runtime_root}/target/release}"
"${runtime_root}/.venv/bin/dora" build dataflow.yaml
exec "${runtime_root}/.venv/bin/dora" run dataflow.yaml
