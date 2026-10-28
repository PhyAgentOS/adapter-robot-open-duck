import pytest
from forge_msgs import JointCommand
from robots_open_duck.config import JOINT_ORDER, OpenDuckNodeConfig
from robots_open_duck.driver import OpenDuckDriver
from fake_io import FakeFeetechIO
from robots_open_duck.sdk import OpenDuckSDK


def _connected_driver(action=True):
    offsets = dict.fromkeys(JOINT_ORDER, 0.0)
    offsets["left_hip_yaw"] = 0.1
    cfg = OpenDuckNodeConfig(backend="real", enable_action=action, offsets=offsets)
    io = FakeFeetechIO([0.0]*14)
    driver = OpenDuckDriver(cfg, sdk=OpenDuckSDK(cfg,io))
    driver.connect()
    return driver,io


def test_sdk_applies_offsets_in_each_direction():
    driver,io=_connected_driver()
    assert driver.get_state().position[0] == pytest.approx(-.1)
    driver.set_command(JointCommand(name=[JOINT_ORDER[0]],position=[.2]))
    assert io.writes[-1][0][0] == 20
    assert io.writes[-1][1][0] == pytest.approx(.3)


def test_sparse_targets_hold_previous_values():
    driver,io=_connected_driver()
    driver.set_command(JointCommand(name=[JOINT_ORDER[0]],position=[.2]))
    driver.set_command(JointCommand(name=[JOINT_ORDER[1]],position=[-.1]))
    assert io.writes[-1][1][0] == pytest.approx(.3)
    assert io.writes[-1][1][1] == pytest.approx(-.1)


def test_invalid_command_writes_nothing():
    driver,io=_connected_driver()
    with pytest.raises(ValueError):
        driver.set_command(JointCommand(name=[JOINT_ORDER[0]],position=[.2],velocity=[1.]))
    assert io.writes == []


def test_read_fault_disconnects_sdk():
    driver,io=_connected_driver()
    io.fail_read=True
    with pytest.raises(OSError): driver.get_state()
    assert not driver.sdk.connected


def test_read_only_blocks_motion():
    driver,io=_connected_driver(False)
    with pytest.raises(PermissionError):
        driver.set_command(JointCommand(name=[JOINT_ORDER[0]],position=[.1]))
    assert not io.writes


def test_stop_latches_motion_until_reconnect():
    driver,io=_connected_driver()
    driver.stop()
    with pytest.raises(RuntimeError):
        driver.set_command(JointCommand(name=[JOINT_ORDER[0]],position=[.1]))
    driver.disconnect(); driver.connect()
    driver.set_command(JointCommand(name=[JOINT_ORDER[0]],position=[.1]))


def test_write_failure_cleans_up_and_does_not_continue():
    driver,io=_connected_driver()
    io.fail_write=True
    with pytest.raises(OSError):
        driver.set_command(JointCommand(name=[JOINT_ORDER[0]],position=[.1]))
    assert not driver.sdk.connected
    assert io.closed


def test_limits_are_clipped_before_write():
    driver,io=_connected_driver()
    driver.set_command(JointCommand(name=[JOINT_ORDER[0]],position=[2.0]))
    assert io.writes[-1][1][0] == pytest.approx(.523599+.1)


def test_disconnect_disables_torque_after_actions():
    driver,io=_connected_driver()
    driver.set_command(JointCommand(name=[JOINT_ORDER[0]],position=[.1]))
    assert io.enabled
    driver.disconnect()
    assert not io.enabled and io.closed


def test_short_or_nan_feedback_is_rejected_and_released():
    for failure in ("missing_feedback","nan_feedback"):
        cfg=OpenDuckNodeConfig(backend="real", offsets=dict.fromkeys(JOINT_ORDER, 0.0))
        io=FakeFeetechIO(); setattr(io,failure,True); sdk=OpenDuckSDK(cfg,io)
        with pytest.raises(RuntimeError): sdk.connect()
        assert not sdk.connected and io.closed
