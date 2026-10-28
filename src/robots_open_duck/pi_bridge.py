"""Standalone Python 3.10 Pi receiver, transported as source over authenticated SSH.

Stdout is reserved for JSON RPC. A read-only session never changes torque or gains.
"""
from __future__ import annotations

import fcntl
import json
import math
import os
from pathlib import Path
import select
import signal
import sys
import time

_RPC_OUTPUT = None


class BridgeSession:
    def __init__(self, hwi, options):
        self.hwi = hwi
        self.specs = options["specs"]
        self.names = [spec["name"] for spec in self.specs]
        self.ids = [spec["motor_id"] for spec in self.specs]
        self.offsets = dict(hwi.joints_offsets)
        self.allowed = options["enable_action"]
        self.timeout = options["command_timeout_seconds"]
        self.armed = False
        self.stopped = False
        self.last_write = None
        self.targets = None
        if list(hwi.joints) != self.names or list(hwi.joints.values()) != self.ids:
            raise ValueError("Runtime joint mapping does not match Forge")
        if set(self.offsets) != set(self.names) or not all(
            math.isfinite(float(value)) for value in self.offsets.values()
        ):
            raise ValueError("duck_config.json needs all 14 finite joints_offsets")
        if any(abs(hwi.init_pos[s["name"]] - s["home"]) > 1e-6 for s in self.specs):
            raise ValueError("Runtime initial pose does not match Forge HOME")

    def metadata(self):
        return {"joint_order": self.names, "motor_ids": self.ids,
                "home": [self.hwi.init_pos[name] for name in self.names],
                "offsets": self.offsets}

    def read(self):
        values = self.hwi.io.read_present_position(self.ids)
        if values is None or len(values) != len(self.ids):
            raise RuntimeError("invalid motor feedback length")
        values = [float(value) for value in values]
        if not all(math.isfinite(value) for value in values):
            raise RuntimeError("non-finite motor feedback")
        return values

    def disable(self):
        # A read-only connection must not release torque held by another program.
        if self.armed:
            self.hwi.turn_off()
            self.armed = False
        self.stopped = True

    def watchdog(self, now=None):
        now = time.monotonic() if now is None else now
        if self.armed and now - self.last_write > self.timeout:
            self.disable()
            raise TimeoutError("motor command watchdog expired; torque disabled")

    def handle(self, request):
        self.watchdog()
        if request.get("ids") != self.ids:
            raise ValueError("expected canonical 14 motor IDs")
        op = request["op"]
        if op == "read":
            return self.read()
        if op == "disable":
            self.disable()
            return None
        if not self.allowed:
            raise PermissionError("actions are disabled by PC configuration")
        if self.stopped:
            raise RuntimeError("stop is latched; reconnect to resume")
        if op == "enable":
            if self.armed:
                return None
            measured = self.read()
            self.armed = True
            self.last_write = time.monotonic()
            # Stage measured positions individually before enabling torque.
            # The local Runtime avoids the 14-motor startup position packet.
            for motor_id, value in zip(self.ids, measured):
                self.hwi.io.write_goal_position([motor_id], [value])
            kps = [30] * len(self.ids)
            for index, name in enumerate(self.names):
                if name in {"neck_pitch", "head_pitch", "head_yaw", "head_roll"}:
                    kps[index] = 8
            self.hwi.set_kps(kps)
            self.hwi.set_kds([0] * len(self.ids))
            enable = getattr(self.hwi.io, "enable_torque", None)
            if enable is not None:
                enable(self.ids)
            self.targets = measured
            self.last_write = time.monotonic()
            return None
        if op != "write":
            raise ValueError("unknown bridge operation")
        if not self.armed:
            raise RuntimeError("torque has not been enabled")
        values = request.get("values")
        if not isinstance(values, list) or len(values) != len(self.ids):
            raise ValueError("expected 14 target positions")
        values = [float(value) for value in values]
        for spec, value, previous in zip(self.specs, values, self.targets):
            logical = value - self.offsets[spec["name"]]
            previous_logical = previous - self.offsets[spec["name"]]
            # Startup may be outside the model's operating range. Permit hold
            # or inward recovery only; never extend that range farther outward.
            lower = min(spec["lower"], previous_logical)
            upper = max(spec["upper"], previous_logical)
            if not math.isfinite(value) or not lower - 1e-9 <= logical <= upper + 1e-9:
                raise ValueError("target outside joint limits: " + spec["name"])
            if abs(value - previous) > 0.08:
                raise ValueError(
                    f"position step exceeds 0.08 rad: {spec['name']} "
                    f"({previous_logical:.6f} -> {logical:.6f} rad)"
                )
        # Only changed joints are written. Other servos keep their last target.
        for motor_id, value, previous in zip(self.ids, values, self.targets):
            if abs(value - previous) > 1e-7:
                self.hwi.io.write_goal_position([motor_id], [value])
        self.targets = values
        self.last_write = time.monotonic()
        return None


