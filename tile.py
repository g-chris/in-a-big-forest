"""tile.py — a single screen's worth of content (trees + items).

Content is defined per-tile in the small data tables below and built on
demand by `generate_tile()`, rather than being kept in memory for all 25
tiles at once — `map.World` calls this each time the player enters a tile,
and discards the previous one.
"""

import pygame

from building import Building
from fish_icon import draw_fish
from inventory import Item, WorldItem
from item_db import get_item
from motorcycle_icon import draw_motorcycle
from spaceport_icon import draw_launchpad, draw_spaceport_body, spaceport_sign_icon
from tree import generate_trees

FISH_SIGN_COLOR = (210, 200, 70)
MOTO_SIGN_COLOR = (200, 40, 40)

# tiles not listed here are blank placeholders (walkable, no trees) until
# their content is designed
TILE_FORESTS = {
    (2, 2): {"seed": 7, "count": 18},  # the original forest
    (2, 3): {"seed": 3, "count": 7},  # Test
    (2, 4): {"seed": 11, "count": 10},  # a few trees for a woodsy lake feel
    (4, 2): {"seed": 17, "count": 12},  # woodsy trees around the moto track
    (0, 3): {"seed": 23, "count": 8},  # a clearing around the spaceport
}

# tiles not listed here have no items. Coordinates are exact, hand-placed
# positions (not RNG seeds) so they're easy to read and retune by eye.
TILE_ITEMS = {
    (2, 2): [("Metal Gear Solid for the PS1", 684, 177)],
}


def _fish_sign_icon(surface, center, height):
    draw_fish(surface, center[0], center[1], height * 2.2, FISH_SIGN_COLOR)


def _moto_sign_icon(surface, center, height):
    # draw_motorcycle's ground point is its base, not its center, so nudge
    # the base down by half the icon's height to vertically center it in
    # the sign box the same way the pin/fish icons already sit
    icon_height = height * 0.9
    draw_motorcycle(surface, center[0], center[1] + icon_height * 0.5, icon_height, MOTO_SIGN_COLOR)


# tiles not listed here have no buildings. Construction parameters, not live
# Building instances — pygame.font isn't initialized yet at module-import
# time, so these are only turned into Building objects inside generate_tile().
TILE_BUILDINGS = {
    (2, 1): [
        {
            "x": 450, "y": 420,
            "width": 300,   # ~4 tree canopies wide
            "height": 50,   # the height of the player character
            "color": (120, 80, 40),
            "sign_text": "BOWLING",
            "kind": "bowling",
        },
    ],
    (2, 4): [
        {
            "x": 450, "y": 480,
            "width": 260,
            "height": 50,   # the height of the player character
            "color": (90, 65, 40),
            "sign_text": "FISHING",
            "kind": "fishing",
            "sign_icon": _fish_sign_icon,
        },
    ],
    (4, 2): [
        {
            "x": 450, "y": 420,
            "width": 260,
            "height": 50,   # the height of the player character
            "color": (95, 70, 50),
            "sign_text": "1997 MotoX",
            "kind": "motocross",
            "sign_icon": _moto_sign_icon,
        },
    ],
    (0, 3): [
        {
            "x": 450, "y": 480,
            "width": 200,
            "height": 90,   # "large" — taller than the other huts
            "color": (150, 150, 150),
            "sign_text": "SPACEPORT",
            "kind": "spaceport",
            "sign_icon": spaceport_sign_icon,
            "body_draw": draw_spaceport_body,
        },
    ],
}

# tiles not listed here have no lake. Same "construction parameters, built
# lazily" reasoning as buildings above (kept consistent even though Lake
# itself doesn't need pygame.font, for one predictable pattern to read).
TILE_LAKES = {
    (2, 4): {"x": 450, "y": 210, "width": 380, "height": 170},
}

# tiles not listed here have no moto track. Same "construction parameters,
# built lazily" reasoning as lakes/buildings above.
TILE_MOTOCROSS_TRACKS = {
    (4, 2): {"x": 450, "y": 200, "width": 360, "height": 150},
}

# tiles not listed here have no launchpad. Same "construction parameters,
# built lazily" reasoning as lakes/buildings above.
TILE_LAUNCHPADS = {
    (0, 3): {"x": 450, "y": 150, "width": 360, "height": 260},
}


