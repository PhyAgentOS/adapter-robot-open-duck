"""Open Duck Mini v2 Forge robot package. Importing has no hardware side effects."""
from .config import HOME, JOINT_ORDER, MOTOR_IDS, OPEN_DUCK_ACTUATOR_SPECS, OpenDuckNodeConfig, asset_directory, load_config

__all__ = [
    "HOME", "JOINT_ORDER", "MOTOR_IDS", "OPEN_DUCK_ACTUATOR_SPECS",
    "OpenDuckNodeConfig", "OpenDuckSDK", "OpenDuckDriver",
    "asset_directory", "load_config",
]


def __getattr__(name: str):
    if name == "OpenDuckDriver":
        from .driver import OpenDuckDriver
        return OpenDuckDriver
    if name == "OpenDuckSDK":
        from .sdk import OpenDuckSDK
        return OpenDuckSDK
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
