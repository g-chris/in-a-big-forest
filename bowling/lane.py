"""bowling/lane.py — the roll-outcome logic: a moving green/gold zone on
the power bar, timed against a release marker driven by a time-based meter.

Pin count is entirely bar-precision-driven now — aim only gates whether the
throw counts at all (see bowling/scene.py's alignment check), it no longer
affects which/how many pins fall. The important property carries over from
before: outcome is deterministic given (power, zone position), but the zone
moves on its own clock independent of the charge timer, so reading its live
position for real is the only way to time a release well — no memorizable
pattern.
"""

PIN_COUNT = 10

ZONE_SPEED_MIN = 0.8   # bar-widths/sec at 10 pins standing (easiest: full rack)
ZONE_SPEED_MAX = 2.1   # bar-widths/sec at 1 pin standing (hardest: spare pick)
GREEN_WIDTH = 0.30      # fraction of the bar — "slightly bigger" than the old 0.05 window
GOLD_WIDTH = 0.06       # fraction of the bar — inner guaranteed-clear zone
MAX_GREEN_PINS = 9      # pins knocked just outside gold (gold itself = clear everything standing)
MIN_GREEN_PINS = 1      # pins knocked at the very edge of green

GUTTER_NOT_ALIGNED = "not_aligned"
GUTTER_MISS = "miss"
HIT_GOLD = "gold"
HIT_GREEN = "green"

POWER_METER_PERIOD = 2       # seconds for one full 0 -> 1 -> 0 sweep


def power_meter_value(elapsed):
    """The power bar's release-marker position (0.0-1.0) after `elapsed`
    seconds of charging — a triangle wave, so it rises then falls repeatedly
    until the player releases it."""
    phase = (elapsed % POWER_METER_PERIOD) / POWER_METER_PERIOD
    return 1.0 - abs(phase * 2 - 1)


def zone_speed(pins_standing):
    """The green/gold zone's movement speed (bar-widths/sec) — slower with
    more pins standing (10 = easiest, the full rack), fastest picking up a
    single pin."""
    pins_standing = max(1, min(PIN_COUNT, pins_standing))
    t = (pins_standing - 1) / (PIN_COUNT - 1)  # 0 at 1 pin, 1 at 10 pins
    return ZONE_SPEED_MAX + (ZONE_SPEED_MIN - ZONE_SPEED_MAX) * t


def zone_center(elapsed, speed, half_width):
    """The moving zone's center (0.0-1.0 bar fraction) at `elapsed` seconds
    — a triangle wave, same shape as power_meter_value, parameterized by
    speed so its period isn't fixed, and kept fully on-bar by only
    traveling within [half_width, 1-half_width]."""
    travel_min, travel_max = half_width, 1.0 - half_width
    travel_range = travel_max - travel_min
    period = 2.0 * travel_range / speed
    phase = (elapsed % period) / period
    return travel_min + travel_range * (1.0 - abs(phase * 2 - 1))


def resolve_bar_roll(power, zone_center_value, pins_standing, aligned, green_half_width, gold_half_width):
    """power: the release marker's position (0..1) at the moment of release.
    zone_center_value: the moving zone's center (0..1) at that same moment.
    Returns (outcome, pins_knocked).

    Strike/spare aren't special-cased here — hitting gold always clears
    every pin currently standing, and the existing scoring already turns
    that into a strike (10 standing, first throw) or a spare (fewer
    standing, second throw) once the count is recorded.
    """
    if not aligned:
        return GUTTER_NOT_ALIGNED, 0

    dist = abs(power - zone_center_value)
    if dist <= gold_half_width:
        return HIT_GOLD, pins_standing
    if dist <= green_half_width:
        t = (dist - gold_half_width) / (green_half_width - gold_half_width)
        pins = round(MAX_GREEN_PINS + (MIN_GREEN_PINS - MAX_GREEN_PINS) * t)
        return HIT_GREEN, min(pins, pins_standing)
    return GUTTER_MISS, 0
