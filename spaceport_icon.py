"""spaceport_icon.py — the Spaceport building's sphere-on-legs body, its
sign icon (a small copy of the actual ship art), and the launchpad
decoration the ship sits on. First place in the game that loads a real
image asset instead of drawing everything with pygame.draw primitives.
"""

import os

import pygame

ASSET_DIR = os.path.join(os.path.dirname(__file__), "assets")
SHIP_ASSET = "PLAYERSHIP.png"

LEG_COLOR = (90, 90, 90)
OUTLINE_COLOR = (40, 40, 40)
PAD_COLOR = (120, 80, 40)
TOWER_COLOR = (90, 70, 50)

_ship_image_cache = {}


def _ship_image(size):
    """The PLAYERSHIP sprite scaled to `size`x`size`, cached per size.

    Loaded lazily (not at module import time) — tile.py, which uses this,
    is imported well before game.py's main() calls pygame.display.set_mode(),
    so loading here instead of at import time avoids any dependency on
    display-mode timing. convert_alpha() is skipped for the same reason;
    the cost difference for a single small 12x12 blit is irrelevant.
    """
    if size not in _ship_image_cache:
        raw = pygame.image.load(os.path.join(ASSET_DIR, SHIP_ASSET))
        _ship_image_cache[size] = pygame.transform.scale(raw, (size, size))
    return _ship_image_cache[size]


def draw_spaceport_body(surface, building):
    """A large grey sphere on three legs — building.body_draw callback."""
    cx = building.x
    base_y = building.y
    sphere_r = building.width * 0.28
    sphere_cy = base_y - building.height * 0.75

    leg_top = (cx, sphere_cy + sphere_r * 0.3)
    leg_spread = building.width * 0.32
    leg_width = max(2, int(building.width * 0.03))
    for leg_x in (cx - leg_spread, cx, cx + leg_spread):
        pygame.draw.line(surface, LEG_COLOR, leg_top, (leg_x, base_y), leg_width)

    # sphere drawn after the legs so their attachment point tucks underneath it
    pygame.draw.circle(surface, building.color, (cx, sphere_cy), sphere_r)
    pygame.draw.circle(surface, OUTLINE_COLOR, (cx, sphere_cy), sphere_r, 2)


def spaceport_sign_icon(surface, center, height):
    """The sign icon: a small copy of the ship you'll actually fly."""
    size = int(height * 1.6)
    image = _ship_image(size)
    surface.blit(image, image.get_rect(center=center))


def draw_launchpad(surface, rect):
    """A brown pad with a two-rail lattice tower (X-strut cross-braces) on
    its left portion, and the actual PLAYERSHIP sprite standing on its
    right portion, clear of the tower."""
    pad_y = rect.bottom
    pygame.draw.line(surface, PAD_COLOR, (rect.left, pad_y), (rect.right, pad_y), 6)

    tower_width = rect.width * 0.22
    tower_left = rect.left + rect.width * 0.08
    tower_right = tower_left + tower_width
    tower_top = rect.top
    rail_w = 4
    pygame.draw.line(surface, TOWER_COLOR, (tower_left, pad_y), (tower_left, tower_top), rail_w)
    pygame.draw.line(surface, TOWER_COLOR, (tower_right, pad_y), (tower_right, tower_top), rail_w)

    strut_spacing = 26
    y = pad_y
    while y - strut_spacing >= tower_top:
        y_next = y - strut_spacing
        pygame.draw.line(surface, TOWER_COLOR, (tower_left, y), (tower_right, y_next), 3)
        pygame.draw.line(surface, TOWER_COLOR, (tower_right, y), (tower_left, y_next), 3)
        y = y_next

    ship_size = 90
    ship_x = rect.right - rect.width * 0.2
    image = _ship_image(ship_size)
    surface.blit(image, image.get_rect(midbottom=(ship_x, pad_y)))
