"""main_menu.py — the game's entry menu, plus a "Minigames" menu that gives
direct access to every mini-game built so far, for quick playtesting
without walking to each hut and satisfying its unlock condition.

New mini-games should be added to MINIGAME_LAUNCHERS below — that's the one
place this file needs to change to show up on the test menu. In the shipped
game, hut/minigame access will instead be gated behind save data (see the
planned Load Game slots); until then this menu is the fast path for testing.
"""

from art_tools import PixelArtScene
from bowling.scene import BowlingScene
from explore_scene import ExploreScene
from fishing.scene import FishingScene
from menu import ListMenu
from motocross.scene import MotocrossScene
from space_wars.scene import SpaceWarsScene

COMING_SOON = "Coming soon!"


def build_main_menu(footstep_sound, bump_sound, engine_sound):
    def on_select(manager, index, label):
        if label == "New Game":
            manager.replace(ExploreScene(footstep_sound, bump_sound, engine_sound))
        elif label == "Minigames":
            manager.push(build_minigames_menu(footstep_sound, bump_sound, engine_sound))
        elif label == "Options":
            manager.push(build_options_menu())
        else:
            manager.current.show_notice(COMING_SOON)

    return ListMenu(
        title="In a Big Forest",
        options=["New Game", "Load Game", "Minigames", "Options", "Credits"],
        on_select=on_select,
    )


def build_options_menu():
    options = ["Pixel Art Editor", "Back"]

    def on_select(manager, index, label):
        if label == "Back":
            manager.pop()
            return
        manager.push(PixelArtScene())

    return ListMenu(title="Options", options=options, on_select=on_select)


def build_minigames_menu(footstep_sound, bump_sound, engine_sound):
    def _launch_full_game(manager):
        manager.replace(ExploreScene(footstep_sound, bump_sound, engine_sound))

    entries = [("Full Game (from the start)", _launch_full_game)] + MINIGAME_LAUNCHERS
    options = [name for name, _launcher in entries] + ["Back"]
    launchers = dict(entries)

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
        manager.push(BowlingScene(player_names, on_finish=_on_bowling_test_finish))

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


# -- motocross: single-player only, launches straight in, no gear gate --

def _launch_motocross(manager):
    manager.push(MotocrossScene(on_finish=_on_motocross_test_finish))


def _on_motocross_test_finish(manager, race):
    manager.pop()  # back to the minigames menu
    manager.current.show_notice(f"Time: {race.race_time:.1f}s")


# -- space wars: single-player only, launches straight in --

def _launch_space_wars(manager):
    manager.push(SpaceWarsScene(on_finish=_on_space_wars_test_finish))


def _launch_space_wars_stage_2(manager):
    manager.push(SpaceWarsScene(on_finish=_on_space_wars_test_finish, stage="1-2"))


def _launch_space_wars_stage_3(manager):
    manager.push(SpaceWarsScene(on_finish=_on_space_wars_test_finish, stage="1-3"))


def _on_space_wars_test_finish(manager, scene):
    manager.pop()  # back to the minigames menu
    manager.current.show_notice(f"Stage {scene.stage} clear!" if scene.state == "won" else "Game Over")


MINIGAME_LAUNCHERS = [
    ("Bowling", _launch_bowling),
    ("Fishing", _launch_fishing),
    ("MotoCross", _launch_motocross),
    ("Space Wars", _launch_space_wars),
    ("Space Wars (Stage 1-2)", _launch_space_wars_stage_2),
    ("Space Wars (Stage 1-3)", _launch_space_wars_stage_3),
]
