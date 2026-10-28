#!/usr/bin/env bash
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${here}/../../.." && pwd)"
runtime_root="$(cd "${repo_root}/../../forge_runtime" && pwd)"
config_path="${OPEN_DUCK_NODE_CONFIG:-${repo_root}/config/config.yaml}"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --check) export OPEN_DUCK_READ_ONLY=1; shift ;;
    --config)
      if [[ $# -lt 2 ]]; then
        echo "--config requires a YAML path" >&2
        exit 2
      fi
      config_path="$2"
      shift 2
      ;;
    *) echo "Usage: $0 [--check] [--config PATH]" >&2; exit 2 ;;
  esac
done
if [[ ! -f "${config_path}" ]]; then
  echo "未找到连接配置：${config_path}。请恢复仓库中的 config/config.yaml，或通过 --config 指定配置文件。" >&2
  exit 2
fi
export OPEN_DUCK_NODE_CONFIG="$(realpath "${config_path}")"
uv sync --inexact --project "${repo_root}"
target="$("${repo_root}/.venv/bin/python" -c 'from robots_open_duck.config import load_config; config = load_config(); assert config.backend == "ssh", "此 workflow 使用 SSH 后端"; print(config.ssh_target)')"
control_dir="$(mktemp -d /tmp/open-duck-ssh.XXXXXX)"
export OPEN_DUCK_SSH_CONTROL_PATH="${control_dir}/socket"
cleanup() {
  ssh -S "${OPEN_DUCK_SSH_CONTROL_PATH}" -O exit "${target}" >/dev/null 2>&1 || true
  rm -rf "${control_dir}"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
# Authenticate in this terminal; Dora child processes reuse the same SSH session.
ssh -M -S "${OPEN_DUCK_SSH_CONTROL_PATH}" -o ControlPersist=no \
  -o ConnectTimeout=5 -o ServerAliveInterval=2 -o ServerAliveCountMax=2 -fN "${target}"
cd "${here}"
"${runtime_root}/.venv/bin/dora" build dataflow.yaml
"${runtime_root}/.venv/bin/dora" run dataflow.yaml
