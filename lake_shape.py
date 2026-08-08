"""lake_shape.py — the "bisected bowl" lake: viewed as if the far shore is
just over the rise, so only the near half is drawn — a flat line across the
top, curving down to a rounded bottom. Scales to any rect, so the same
function draws both the small lake on the overworld tile and the full-screen
lake in the fishing mini-game.
"""

import math

import pygame

WATER_COLOR = (50, 110, 170)
BED_COLOR = (110, 80, 45)
SHORE_COLOR = (60, 130, 60)
SAND_COLOR = (210, 190, 140)

_ARC_SAMPLES = 20


def _bowl_points(rect):
    """Points tracing the bottom half of an ellipse inscribed in `rect`,
    from the top-right corner, down through the bottom, to the top-left
    corner. `pygame.draw.polygon` closes the shape with a straight line
    back to the start — which is exactly the flat top edge."""
    cx, cy = rect.centerx, rect.top
    rx, ry = rect.width / 2, rect.height
    points = []
    for i in range(_ARC_SAMPLES + 1):
        theta = math.pi * i / _ARC_SAMPLES
        points.append((cx + rx * math.cos(theta), cy + ry * math.sin(theta)))
    return points


def draw_lake(surface, rect, water_color=WATER_COLOR, bed_color=BED_COLOR,
              shore_color=SHORE_COLOR, sand_color=SAND_COLOR):
    bed_rect = pygame.Rect(rect.x - 10, rect.y, rect.width + 20, rect.height + 16)
    pygame.draw.polygon(surface, bed_color, _bowl_points(bed_rect))
    pygame.draw.polygon(surface, water_color, _bowl_points(rect))

    shore_rect = pygame.Rect(bed_rect.x - 4, rect.top - 6, bed_rect.width + 8, 8)
    pygame.draw.rect(surface, shore_color, shore_rect)

    sand_w, sand_h = max(18, rect.width * 0.08), max(8, rect.height * 0.12)
    for sand_x in (bed_rect.left + sand_w * 0.3, bed_rect.right - sand_w * 1.3):
        sand_rect = pygame.Rect(sand_x, rect.top - sand_h * 0.3, sand_w, sand_h)
        pygame.draw.ellipse(surface, sand_color, sand_rect)
