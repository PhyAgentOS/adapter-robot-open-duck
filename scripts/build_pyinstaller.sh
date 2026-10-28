#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
package_dir="$(cd "${script_dir}/.." && pwd)"
dist_dir="${package_dir}/dist"
work_dir="${package_dir}/build/pyinstaller"
build_venv="${package_dir}/.venv_build"

mkdir -p "${dist_dir}" "${work_dir}"
rm -f "${dist_dir}/robots_open_duck"
rm -rf "${build_venv}"
trap 'rm -rf "${build_venv}"' EXIT

UV_PROJECT_ENVIRONMENT="${build_venv}" uv sync \
  --project "${package_dir}" \
  --frozen \
  --no-dev \
  --extra pyinstaller \
  --python 3.12

"${build_venv}/bin/pyinstaller" \
  --noconfirm \
  --clean \
  --distpath "${dist_dir}" \
  --workpath "${work_dir}" \
  "${script_dir}/robots_open_duck.spec"

test -x "${dist_dir}/robots_open_duck"
echo "OK: ${dist_dir}/robots_open_duck"