def _inside_ellipse(px, py, cx, cy, rx, ry):
    """Shared by Lake and MotocrossTrack: is (px, py) inside the ellipse
    centered at (cx, cy) with radii (rx, ry)?"""
    return ((px - cx) / rx) ** 2 + ((py - cy) / ry) ** 2 <= 1


class Lake:
    def __init__(self, x, y, width, height):
        self.rect = pygame.Rect(x - width / 2, y, width, height)

    def blocks(self, px, py, radius):
        """Same polymorphic obstacle interface as Tree/Building.blocks(),
        but shaped like the bisected bowl actually drawn (lake_shape.draw_lake)
        rather than its bounding rect, so the player can't just walk on water."""
        if py < self.rect.top - radius:
            return False
        cx, cy = self.rect.centerx, self.rect.top
        return _inside_ellipse(px, py, cx, cy, self.rect.width / 2 + radius, self.rect.height + radius)


class MotocrossTrack:
    def __init__(self, x, y, width, height):
        self.rect = pygame.Rect(x - width / 2, y - height / 2, width, height)

    def blocks(self, px, py, radius):
        """Same polymorphic obstacle interface as Tree/Building/Lake.blocks()
        — a full oval this time (not bisected like the lake's bowl), since
        the track decoration reads as a complete loop from above."""
        cx, cy = self.rect.center
        return _inside_ellipse(px, py, cx, cy, self.rect.width / 2 + radius, self.rect.height / 2 + radius)


class Launchpad:
    def __init__(self, x, y, width, height):
        self.rect = pygame.Rect(x - width / 2, y - height / 2, width, height)

    def blocks(self, px, py, radius):
        """Same polymorphic obstacle interface as Tree/Building/Lake/
        MotocrossTrack.blocks() — a plain rectangle, same reasoning
        Building uses (the launchpad's silhouette is close enough to its
        bounding box that a fitted shape isn't worth it, unlike Lake/
        MotocrossTrack's much more distinctly non-rectangular shapes)."""
        return self.rect.inflate(radius * 2, radius * 2).collidepoint(px, py)


class Tile:
    def __init__(self, trees, items, buildings, lake, track, launchpad):
        self.trees = trees
        self.items = items
        self.buildings = buildings
        self.lake = lake
        self.track = track
        self.launchpad = launchpad


def _clear_of(rects, margin=20):
    """A predicate factory: True if a tree's base point falls outside every
    rect in `rects` (each inflated by `margin`)."""
    inflated = [r.inflate(margin * 2, margin * 2) for r in rects]

    def clear(tree):
        return not any(r.collidepoint(tree.x, tree.y) for r in inflated)

    return clear


def generate_tile(tx, ty, collected_items):
    """Build the Tile at grid position (tx, ty).

    `collected_items` is the World's persistent set of (tx, ty, item_name)
    tuples already picked up, so a previously-collected item doesn't
    reappear when the player regenerates a tile by revisiting it.
    """
    forest = TILE_FORESTS.get((tx, ty))
    trees = generate_trees(forest["seed"], forest["count"]) if forest else []

    items = []
    for name, x, y in TILE_ITEMS.get((tx, ty), []):
        if (tx, ty, name) in collected_items:
            continue  # already picked up on an earlier visit to this tile
        record = get_item(name)
        items.append(WorldItem(x, y, Item(name, record.color)))

    buildings = [Building(**cfg) for cfg in TILE_BUILDINGS.get((tx, ty), [])]

    lake_cfg = TILE_LAKES.get((tx, ty))
    lake = Lake(**lake_cfg) if lake_cfg else None

    track_cfg = TILE_MOTOCROSS_TRACKS.get((tx, ty))
    track = MotocrossTrack(**track_cfg) if track_cfg else None

    launchpad_cfg = TILE_LAUNCHPADS.get((tx, ty))
    launchpad = Launchpad(**launchpad_cfg) if launchpad_cfg else None

    if trees and (lake or buildings or track or launchpad):
        # a tile with both a forest and a lake/building/track/launchpad
        # wasn't hand-checked for overlap when the forest seed was picked,
        # so just drop any tree that landed on top of one — may end up
        # with fewer trees than `count`, which is fine for a decorative forest
        obstacle_rects = (([lake.rect] if lake else []) + ([track.rect] if track else [])
                          + ([launchpad.rect] if launchpad else []) + [b.rect for b in buildings])
        trees = list(filter(_clear_of(obstacle_rects), trees))

    return Tile(trees, items, buildings, lake, track, launchpad)
