"""map.py — the World: tracks which tile the player is on in the 5x5 grid
and hands off to a neighboring tile when the player walks off an edge.

Only one Tile is ever kept in memory (`self.tile`) — moving to a neighbor
replaces it rather than caching every tile the player has visited.
"""

from constants import SCREEN_HEIGHT, SCREEN_WIDTH, START_TX, START_TY, WORLD_COLS, WORLD_ROWS
from tile import generate_tile


class World:
    def __init__(self, tx=START_TX, ty=START_TY, collected_items=None):
        self.tx = tx
        self.ty = ty
        self.collected_items = collected_items if collected_items is not None else set()  # {(tx, ty, item_name)}, survives tile regen
        self.tile = generate_tile(self.tx, self.ty, self.collected_items)

    def handle_transition(self, player):
        """Call once per frame after `player.update()`. If the player just
        exited an edge that has a neighboring tile, move there, reposition
        the player at the matching entry point, and load the new tile's
        content. Does nothing if the edge is at the map's outer boundary —
        Player's own clamp already keeps them on-screen in that case.
        """
        edge = player.exit_edge
        if edge == "left" and self.tx > 0:
            self.tx -= 1
            player.x = SCREEN_WIDTH - player.height / 2 - 1
        elif edge == "right" and self.tx < WORLD_COLS - 1:
            self.tx += 1
            player.x = player.height / 2 + 1
        elif edge == "top" and self.ty > 0:
            self.ty -= 1
            player.y = SCREEN_HEIGHT - 11
        elif edge == "bottom" and self.ty < WORLD_ROWS - 1:
            self.ty += 1
            player.y = player.height + 1
        else:
            return

        self.tile = generate_tile(self.tx, self.ty, self.collected_items)

    def collect(self, item_name):
        """Mark an item as picked up on the current tile so it won't
        reappear if this tile is regenerated later (e.g. on revisit)."""
        self.collected_items.add((self.tx, self.ty, item_name))