def reply(message):
    print(json.dumps(message, allow_nan=False), file=_RPC_OUTPUT, flush=True)


def main():
    options = json.loads(sys.argv[1])
    runtime_dir = Path(options["runtime_dir"]).expanduser()
    config_path = Path(options["duck_config_path"]).expanduser()
    port = os.path.realpath(options["port"])
    config_data = json.loads(config_path.read_text())
    offsets = config_data.get("joints_offsets", {})
    expected = {spec["name"] for spec in options["specs"]}
    if set(offsets) != expected:
        raise ValueError("Pi calibration is missing joint offsets")
    # One bridge owns the serial bus; refuse another process already using it.
    lock_path = "/tmp/open_duck_forge_" + Path(port).name + ".lock"
    with open(lock_path, "a") as lock_file:
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        for process_dir in Path("/proc").iterdir():
            if not process_dir.name.isdigit() or process_dir.name == str(os.getpid()):
                continue
            try:
                for fd in (process_dir / "fd").iterdir():
                    try:
                        if os.path.realpath(fd) == port:
                            raise RuntimeError("serial port is already open by PID " + process_dir.name)
                    except (PermissionError, FileNotFoundError):
                        continue
            except (PermissionError, FileNotFoundError):
                continue
        sys.path.insert(0, str(runtime_dir / "mini_bdx_runtime"))
        from mini_bdx_runtime.duck_config import DuckConfig
        from mini_bdx_runtime.rustypot_position_hwi import HWI
        hwi = HWI(DuckConfig(config_json_path=str(config_path)), options["port"])
        session = BridgeSession(hwi, options)
        def interrupted(signum, frame):
            raise KeyboardInterrupt
        for signum in (signal.SIGTERM, signal.SIGHUP, signal.SIGINT):
            signal.signal(signum, interrupted)
        try:
            reply({"ok": True, "result": session.metadata()})
            while True:
                session.watchdog()
                readable, _, _ = select.select([sys.stdin], [], [], 0.1)
                if not readable:
                    continue
                line = sys.stdin.readline()
                if not line:
                    break
                request = json.loads(line)
                try:
                    result = session.handle(request)
                    reply({"id": request.get("id"), "ok": True, "result": result})
                except Exception as error:
                    session.disable()
                    reply({"id": request.get("id"), "ok": False, "error": str(error)})
                    break
        finally:
            session.disable()


if __name__ == "__main__":
    # Rustypot's native code writes directly to fd 1. redirect_stdout only
    # changes Python's sys.stdout, so reserve a duplicate of the SSH output
    # exclusively for RPC, then send fd 1 (including Rust/C output) to stderr.
    sys.stdout.flush()
    with os.fdopen(os.dup(sys.stdout.fileno()), "w", buffering=1, encoding="utf-8") as _RPC_OUTPUT:
        os.dup2(sys.stderr.fileno(), sys.stdout.fileno())
        try:
            main()
        except (Exception, KeyboardInterrupt) as error:
            reply({"ok": False, "error": str(error) or "bridge interrupted"})
            sys.exit(1)
