"""Open Duck Mini v2 configuration and canonical actuator specification."""
from __future__ import annotations

from dataclasses import dataclass
import math
import os
from pathlib import Path
from typing import Any, Mapping

import yaml


@dataclass(frozen=True)
class ActuatorSpec:
    name: str
    motor_id: int
    lower: float
    upper: float
    home: float


_ROWS = [
    ("left_hip_yaw",20,-.523599,.523599,.002),("left_hip_roll",21,-.436332,.436332,.053),
    ("left_hip_pitch",22,-1.221730,.523599,-.630),("left_knee",23,-1.570796,1.570796,1.368),
    ("left_ankle",24,-1.570796,1.570796,-.784),("neck_pitch",30,-.349066,1.134464,0.),
    ("head_pitch",31,-.785398,.785398,0.),("head_yaw",32,-2.792527,2.792527,0.),
    ("head_roll",33,-.523599,.523599,0.),("right_hip_yaw",10,-.523599,.523599,-.003),
    ("right_hip_roll",11,-.436332,.436332,-.065),("right_hip_pitch",12,-.523599,1.221730,.635),
    ("right_knee",13,-1.570796,1.570796,1.379),("right_ankle",14,-1.570796,1.570796,-.796),
]
OPEN_DUCK_ACTUATOR_SPECS = tuple(ActuatorSpec(*r) for r in _ROWS)
JOINT_ORDER = tuple(s.name for s in OPEN_DUCK_ACTUATOR_SPECS)
MOTOR_IDS = tuple(s.motor_id for s in OPEN_DUCK_ACTUATOR_SPECS)
HOME = tuple(s.home for s in OPEN_DUCK_ACTUATOR_SPECS)

def asset_directory() -> Path:
    """Resolve model assets in a source checkout."""
    checkout_assets = Path(__file__).resolve().parents[2] / "assets"
    if not checkout_assets.is_dir():
        raise FileNotFoundError(
            "Open Duck model assets are not included in the installed Python package; "
            "use a source checkout with its root assets/ directory."
        )
    return checkout_assets


@dataclass(frozen=True)
class OpenDuckNodeConfig:
    backend: str = "ssh"
    port: str = "/dev/ttyACM0"
    baudrate: int = 1_000_000
    offsets: Mapping[str, float] | None = None
    enable_action: bool = False
    debug: bool = False
    ssh_target: str | None = None
    remote_python: str | None = None
    remote_runtime_dir: str | None = None
    duck_config_path: str | None = None
    rpc_timeout_seconds: float = 3.0
    command_timeout_seconds: float = 1.0

    def __post_init__(self) -> None:
        if self.backend not in {"real", "ssh"}:
            raise ValueError("backend must be 'real' or 'ssh'")
        if not isinstance(self.port, str) or not self.port.strip():
            raise ValueError("port must be a non-empty string")
        if isinstance(self.baudrate, bool) or not isinstance(self.baudrate, int) or self.baudrate <= 0:
            raise ValueError("baudrate must be a positive integer")
        if type(self.enable_action) is not bool or type(self.debug) is not bool:
            raise ValueError("enable_action and debug must be booleans")
        offsets = dict(self.offsets or {})
        unknown = set(offsets) - set(JOINT_ORDER)
        if unknown:
            raise ValueError(f"unknown offset joints: {sorted(unknown)}")
        for key, value in offsets.items():
            if isinstance(value, bool) or not isinstance(value, (int,float)) or not math.isfinite(value):
                raise ValueError(f"offset for {key} must be a finite number")
        if self.backend == "real" and set(offsets) != set(JOINT_ORDER):
            raise ValueError("real backend requires an explicit offset for all 14 joints")
        if self.backend == "ssh" and offsets:
            raise ValueError("ssh backend reads calibration from the Pi; omit offsets")
        for field in ("ssh_target", "remote_python", "remote_runtime_dir", "duck_config_path"):
            value = getattr(self, field)
            if value is None and self.backend != "ssh":
                continue
            if not isinstance(value, str) or not value.strip() or "\n" in value or "\0" in value:
                raise ValueError(f"{field} must be configured as a non-empty single-line string")
        if self.ssh_target and self.ssh_target.startswith("-"):
            raise ValueError("ssh_target must not start with '-'")
        for field in ("rpc_timeout_seconds", "command_timeout_seconds"):
            value = getattr(self, field)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
                raise ValueError(f"{field} must be positive and finite")
        object.__setattr__(self, "offsets", offsets)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "OpenDuckNodeConfig":
        allowed = set(cls.__dataclass_fields__)
        extra = set(data) - allowed
        if extra:
            raise ValueError(f"unknown configuration fields: {sorted(extra)}")
        return cls(**dict(data))

    @classmethod
    def from_yaml_path(cls, path: str | Path) -> "OpenDuckNodeConfig":
        with Path(path).expanduser().open(encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        if not isinstance(data, Mapping):
            raise ValueError("configuration YAML must contain a mapping")
        return cls.from_dict(data)


def load_config(path: str | Path | None = None, *, inline: Mapping[str, Any] | None = None) -> OpenDuckNodeConfig:
    """Choose exactly one source: inline, explicit path, or environment."""
    if inline is not None:
        return OpenDuckNodeConfig.from_dict(inline)
    selected = path or os.getenv("OPEN_DUCK_NODE_CONFIG")
    if selected is None:
        raise ValueError(
            "未找到配置。请通过 --config 指定现场配置，"
            "或设置 OPEN_DUCK_NODE_CONFIG 环境变量。"
        )
    return OpenDuckNodeConfig.from_yaml_path(selected)
