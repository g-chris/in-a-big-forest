"""bank_icon.py — the Bank building's classical facade: two grey columns
holding up a grey pediment lettered "BANK" in green, and two large doors
with gold knobs. Also its small roof-sign icon (a gold dollar sign).
"""

import pygame

COLUMN_COLOR = (150, 150, 150)
PEDIMENT_COLOR = (185, 185, 185)
OUTLINE_COLOR = (60, 60, 60)
DOOR_COLOR = (55, 45, 35)
DOOR_OUTLINE_COLOR = (25, 25, 25)
KNOB_COLOR = (212, 175, 55)
BANK_TEXT_COLOR = (30, 150, 60)

_bank_font = None
_sign_font_cache = {}


def draw_bank_body(surface, building):
    """building.body_draw callback — replaces the default rect+door body."""
    global _bank_font
    rect = building.rect

    pediment_h = building.height * 0.35
    pediment_rect = pygame.Rect(rect.left, rect.top, rect.width, pediment_h)
    pygame.draw.rect(surface, PEDIMENT_COLOR, pediment_rect)
    pygame.draw.rect(surface, OUTLINE_COLOR, pediment_rect, 2)

    body_top = rect.top + pediment_h
    body_rect = pygame.Rect(rect.left, body_top, rect.width, rect.height - pediment_h)
    pygame.draw.rect(surface, building.color, body_rect)
    pygame.draw.rect(surface, OUTLINE_COLOR, body_rect, 2)

    column_w = building.width * 0.1
    for column_x in (rect.left + building.width * 0.18, rect.right - building.width * 0.18 - column_w):
        column_rect = pygame.Rect(column_x, body_top, column_w, body_rect.height)
        pygame.draw.rect(surface, COLUMN_COLOR, column_rect)
        pygame.draw.rect(surface, OUTLINE_COLOR, column_rect, 2)

    door_w, door_h = building.width * 0.14, body_rect.height * 0.85
    gap = building.width * 0.03
    door_y = body_rect.bottom - door_h
    # (left edge x, knob offset from that edge) — knobs sit closest to the gap between the doors
    doors = [
        (building.x - gap - door_w, door_w * 0.82),
        (building.x + gap, door_w * 0.18),
    ]
    for door_x, knob_offset in doors:
        door_rect = pygame.Rect(door_x, door_y, door_w, door_h)
        pygame.draw.rect(surface, DOOR_COLOR, door_rect)
        pygame.draw.rect(surface, DOOR_OUTLINE_COLOR, door_rect, 2)
        knob_center = (int(door_rect.left + knob_offset), int(door_rect.top + door_h * 0.55))
        pygame.draw.circle(surface, KNOB_COLOR, knob_center, max(2, int(door_w * 0.12)))

    if _bank_font is None:
        _bank_font = pygame.font.SysFont(None, max(14, int(pediment_h * 0.85)), bold=True)
    label = _bank_font.render("BANK", True, BANK_TEXT_COLOR)
    surface.blit(label, label.get_rect(center=pediment_rect.center))


def bank_sign_icon(surface, center, height):
    """A small gold dollar sign, for the roof sign board — building.py's
    default per-building icon slot (same role as draw_pin_icon/draw_fish)."""
    size = int(height * 1.4)
    if size not in _sign_font_cache:
        _sign_font_cache[size] = pygame.font.SysFont(None, size, bold=True)
    label = _sign_font_cache[size].render("$", True, KNOB_COLOR)
    surface.blit(label, label.get_rect(center=center))
