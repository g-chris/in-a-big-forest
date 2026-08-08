"""constants.py — shared config and colors used across multiple modules.

Kept separate so `player.py`, `tree.py`, `tile.py`, and `map.py` can all
reference the same screen size / world size without importing from `game.py`
(which would create circular imports, since `game.py` is the entry point that
imports all of them).
"""

SCREEN_WIDTH = 900
SCREEN_HEIGHT = 600
FPS = 60

# the world is a 5x5 grid of screens ("tiles"); tile (2, 2) is the center,
# where the original forest lives
WORLD_COLS = 5
WORLD_ROWS = 5
START_TX = 2
START_TY = 2

BLACK = (0, 0, 0)
YELLOW = (255, 220, 0)
SHADED_YELLOW = (140, 115, 10)  # player color when seen through canopy leaves
BROWN = (110, 70, 30)
GREEN = (40, 150, 40)
