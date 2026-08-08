"""bowling/lane.py — the simplified roll physics: lateral aim position and
release power (from a time-based meter) determine how many pins fall.

Deliberately not a per-pin collision simulation ("simple physics" per spec).
The important property: outcome is deterministic given (aim, power), but
`power` comes from a *time-based* meter the player has to time a second
button press against — so parking in one spot doesn't reliably reproduce a
strike; hitting the strike window takes real timing.
"""

PIN_COUNT = 10

# lane fraction: -1.0 = left gutter, 0.0 = center, +1.0 = right gutter
POCKET_OFFSET = -0.15          # where a strike-line ball needs to be aimed
STRIKE_AIM_TOLERANCE = 0.06    # how close to the pocket counts as "on line"

# release power (0.0-1.0) window that can yield a strike. Originally 10%
# wide (0.85-0.95); halved to 5%, same center, to raise the difficulty.
STRIKE_WINDOW = (0.875, 0.925)
_WINDOW_CENTER = (STRIKE_WINDOW[0] + STRIKE_WINDOW[1]) / 2
_POWER_FALLOFF = 0.45  # how far from the window center power_factor hits 0
                        # (both too weak AND too strong are penalized)

POWER_METER_PERIOD = 1.4       # seconds for one full 0 -> 1 -> 0 sweep


def power_meter_value(elapsed):
    """The power bar's fill level (0.0-1.0) after `elapsed` seconds of
    charging — a triangle wave, so it rises then falls repeatedly until the
    player releases it."""
    phase = (elapsed % POWER_METER_PERIOD) / POWER_METER_PERIOD
    return 1.0 - abs(phase * 2 - 1)


def resolve_roll(aim_offset, power, bumpers=True):
    """aim_offset: -1..1 lateral release position. power: 0..1 release
    power. Returns the number of pins knocked down (0-10)."""
    if bumpers:
        aim_offset = max(-1.0, min(1.0, aim_offset))
    elif abs(aim_offset) > 1.0:
        return 0  # true gutter ball — only possible with bumpers off

    on_pocket = abs(aim_offset - POCKET_OFFSET) <= STRIKE_AIM_TOLERANCE
    in_window = STRIKE_WINDOW[0] <= power <= STRIKE_WINDOW[1]
    if on_pocket and in_window:
        return PIN_COUNT

    accuracy = max(0.0, 1 - abs(aim_offset - POCKET_OFFSET) / 0.9)
    # power_factor peaks at the strike window's center and falls off in both
    # directions, so overpowering the throw is penalized same as underpowering
    # it — previously anything above ~70% power got full credit, which made
    # a near-max-power throw knock down 9 pins almost regardless of timing
    power_factor = max(0.0, 1 - abs(power - _WINDOW_CENTER) / _POWER_FALLOFF)
    pins = round(PIN_COUNT * accuracy * power_factor)
    # a strike is reserved for the on-pocket + timed-window combo above, so
    # perfect aim alone (without hitting the window) can't also reach 10
    return min(pins, PIN_COUNT - 1)
