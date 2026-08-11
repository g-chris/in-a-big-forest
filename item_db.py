"""item_db.py — the item database.

A single table of static item data: what each item is called, its category
tag, and the flavor text shown when the player tries to use it from the
inventory (one line for when it can't be used right now, one for when it can).

`equip_slot` is for items that toggle a persistent change to the player
instead of showing flavor text (see explore_scene.py's inventory "use"
handler) — `None` for ordinary items, or a slot name like `"vehicle"` /
`"head"` for equippable ones. cant_use/use description are unused for
equip items (the toggle messages are generated where the toggle happens).
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ItemRecord:
    name: str
    tag: str
    color: tuple
    cant_use_description: str
    use_description: str
    equip_slot: str = None


ITEM_TABLE = [
    ItemRecord(
        name="Metal Gear Solid for the PS1",
        tag="Key Item",
        color=(130, 130, 130),
        cant_use_description="There's no Sony PlayStation . . .",
        use_description="You insert the disc.",
    ),
    ItemRecord(
        name="Machine Part #25",
        tag="Key Item",
        color=(100, 140, 190),
        cant_use_description="It doesn't fit anything you have yet.",
        use_description="You attach the part.",
    ),
    ItemRecord(
        name="1957 Vincent Black Shadow",
        tag="Key Item",
        color=(20, 20, 20),
        cant_use_description="",
        use_description="",
        equip_slot="vehicle",
    ),
    ItemRecord(
        name="Motorcycle Helmet",
        tag="Key Item",
        color=(30, 30, 30),
        cant_use_description="",
        use_description="",
        equip_slot="head",
    ),
    ItemRecord(
        name="Hammer",
        tag="Key Item",
        color=(120, 120, 125),
        cant_use_description="Nothing around here needs hammering. Yet.",
        use_description="You give it a few test swings.",
    ),
]

_BY_NAME = {row.name: row for row in ITEM_TABLE}


def get_item(name):
    """Look up an item's database row by its exact name, or None if unknown."""
    return _BY_NAME.get(name)
