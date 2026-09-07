"""save_system.py — reading/writing save-game data as plain JSON dicts.

Deliberately has no dependency on explore_scene.py/map.py/player.py/etc —
it only ever touches plain dicts of primitives, so explore_scene.py can
import this module (to actually write/read a slot) without a circular
import; explore_scene.py itself owns turning a dict into/out of its own
live game objects (ExploreScene.to_save_data/from_save_data).
"""

import json
import os

from constants import SCREEN_HEIGHT, SCREEN_WIDTH, START_TX, START_TY

SAVE_DIR = os.path.join(os.path.dirname(__file__), "saves")

SLOT_IDS = ["1", "2", "3"]
SLOT_LABELS = {"1": "SAVE SLOT 1", "2": "SAVE SLOT 2", "3": "SAVE SLOT 3"}
LABEL_TO_SLOT_ID = {label: slot_id for slot_id, label in SLOT_LABELS.items()}


def _slot_path(slot_id):
    return os.path.join(SAVE_DIR, f"slot_{slot_id}.json")


def slot_exists(slot_id):
    return os.path.exists(_slot_path(slot_id))


def write_slot(slot_id, data):
    os.makedirs(SAVE_DIR, exist_ok=True)
    with open(_slot_path(slot_id), "w") as f:
        json.dump(data, f, indent=2)


def read_slot(slot_id):
    with open(_slot_path(slot_id)) as f:
        return json.load(f)


def debug_fixture():
    """A hand-built save used only by the DEBUG load slot (never written
    by the player), for jumping straight into late-game testing without
    playing through every minigame first. Every gear-gated hut is already
    open; Space Wars itself is left untouched so it's still fully
    testable end-to-end from the Spaceport."""
    return {
        "tx": START_TX, "ty": START_TY,
        "player_x": SCREEN_WIDTH / 2, "player_y": SCREEN_HEIGHT / 2,
        "riding": True, "wearing_helmet": True,
        "collected_items": [[START_TX, START_TY, "Metal Gear Solid for the PS1"]],
        "inventory": [
            "Machine Part #25", "1957 Vincent Black Shadow", "Motorcycle Helmet", "Hammer",
            "Metal Gear Solid for the PS1",
            None, None, None, None, None, None, None, None, None, None, None,
        ],
        "won_machine_part": True,
        "bowling_high_score": 200,
        "won_motorcycle": True,
        "won_helmet": True,
        "fishing_high_score": 100,
        "won_hammer": True,
        "motocross_best_time": 20.0,
        "player_name": None,
        "bowling_alley_closed": False,
    }
