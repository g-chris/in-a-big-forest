"""fish_icon.py — the classic single-stroke fish silhouette: an almond body,
a notched tail, one dorsal fin, and a small mouth mark. Shared by the actual
fish in the fishing mini-game and the fishing hut's sign icon.
"""

import math

import pygame

OUTLINE_COLOR = (0, 0, 0)


def draw_fish(surface, x, y, length, color, wiggle=0.0, line_width=2):
    """Draw a fish centered at (x, y), `length` pixels nose-to-tail-tip.
    `wiggle` (radians) bends the tail sideways for a swimming animation."""
    half = length / 2
    body_h = length * 0.5
    tail_bend = math.sin(wiggle) * body_h * 0.3

    # one continuous outline: nose -> over the back -> out to the tail's
    # top point -> in to the tail notch -> out to the tail's bottom point
    # -> back along the belly -> nose. No retraced segments.
    nose = (x + half, y)
    back = (x + half * 0.2, y - body_h / 2)
    tail_root_top = (x - half * 0.45, y - body_h * 0.18)
    tail_tip_top = (x - half, y - body_h * 0.5 + tail_bend)
    tail_notch = (x - half * 0.68, y)
    tail_tip_bottom = (x - half, y + body_h * 0.5 + tail_bend)
    tail_root_bottom = (x - half * 0.45, y + body_h * 0.18)
    belly = (x + half * 0.2, y + body_h / 2)

    body_points = [
        nose, back, tail_root_top, tail_tip_top, tail_notch,
        tail_tip_bottom, tail_root_bottom, belly, nose,
    ]
    pygame.draw.lines(surface, color, False, body_points, line_width)

    # dorsal fin, one side only
    fin_base = (x, y - body_h * 0.28)
    fin_tip = (fin_base[0] - half * 0.15, fin_base[1] - body_h * 0.5)
    fin_back = (fin_base[0] - half * 0.3, fin_base[1] - body_h * 0.05)
    pygame.draw.lines(surface, color, False, [fin_base, fin_tip, fin_back], max(1, line_width - 1))

    # small mouth mark at the nose
    mouth_start = (nose[0] - 2, nose[1])
    mouth_end = (nose[0] - half * 0.14, nose[1] + body_h * 0.1)
    pygame.draw.line(surface, color, mouth_start, mouth_end, max(1, line_width - 1))
