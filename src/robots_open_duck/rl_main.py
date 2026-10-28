"""Dora entry point for the native Open Duck RL walking mode."""
from __future__ import annotations

import argparse
from collections.abc import Mapping
from pathlib import Path
import re
import subprocess
from typing import Any

from forge_robot.node_runner import run_dora_robot_node
import yaml

from .rl_driver import OpenDuckRLDriver, RLWalkConfig


ALLOWED_CONNECTION_FIELDS = frozenset({"host", "user"})
USER_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")


def _load_mapping(path: Path, *, label: str) -> dict[str, Any]:
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError(f"cannot read {label}: {path}") from exc
    except yaml.YAMLError as exc:
        raise ValueError(f"cannot parse {label}: {path}") from exc
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must contain a YAML mapping: {path}")
    return dict(value)


def load_ssh_target(path: Path) -> str:
    data = _load_mapping(path, label="Open Duck connection config")
    unknown = sorted(set(data) - ALLOWED_CONNECTION_FIELDS)
    if unknown:
        raise ValueError(f"unknown Open Duck connection fields: {unknown}")
    host = data.get("host")
    user = data.get("user", "pi")
    if (
        not isinstance(host, str)
        or not host
        or host != host.strip()
        or host.startswith("-")
        or "@" in host
        or any(character.isspace() or character == "\0" for character in host)
    ):
        raise ValueError("Open Duck connection field 'host' is invalid")
    if not isinstance(user, str) or not USER_PATTERN.fullmatch(user):
        raise ValueError("Open Duck connection field 'user' is invalid")
    return f"{user}@{host}"


def load_rl_config(config_path: Path, connection_path: Path) -> RLWalkConfig:
    data = _load_mapping(config_path, label="Open Duck RL profile config")
    if "ssh_target" in data:
        raise ValueError(
            "Open Duck RL profile must not hard-code ssh_target; use the connection config"
        )
    return RLWalkConfig(**{**data, "ssh_target": load_ssh_target(connection_path)})


def check_noninteractive_ssh(ssh_target: str) -> None:
    command = [
        "ssh", "-T", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5",
        ssh_target, "true",
    ]
    try:
        result = subprocess.run(
            command, check=False, capture_output=True, text=True, timeout=8
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError(
            f"non-interactive SSH preflight failed for {ssh_target}"
        ) from exc
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        suffix = f": {detail}" if detail else ""
        raise RuntimeError(
            f"non-interactive SSH preflight failed for {ssh_target}{suffix}. "
            "Configure an SSH key and accept the host key before starting the Skill."
        )


def run(config_path: str, connection_path: str) -> int:
    config = load_rl_config(Path(config_path), Path(connection_path))
    check_noninteractive_ssh(config.ssh_target)
    driver = OpenDuckRLDriver(config)
    try:
        driver.connect()
        return run_dora_robot_node(driver)
    finally:
        driver.disconnect()


def main() -> None:
    parser = argparse.ArgumentParser(description="Open Duck native RL walking driver")
    parser.add_argument("--config", required=True)
    parser.add_argument("--connection-config", required=True)
    args = parser.parse_args()
    raise SystemExit(run(args.config, args.connection_config))


if __name__ == "__main__":
    main()
