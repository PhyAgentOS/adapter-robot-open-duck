import json
import pytest
from robots_open_duck.config import JOINT_ORDER, OpenDuckNodeConfig, asset_directory, load_config

SSH_CONFIG = {
    "backend": "ssh", "ssh_target": "test.invalid",
    "remote_python": "python3", "remote_runtime_dir": "/test/runtime",
    "duck_config_path": "/test/duck.json",
}

def test_missing_config_requires_explicit_source(monkeypatch):
    monkeypatch.delenv("OPEN_DUCK_NODE_CONFIG", raising=False)
    with pytest.raises(ValueError, match="未找到配置"):
        load_config()

def test_real_requires_complete_offsets():
    with pytest.raises(ValueError): OpenDuckNodeConfig(backend="real")

def test_unknown_keys_rejected():
    with pytest.raises(ValueError): OpenDuckNodeConfig.from_dict({**SSH_CONFIG, "mystery": 1})

def test_order_is_canonical_14():
    assert len(JOINT_ORDER)==14 and JOINT_ORDER[0]=="left_hip_yaw" and JOINT_ORDER[-1]=="right_ankle"

def test_import_does_not_load_rustypot():
    import subprocess,sys
    code="import sys; import robots_open_duck; import robots_open_duck.main; assert 'rustypot' not in sys.modules"
    subprocess.run([sys.executable,"-c",code],check=True)

def test_model_asset_is_resolvable():
    assert (asset_directory()/"mjcf"/"open_duck_fixed.xml").is_file()

def test_dataflow_inline_precedes_cli_config(tmp_path,monkeypatch):
    from robots_open_duck.main import load_node_config
    p=tmp_path/"cli.yaml";p.write_text(json.dumps({**SSH_CONFIG, "enable_action": True}))
    monkeypatch.setenv("OPEN_DUCK_DATAFLOW_CONFIG",json.dumps({**SSH_CONFIG, "enable_action": False}))
    assert load_node_config(str(p)).enable_action is False

def test_dataflow_config_path_precedes_cli_config(tmp_path,monkeypatch):
    from robots_open_duck.main import load_node_config
    cli=tmp_path/"cli.yaml"; cli.write_text(json.dumps({**SSH_CONFIG, "enable_action": False}))
    dataflow=tmp_path/"dataflow.yaml"; dataflow.write_text(json.dumps({**SSH_CONFIG, "enable_action": True}))
    monkeypatch.delenv("OPEN_DUCK_DATAFLOW_CONFIG",raising=False)
    monkeypatch.setenv("OPEN_DUCK_DATAFLOW_CONFIG_PATH",str(dataflow))
    assert load_node_config(str(cli)).enable_action is True
