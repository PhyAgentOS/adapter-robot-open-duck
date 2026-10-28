"""Fake Feetech IO for offline SDK adapter validation; not a physics simulator."""
from __future__ import annotations
from typing import Sequence
from robots_open_duck.config import MOTOR_IDS


class FakeFeetechIO:
    def __init__(self, positions: Sequence[float] | None = None):
        self.positions = list(positions or [0.0]*14)
        self.writes: list[tuple[list[int],list[float]]] = []
        self.enabled = False
        self.closed = False
        self.fail_read = False
        self.fail_write = False
        self.nan_feedback = False
        self.missing_feedback = False
    def read_present_position(self, ids: list[int]):
        if self.fail_read: raise OSError("injected read failure")
        values = [self.positions[MOTOR_IDS.index(i)] for i in ids]
        if self.missing_feedback: return values[:-1]
        if self.nan_feedback: values[0] = float("nan")
        return values
    def write_goal_position(self, ids: list[int], values: list[float]):
        if self.fail_write: raise OSError("injected write failure")
        self.writes.append((list(ids),list(values)))
        for i,v in zip(ids,values): self.positions[MOTOR_IDS.index(i)] = v
    def disable_torque(self, ids: list[int]): self.enabled = False
    def enable_torque(self, ids: list[int]): self.enabled = True
    def close(self): self.closed = True
