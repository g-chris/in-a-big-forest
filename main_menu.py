"""main_menu.py — the game's entry menu, plus a "Minigames" menu that gives
direct access to every mini-game built so far, for quick playtesting
without walking to each hut and satisfying its unlock condition.

New mini-games should be added to MINIGAME_LAUNCHERS below — that's the one
place this file needs to change to show up on the test menu. In the shipped
game, hut/minigame access will instead be gated behind save data (see the
planned Load Game slots); until then this menu is the fast path for testing.
"""

from bowling.scene import BowlingScene
from explore_scene import ExploreScene
from fishing.scene import FishingScene
from menu import ListMenu

COMING_SOON = "Coming soon!"


def build_main_menu(footstep_sound, bump_sound, engine_sound):
    def on_select(manager, index, label):
        if label == "New Game":
            manager.replace(ExploreScene(footstep_sound, bump_sound, engine_sound))
        elif label == "Minigames":
            manager.push(build_minigames_menu())
        else:
            manager.current.show_notice(COMING_SOON)

    return ListMenu(
        title="In a Big Forest",
        options=["New Game", "Load Game", "Minigames", "Options", "Credits"],
        on_select=on_select,
    )


def build_minigames_menu():
    options = [name for name, _launcher in MINIGAME_LAUNCHERS] + ["Back"]
    launchers = dict(MINIGAME_LAUNCHERS)

    def on_select(manager, index, label):
        if label == "Back":
            manager.pop()
            return
        launchers[label](manager)

    return ListMenu(title="Minigames", subtitle="Direct-launch for playtesting", options=options, on_select=on_select)


# -- bowling: the one minigame with multiplayer, so it gets a player-count step --

def _launch_bowling(manager):
    manager.push(build_bowling_player_count_menu())


def build_bowling_player_count_menu():
    options = ["1 Player", "2 Players", "3 Players", "4 Players", "Back"]

    def on_select(manager, index, label):
        if label == "Back":
            manager.pop()
            return
        count = index + 1
        manager.pop()  # drop the player-count menu
        player_names = [f"Player {i + 1}" for i in range(count)]
        manager.push(BowlingScene(player_names, bumpers=True, on_finish=_on_bowling_test_finish))

    return ListMenu(title="Bowling", subtitle="How many players?", options=options, on_select=on_select)


def _on_bowling_test_finish(manager, match):
    manager.pop()  # back to the minigames menu
    summary = ", ".join(f"{p.name}: {p.score}" for p in match.players)
    manager.current.show_notice(summary)


# -- fishing: single-player only, launches straight in --

def _launch_fishing(manager):
    manager.push(FishingScene(on_finish=_on_fishing_test_finish))


def _on_fishing_test_finish(manager, result):
    manager.pop()  # back to the minigames menu
    manager.current.show_notice(f"Caught {result.total_kg()}kg")


MINIGAME_LAUNCHERS = [
    ("Bowling", _launch_bowling),
    ("Fishing", _launch_fishing),
]
