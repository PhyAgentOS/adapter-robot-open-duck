"""Open Duck CLI and standard Forge Dora node entry point."""
from __future__ import annotations
import logging
import json
import os
from dataclasses import replace
import typer
from .config import OpenDuckNodeConfig, load_config
from .driver import OpenDuckDriver

app = typer.Typer(
    name="robots-open-duck", no_args_is_help=False, add_completion=False,
    help="Open Duck Forge 节点与设备工具；默认运行 Dora 节点。",
)

def run_node(config: OpenDuckNodeConfig, *, finite: bool = False) -> int:
    from forge_robot.node_runner import run_dora_robot_node
    if os.getenv("OPEN_DUCK_READ_ONLY") == "1":
        config = replace(config, enable_action=False)
    driver = OpenDuckDriver(config)
    try:
        driver.connect()
        if finite:
            from .node import run_finite_node
            print("Connected; calibration and joint mapping verified", flush=True)
            return run_finite_node(driver)
        return run_dora_robot_node(driver,debug=config.debug)
    finally: driver.disconnect()

def load_node_config(explicit_path: str | None) -> OpenDuckNodeConfig:
    """Resolve supported Dora env config before CLI, environment, and defaults."""
    inline=os.getenv("OPEN_DUCK_DATAFLOW_CONFIG")
    if inline is not None:
        data=json.loads(inline)
        if not isinstance(data,dict): raise ValueError("OPEN_DUCK_DATAFLOW_CONFIG must be a JSON object")
        return load_config(inline=data)
    dataflow_path=os.getenv("OPEN_DUCK_DATAFLOW_CONFIG_PATH")
    if dataflow_path:
        return load_config(dataflow_path)
    return load_config(explicit_path)

@app.callback(invoke_without_command=True)
def cli(ctx: typer.Context, config: str | None = typer.Option(None,"--config",help="YAML config path"), version: bool = typer.Option(False,"--version")):
    if version:
        from importlib.metadata import version as package_version
        try: typer.echo(package_version("open-duck"))
        except Exception: typer.echo("0.1.0")
        raise typer.Exit()
    if ctx.invoked_subcommand is None:
        raise typer.Exit(run_node(load_node_config(config)))

@app.command("watch-state")
def watch_state(config: str | None = typer.Option(None,"--config")):
    """读取一帧状态并断开，不启用动作。"""
    from .device_tools import read_state
    cfg = replace(load_node_config(config), enable_action=False)
    typer.echo(read_state(OpenDuckDriver(cfg)).model_dump_json())

@app.command("run")
def run(
    config: str | None = typer.Option(None, "--config", help="YAML 配置文件路径"),
    finite: bool = typer.Option(False, "--finite", help="启用有限工作流的 finish 输入"),
):
    """运行正式 Forge/Dora 节点。"""
    raise typer.Exit(run_node(load_node_config(config), finite=finite))

@app.command("rl")
def run_rl(
    config: str = typer.Option(..., "--config", help="Protected RL profile YAML"),
    connection_config: str = typer.Option(
        ..., "--connection-config", help="User-editable SSH connection YAML"
    ),
):
    """Run the native Open Duck RL walking driver."""
    from .rl_main import run as run_rl_node

    raise typer.Exit(run_rl_node(config, connection_config))

@app.command("move-home")
def move_home(config: str | None = typer.Option(None, "--config")):
    """平滑归位 HOME；配置须允许动作，退出时释放本次扭矩。"""
    from .device_tools import move_home as move
    driver = OpenDuckDriver(load_node_config(config))
    try:
        driver.connect()
        typer.echo(move(driver).model_dump_json())
    finally:
        driver.disconnect()

@app.command("move-joint")
def move_joint(
    name: str = typer.Argument(..., help="关节名称"),
    position: float = typer.Argument(..., help="绝对目标角度，rad"),
    config: str | None = typer.Option(None, "--config"),
):
    """平滑移动单关节；其他关节保持目标，退出时释放本次扭矩。"""
    from .device_tools import move_joint as move
    driver = OpenDuckDriver(load_node_config(config))
    try:
        driver.connect()
        typer.echo(move(driver, name, position).model_dump_json())
    finally:
        driver.disconnect()

def main() -> None:
    logging.basicConfig(level=logging.INFO)
    app()

if __name__ == "__main__": main()
