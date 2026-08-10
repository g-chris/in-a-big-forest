"""game.py — entry point: sets up pygame/audio and runs the SceneManager
loop. Keep this file thin — gameplay lives in explore_scene.py, dialogue.py,
bowling/, player.py, tree.py, building.py, tile.py, map.py, inventory.py,
and item_db.py.
"""

import os

import pygame

from audio.midi_tools import build_forest_theme
from audio.sound_tools import synthesize_bump, synthesize_engine_rumble, synthesize_footstep
from constants import FPS, SCREEN_HEIGHT, SCREEN_WIDTH
from main_menu import build_main_menu
from scene import SceneManager

ASSET_DIR = os.path.join(os.path.dirname(__file__), "assets")
SOUNDTRACK_PATH = os.path.join(ASSET_DIR, "soundtrack.mid")
FOOTSTEP_PATH = os.path.join(ASSET_DIR, "footstep.wav")
BUMP_PATH = os.path.join(ASSET_DIR, "bump.wav")
ENGINE_PATH = os.path.join(ASSET_DIR, "engine.wav")


def play_soundtrack():
    if not os.path.exists(SOUNDTRACK_PATH):
        build_forest_theme(SOUNDTRACK_PATH)
    try:
        pygame.mixer.music.load(SOUNDTRACK_PATH)
        pygame.mixer.music.play(loops=-1)
    except pygame.error as e:
        # MIDI playback depends on the SDL_mixer build having a MIDI backend
        # available (e.g. Timidity on Linux); fall back to silence rather
        # than crashing the game.
        print(f"Couldn't play soundtrack: {e}")


def load_sfx():
    if not os.path.exists(FOOTSTEP_PATH):
        synthesize_footstep(FOOTSTEP_PATH)
    if not os.path.exists(BUMP_PATH):
        synthesize_bump(BUMP_PATH)
    if not os.path.exists(ENGINE_PATH):
        synthesize_engine_rumble(ENGINE_PATH)
    try:
        footstep = pygame.mixer.Sound(FOOTSTEP_PATH)
        footstep.set_volume(0.10)
        bump = pygame.mixer.Sound(BUMP_PATH)
        bump.set_volume(0.20)
        engine = pygame.mixer.Sound(ENGINE_PATH)
        engine.set_volume(0.15)
        return footstep, bump, engine
    except pygame.error as e:
        print(f"Couldn't load sound effects: {e}")
        return None, None, None


def main():
    os.makedirs(ASSET_DIR, exist_ok=True)

    pygame.init()
    pygame.mixer.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Big Forest")
    clock = pygame.time.Clock()

    play_soundtrack()
    footstep_sound, bump_sound, engine_sound = load_sfx()

    manager = SceneManager(build_main_menu(footstep_sound, bump_sound, engine_sound))

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
            else:
                manager.current.handle_event(event, manager)

        keys = pygame.key.get_pressed()
        manager.current.update(dt, keys, manager)
        manager.current.draw(screen)

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
