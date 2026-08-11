"""track_icon.py — a small animated decoration for the MotoCross tile: a
miniature oval dirt track (a ring, seen from above) with a couple of tiny
bikers circling it and a small crowd along the near edge. Purely visual —
collision for the track lives on tile.MotocrossTrack.
"""

import math

import pygame

TRACK_COLOR = (200, 170, 110)
INFIELD_COLOR = (60, 130, 60)
BIKER_COLORS = [(200, 40, 40), (40, 80, 200), (230, 200, 40)]
CROWD_COLOR = (150, 130, 110)

BIKER_PHASES = [0.0, 2.1, 4.2]
BIKER_ANGULAR_SPEED = 1.4  # radians/sec
CROWD_OFFSETS = range(-40, 41, 8)


def draw_track_decoration(surface, rect, t):
    """rect: the track's bounding pygame.Rect. t: elapsed seconds, used to
    animate the bikers circling the ring."""
    pygame.draw.ellipse(surface, TRACK_COLOR, rect)
    infield = rect.inflate(-rect.width * 0.45, -rect.height * 0.45)
    pygame.draw.ellipse(surface, INFIELD_COLOR, infield)

    cx, cy = rect.center
    ring_rx, ring_ry = rect.width * 0.35, rect.height * 0.35
    for i, phase in enumerate(BIKER_PHASES):
        angle = t * BIKER_ANGULAR_SPEED + phase
        x = cx + ring_rx * math.cos(angle)
        y = cy + ring_ry * math.sin(angle)
        pygame.draw.circle(surface, BIKER_COLORS[i % len(BIKER_COLORS)], (int(x), int(y)), 3)

    crowd_y = rect.bottom - rect.height * 0.08
    for dx in CROWD_OFFSETS:
        pygame.draw.circle(surface, CROWD_COLOR, (int(cx + dx), int(crowd_y)), 2)
