"""render_map_overview.py — renders the whole 5x5 world grid to a single
PNG in assets/ (world_map.png): one thumbnail per tile — trees, lake,
track, launchpad, buildings, and items — with grid lines and (tx, ty)
labels, so it's easy to see at a glance which tiles are still empty
("black"). Not part of the game itself; rerun any time after adding new
tile content in tile.py to regenerate the overview.
"""

import os

import pygame

from constants import SCREEN_HEIGHT, SCREEN_WIDTH, START_TX, START_TY, WORLD_COLS, WORLD_ROWS
from lake_shape import draw_lake
from spaceport_icon import draw_launchpad
from tile import generate_tile
from track_icon import draw_track_decoration

ASSET_DIR = os.path.join(os.path.dirname(__file__), "assets")
OUTPUT_PATH = os.path.join(ASSET_DIR, "world_map.png")

THUMB_W = SCREEN_WIDTH // 3   # 300 — small enough for a 5x5 mosaic to stay a reasonable
THUMB_H = SCREEN_HEIGHT // 3  # 200 — file size, large enough to keep building signage legible

HEADER_H = 32
GRID_LINE_COLOR = (70, 70, 70)
START_BORDER_COLOR = (255, 220, 0)
LABEL_COLOR = (255, 255, 255)
HEADER_BG = (20, 20, 20)


def render_tile_surface(tx, ty):
    """Render one tile at full game resolution — generate_tile()'s content
    is deterministic from (tx, ty) alone once collected_items is empty, so
    this always shows every item, even ones the player has since picked up
    in an actual save."""
    tile = generate_tile(tx, ty, collected_items=set())
    surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    surface.fill((0, 0, 0))

    if tile.lake is not None:
        draw_lake(surface, tile.lake.rect)
    if tile.track is not None:
        draw_track_decoration(surface, tile.track.rect, 0.0)
    if tile.launchpad is not None:
        draw_launchpad(surface, tile.launchpad.rect)
    for tree in tile.trees:
        tree.draw(surface)
    for building in tile.buildings:
        building.draw(surface)
    for world_item in tile.items:
        world_item.draw(surface)

    is_empty = not (tile.trees or tile.buildings or tile.items or tile.lake or tile.track or tile.launchpad)
    return surface, is_empty


def main():
    pygame.init()
    label_font = pygame.font.SysFont(None, 20)
    header_font = pygame.font.SysFont(None, 26)

    map_w = THUMB_W * WORLD_COLS
    map_h = THUMB_H * WORLD_ROWS
    output = pygame.Surface((map_w, HEADER_H + map_h))
    output.fill((0, 0, 0))

    header_rect = pygame.Rect(0, 0, map_w, HEADER_H)
    pygame.draw.rect(output, HEADER_BG, header_rect)
    header_label = header_font.render("In a Big Forest — World Map", True, LABEL_COLOR)
    output.blit(header_label, header_label.get_rect(center=header_rect.center))

    empty_tiles = []
    for ty in range(WORLD_ROWS):
        for tx in range(WORLD_COLS):
            tile_surface, is_empty = render_tile_surface(tx, ty)
            if is_empty:
                empty_tiles.append((tx, ty))
            thumb = pygame.transform.smoothscale(tile_surface, (THUMB_W, THUMB_H))
            output.blit(thumb, (tx * THUMB_W, HEADER_H + ty * THUMB_H))

    # grid lines + coordinate labels drawn on top, after every thumbnail is placed
    for ty in range(WORLD_ROWS + 1):
        y = HEADER_H + ty * THUMB_H
        pygame.draw.line(output, GRID_LINE_COLOR, (0, y), (map_w, y), 1)
    for tx in range(WORLD_COLS + 1):
        pygame.draw.line(output, GRID_LINE_COLOR, (tx * THUMB_W, HEADER_H), (tx * THUMB_W, HEADER_H + map_h), 1)

    for ty in range(WORLD_ROWS):
        for tx in range(WORLD_COLS):
            tile_rect = pygame.Rect(tx * THUMB_W, HEADER_H + ty * THUMB_H, THUMB_W, THUMB_H)
            label = label_font.render(f"({tx}, {ty})", True, LABEL_COLOR)
            output.blit(label, (tile_rect.left + 4, tile_rect.top + 4))
            if (tx, ty) == (START_TX, START_TY):
                pygame.draw.rect(output, START_BORDER_COLOR, tile_rect, 3)

    os.makedirs(ASSET_DIR, exist_ok=True)
    pygame.image.save(output, OUTPUT_PATH)
    print(f"Saved {OUTPUT_PATH} ({map_w}x{HEADER_H + map_h})")
    if empty_tiles:
        print("Empty tiles (no trees/buildings/lake/track/launchpad/items):")
        for tx, ty in empty_tiles:
            print(f"  ({tx}, {ty})")


if __name__ == "__main__":
    main()
