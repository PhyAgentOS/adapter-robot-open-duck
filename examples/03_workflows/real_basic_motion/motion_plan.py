"""Finite joint trajectories shared by the PC action source and offline checks."""
import math

from robots_open_duck.config import HOME, JOINT_ORDER, OPEN_DUCK_ACTUATOR_SPECS

AMPLITUDE = 0.30


class MotionPlan:
    def __init__(self, initial):
        if len(initial) != len(HOME):
            raise ValueError("expected all 14 feedback positions")
        self.segments = []
        targets = [float(value) for value in initial]
        if not all(math.isfinite(value) for value in targets):
            raise ValueError("expected finite feedback positions")
        elapsed = 0.0

        def append(index, goal, duration, label):
            nonlocal elapsed, targets
            end = targets.copy()
            end[index] = goal
            self.segments.append((elapsed, duration, targets.copy(), end, label))
            elapsed += duration
            targets = end

        # Recover joints outside the operating limits first (e.g. a drooping head).
        # Never clip the starting pose: doing so would create a target jump.
        order = sorted(range(len(HOME)), key=lambda index: (
            OPEN_DUCK_ACTUATOR_SPECS[index].lower <= targets[index]
            <= OPEN_DUCK_ACTUATOR_SPECS[index].upper
        ))
        for index in order:
            spec = OPEN_DUCK_ACTUATOR_SPECS[index]
            # Smoothstep's maximum derivative is 1.5; cap peak speed at 0.3 rad/s.
            append(index, HOME[index], max(1.0, 1.5 * abs(HOME[index] - targets[index]) / 0.3),
                   f"HOME: {spec.name}")
        self.home_duration = elapsed
        for index, name in enumerate(JOINT_ORDER):
            spec = OPEN_DUCK_ACTUATOR_SPECS[index]
            for offset in (-AMPLITUDE, AMPLITUDE, 0.0):
                target = min(spec.upper, max(spec.lower, HOME[index] + offset))
                actual_offset = target - HOME[index]
                append(index, target, 1.5, f"{name}: HOME {actual_offset:+.3f} rad")
                append(index, target, 0.3, f"{name}: hold")
        self.duration = elapsed + 2.0

    def sample(self, elapsed):
        for start, duration, initial, target, label in self.segments:
            if elapsed < start + duration:
                fraction = max(0.0, (elapsed - start) / duration)
                blend = fraction * fraction * (3.0 - 2.0 * fraction)
                return [a + (b - a) * blend for a, b in zip(initial, target)], label
        return list(HOME), "Final HOME"
