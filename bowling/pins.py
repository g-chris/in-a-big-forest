"""bowling/pins.py — individual pin bodies for the lane rack.

Still "simple physics" — no rigid-body simulation. `bowling.lane.resolve_bar_roll`
stays the sole authority on *how many* pins a roll knocks down (that's what
keeps the moving-zone timing mechanic meaningful); this module only picks
*which* standing pins fall — the ones closest to the ball's line — and gives
knockdowns and near-miss neighbors a small, physical-feeling reaction: a
pin that's hit topples over a short animation instead of vanishing, and any
pin standing close enough to a falling one gets a brief sideways nudge, so
contact reads without a full collision solve.
"""

import math

PIN_HEIGHT = 22
PIN_SPACING = 22
FALL_DURATION = 0.45
NUDGE_RADIUS = 26
NUDGE_DURATION = 0.2
NUDGE_DISTANCE = 4


class Pin:
    def __init__(self, x, y):
        self.home = (x, y)
        self.standing = True
        self.fall_t = 0.0    # 0..1 progress through the fall animation
        self.fall_dir = 1    # +1/-1, which way it topples
        self.nudge_t = 0.0   # 0..1 remaining progress of a sideways nudge
        self.nudge_dx = 0.0

    def knock_down(self, fall_dir):
        self.standing = False
        self.fall_t = 0.0
        self.fall_dir = fall_dir

    def nudge(self, dx):
        self.nudge_t = 1.0
        self.nudge_dx = dx

    def update(self, dt):
        if not self.standing and self.fall_t < 1.0:
            self.fall_t = min(1.0, self.fall_t + dt / FALL_DURATION)
        if self.nudge_t > 0.0:
            self.nudge_t = max(0.0, self.nudge_t - dt / NUDGE_DURATION)

    def draw_pos_and_scale(self):
        """Where to draw this pin right now, and how tall relative to
        PIN_HEIGHT (shrinks toward 0 as it finishes toppling)."""
        x, y = self.home
        if self.nudge_t > 0.0:
            x += self.nudge_dx * self.nudge_t
        if not self.standing:
            x += self.fall_dir * 13 * self.fall_t
            y += 7 * self.fall_t
            return (x, y), max(0.0, 1.0 - 0.8 * self.fall_t)
        return (x, y), 1.0


def build_rack(center_x, base_y, row_spacing=22, pin_spacing=PIN_SPACING):
    """A standard 4-row (1-2-3-4) triangle, headpin first — the order
    knockdown-selection walks front-to-back when picking which pins fall."""
    positions = []
    for row_i, count in enumerate([1, 2, 3, 4]):
        row_y = base_y - row_i * row_spacing
        start_x = center_x - (count - 1) * pin_spacing / 2
        for slot in range(count):
            positions.append((start_x + slot * pin_spacing, row_y))
    return [Pin(x, y) for x, y in positions]


def apply_hit(rack, impact_x, pins_to_knock):
    """Knock down `pins_to_knock` standing pins nearest the ball's line
    (impact_x), then give nearby still-standing pins a small nudge so the
    hit reads as physical contact rather than pins independently vanishing.
    """
    standing = [p for p in rack if p.standing]
    standing.sort(key=lambda p: abs(p.home[0] - impact_x))
    to_knock = standing[:pins_to_knock]

    for pin in to_knock:
        fall_dir = 1 if pin.home[0] >= impact_x else -1
        pin.knock_down(fall_dir)

    for pin in to_knock:
        for other in standing:
            if other in to_knock:
                continue
            dx = other.home[0] - pin.home[0]
            dy = other.home[1] - pin.home[1]
            dist = math.hypot(dx, dy)
            if 0 < dist <= NUDGE_RADIUS:
                push = NUDGE_DISTANCE * (1 - dist / NUDGE_RADIUS)
                other.nudge(push if dx >= 0 else -push)
