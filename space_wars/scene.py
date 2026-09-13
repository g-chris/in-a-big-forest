"""space_wars/scene.py — the SPACE WARS mini-game screen. Top-down shooter:
free horizontal movement (wrapping at the screen edges, like every ship in
this game), a bounded vertical advance/retreat, a cooldown-limited laser,
and the Swarm/Launcher enemies from .enemies wired into collision, a
lives/death sequence, and a stage-clear/game-over screen. Stages are
defined in STAGES (Swarm waves per stage, how each wave is released, how
many Launchers appear, and which stage to auto-advance into on a win).
"""

import itertools
import math
import os
import random

import pygame

from audio.midi_tools import build_forest_theme, build_space_theme
from audio.sound_tools import synthesize_enemy_laser_shot, synthesize_explosion, synthesize_laser_shot
from constants import SCREEN_HEIGHT, SCREEN_WIDTH
from scene import Scene

from .enemies import DIVING, DONE, Boss, Launcher, Seeker, SwarmEnemy

ASSET_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "assets"))
FOREST_SOUNDTRACK_PATH = os.path.join(ASSET_DIR, "soundtrack.mid")
SPACE_SOUNDTRACK_PATH = os.path.join(ASSET_DIR, "space_soundtrack.mid")
PLAYER_LASER_SFX_PATH = os.path.join(ASSET_DIR, "laser.wav")
ENEMY_LASER_SFX_PATH = os.path.join(ASSET_DIR, "enemy_laser.wav")
EXPLOSION_SFX_PATH = os.path.join(ASSET_DIR, "explosion.wav")

PLAYER_SIZE = 56
ENEMY_SIZE = 48
LAUNCHER_SIZE = ENEMY_SIZE * 2
LIFE_ICON_SIZE = 22

BASE_Y = 520
VERTICAL_MOVEMENT = 150   # how far up from BASE_Y the player can advance — tune freely
PLAYER_SPEED = 350        # px/s, both axes
COOLDOWN_TIME = 0.2      # seconds between player shots — tune freely
AUTOPILOT_SPEED = 350     # px/s — the cutscene's control-free ship/Friendly movement — tune freely

LASER_SPEED = 420
ENEMY_LASER_SPEED = 260
LASER_W, LASER_H = 3, 16
EXPLOSION_SHOT_SIZE = 8   # small square "shrapnel" shots — a Seeker's radial burst — tune freely

CHARGE_INTERVAL = 1       # seconds held to fire a charge shot — tune freely
CHARGE_SHOT_SPEED = 600     # px/s, faster than a normal laser
CHARGE_SHOT_RADIUS = 14
CHARGE_SHOT_COLOR = (255, 220, 0)
NORMAL_SHOT_DAMAGE = 1      # boss HP damage per normal shot (once its shield is down)
CHARGE_SHOT_DAMAGE = 10     # boss HP damage per charge shot (once its shield is down)
CHARGE_METER_WIDTH = 160
CHARGE_METER_HEIGHT = 18
CHARGE_METER_MARGIN_BOTTOM = 30
CHARGE_TRAIL_PARTICLE_LIFETIME = 0.3  # short-lived sparks left behind the charge shot — tune freely
CHARGE_TRAIL_PARTICLE_SIZE = 3
CHARGE_TRAIL_PARTICLE_SPREAD = 3   # px, small random offset so the trail isn't a single line — tune freely
CHARGE_REVEAL_FLASH_DURATION = 1.2  # total time the Friendly's shield flashes during the reveal
CHARGE_REVEAL_PAUSE = 1.5           # pause after the meter appears, before dialogue resumes
FRIENDLY_DEPART_SPEED = 40          # px/s, initial gentle drift downward — tune freely
FRIENDLY_DEPART_ACCEL = 220         # px/s^2 — it accelerates as it "drops" — tune freely
FRIENDLY_DEPART_SHRINK_DURATION = 1.8  # seconds to shrink to its minimum scale — tune freely
FRIENDLY_DEPART_MIN_SCALE = 0.15

FORMATION_Y = 110
FORMATION_LEFT = 140
FORMATION_RIGHT = 760
GROUP_GAP = 40            # horizontal gap between adjacent groups in a multi-group wave — tune freely
WAVE_DELAY = 3.0          # seconds before a "timer"-gated wave starts entering — tune freely
WAVE_CLEAR_INTERVAL = 2.0  # seconds paused after a "clear"-gated wave clears before the next releases — tune freely

MIN_SWARM_SPACING = ENEMY_SIZE + 12  # a group's row auto-splits into more rows below this spacing — tune freely
SWARM_ROW_SPACING = ENEMY_SIZE + 20  # vertical gap between a group's auto-split rows — tune freely

LAUNCHER_ROW_MIN = 60             # top of the Launcher's patrol band, in px
LAUNCHER_ROW_MAX = SCREEN_HEIGHT / 3  # "top third of the playing area"
LAUNCHER_SPAWN_COUNT = 2          # Swarm ships created per "spawn" action — tune freely

SEEKER_ENTRY_MARGIN = 40          # px off-screen to either side where a Seeker starts
SEEKER_BOTTOM_BAND = 4 / 5         # a Seeker that reaches this far down the screen explodes

# Each stage is a list of waves; each wave is a list of groups, and each
# group names how many Swarm ships and Launchers ("launchers", default 0)
# spawn together in their own horizontal band. "gate" says how the next
# wave in the stage is released ("timer" = after WAVE_DELAY regardless of
# the previous wave's state; "clear" = only once every ship AND Launcher
# in the previous wave has reached DONE). "next" names the stage to
# auto-advance into on win (None = end the run and hand off to on_finish).
STAGES = {
    "1-1": {
        "waves": [{"groups": [{"swarm": 4}]}, {"groups": [{"swarm": 4}]}],
        "gate": "timer", "next": "1-2",
    },
    "1-2": {
        "waves": [{"groups": [{"swarm": 4}]}, {"groups": [{"swarm": 4}]},
                  {"groups": [{"swarm": 8}]}],
        "gate": "clear", "next": "1-3",
    },
    "1-3": {
        "waves": [
            {"groups": [{"swarm": 3, "launchers": 1}, {"swarm": 3, "launchers": 1}]},
            {"groups": [{"swarm": 5, "launchers": 2}, {"swarm": 5, "launchers": 2}]},
        ],
        "gate": "clear", "next": "2-1",
        "cutscene": {
            "wait": 3.0,
            "transmission_text": "Transmission Incoming . . .",
            "speaker": "Bowling Alley Guy",
            "lines": [
                "Yeehaw, cowboy! Looks like you could use a little help.",
                "If there's no Earth, there's no bowling! ha ha ha",
            ],
        },
    },
    "2-1": {
        "waves": [
            {"groups": [{"swarm": 8, "launchers": 3}]},
            {"groups": [{"swarm": 8, "launchers": 8}]},
        ],
        "gate": "clear", "next": "2-2",
        "friendly": True,
        "game_over_line": {"speaker": "Bowling Alley Guy", "line": "Cowboy! Nooooooo !!"},
    },
    "2-2": {
        "waves": [
            {"groups": [{"swarm": 12, "launchers": 6, "seekers": 3}]},
            {"groups": [{"swarm": 6, "seekers": 6}]},
            {"groups": [{"swarm": 16, "seekers": 8}]},
        ],
        "gate": "clear", "next": "2-3",
        "friendly": True,
        "game_over_line": {"speaker": "Bowling Alley Guy", "line": "Cowboy! Nooooooo !!"},
    },
    "2-3": {
        "waves": [
            {"groups": [{"swarm": 2}]},
            {"groups": [{"swarm": 1}]},
            {"groups": [{"swarm": 9}, {"swarm": 9}]},  # 2 rows of 9
            {"groups": [{"swarm": 10, "launchers": 5, "seekers": 10}]},
            {"groups": [{"swarm": 12, "launchers": 10, "seekers": 12}]},
        ],
        "gate": "clear", "next": "3-1",
        "friendly": True,
        "game_over_line": {"speaker": "Bowling Alley Guy", "line": "Cowboy! Nooooooo !!"},
    },
    "3-1": {
        "waves": [
            {"groups": [{"swarm": 10, "launchers": 10, "seekers": 8}]},
            {"groups": [{"swarm": 30}]},
            {"groups": [{"launchers": 20, "seekers": 10}]},
        ],
        "gate": "clear", "next": "3-2",
        "friendly": True,
        "game_over_line": {"speaker": "Bowling Alley Guy", "line": "Cowboy! Nooooooo !!"},
        "boss": True,
        "cutscene": {
            "wait": 3.0,
            "transmission_text": "Transmission Incoming . . .",
            "speaker": "Bowling Alley Guy",
            "lines": [
                "Well shoot! Our lasers can't get through that shield!",
                "Take my energy to unlock your CHARGE SHOT!",
                "Well, that's all the power I have . . .",
                "Good luck Cowboy . . .",
                "I hope you're better at being a hero than bowling . . .",
                "ha ha ha",
            ],
            "unlocks_charge_shot_after_line": 1,
            "friendly_departs": True,
        },
    },
    "3-2": {
        "waves": [
            {"groups": [{"swarm": 20}]},
            {"groups": [{"swarm": 10, "launchers": 10, "seekers": 10}]},
            {"groups": [{"swarm": 20, "launchers": 10, "seekers": 10}]},
            {"groups": [{"launchers": 10, "seekers": 10}]},
        ],
        "gate": "cycle", "next": None,
        "boss": True, "boss_hp": 50,
        "game_over_line": {"speaker": "Bowling Alley Guy", "line": "Cowboy! Nooooooo !!"},
        "cutscene": {
            "wait": 3.0,
            "transmission_text": "Transmission Incoming . . .",
            "speaker": "Space Command",
            "lines": [
                "You did it. You saved the Earth.",
                "For a thousand years, man and the Space Empress have fought.",
                "And it was you, sorry, what did you say your name was?",
                "From everyone on Earth: Thank you, {name}.",
            ],
            "name_entry_after_line": 2,
        },
    },
}

SCORE_PER_KILL = 25       # points for a Swarm ship destroyed by a player laser
SCORE_PER_LAUNCHER_KILL = 150  # points for a Launcher destroyed by a player laser
SCORE_PER_SEEKER_KILL = 300  # points for a Seeker destroyed by a player laser
SCORE_PER_SHOT = 1        # points deducted for each shot fired, floored at 0

LIFE_BONUS_INTERVAL = 1000  # an extra life every 1000 points (1000, 2000, 3000, ...) — tune freely
LIFE_BONUS_FLASH_DURATION = 1.5  # seconds the score flashes + "BONUS LIFE" shows — tune freely
LIFE_BONUS_FLASH_COLOR = (255, 220, 0)  # matches the game's established yellow accent (dialogue.py's PLAYER_COLOR)

STARTING_EXTRA_LIVES = 2
FLASH_INTERVAL = 0.08     # seconds per invulnerability blink half-cycle
INVULNERABLE_DURATION = 2.0  # seconds of post-respawn invulnerability — tune freely

PARTICLE_COUNT_PLAYER = 28
PARTICLE_COUNT_ENEMY = 14
PARTICLE_LIFETIME = 0.6
PARTICLE_SPEED = 140
PARTICLE_SIZE = 4

HIT_RADIUS_PLAYER = 22    # enemy-ship / enemy-laser vs player
HIT_RADIUS_ENEMY = 20     # player-laser vs enemy

# Launcher hitboxes scaled by the same 3x factor as its sprite size, so its
# collision size matches how much bigger it looks than a Swarm ship.
_LAUNCHER_SCALE = LAUNCHER_SIZE / ENEMY_SIZE
LAUNCHER_HIT_RADIUS_PLAYER = HIT_RADIUS_PLAYER * _LAUNCHER_SCALE
LAUNCHER_HIT_RADIUS_ENEMY = HIT_RADIUS_ENEMY * _LAUNCHER_SCALE
LAUNCHER_SHIELD_RADIUS = LAUNCHER_SIZE / 2 + 20  # a faint halo just outside the ship's own hitbox — tune freely

FRIENDLY_SIZE = PLAYER_SIZE       # the wingman flies at the same scale as the player
FRIENDLY_OFFSET_X = -70           # px to the player's left — tune freely
FRIENDLY_SHIELD_RADIUS = FRIENDLY_SIZE / 2 + 6  # tight, permanent halo — tune freely

BOSS_SIZE = ENEMY_SIZE * 4        # tune freely
BOSS_Y = 90                       # fixed patrol row near the top — tune freely
BOSS_SHIELD_RADIUS = BOSS_SIZE / 2 + 20  # a faint halo just outside the boss's own hitbox — tune freely
BOSS_SHIELD_COLOR = (255, 215, 0, 130)   # gold, semi-transparent — impenetrable (until charge-stripped)
BOSS_SHIELD_COLOR_DAMAGED = (200, 40, 40, 150)  # red, after the first charge hit
BOSS_ENEMY_Y_OFFSET = 110  # how far Swarm/Launcher/Seeker spawn rows shift down when a Boss is present

BOSS_HEALTH_BAR_WIDTH = 300
BOSS_HEALTH_BAR_HEIGHT = 22
BOSS_HEALTH_BAR_COLOR = (200, 30, 30)

BOSS_DEFEAT_DURATION = 2.5        # seconds, a gentle/slow white flash — tune freely
BOSS_DEFEAT_FLASH_MAX_ALPHA = 180
BOSS_EXPLOSION_PARTICLE_COUNT = 60  # a big burst — tune freely

DIALOGUE_BOX_MARGIN = 20  # inset from the screen edges — tune freely
DIALOGUE_BOX_HEIGHT = 160
DIALOGUE_FONT_SIZE = 30    # bigger than the small hint/speaker font — tune freely
WORD_REVEAL_INTERVAL = 0.06  # seconds per word, a fast typewriter reveal — tune freely

# post_win_wait's boss-stage layout: the player/Friendly come up just far
# enough to clear the dialogue box (rather than all the way to true screen
# center, which would land them right on top of the Boss); the Boss settles
# a good deal higher, so nothing overlaps — tune freely.
CUTSCENE_PLAYER_Y = SCREEN_HEIGHT - DIALOGUE_BOX_HEIGHT - DIALOGUE_BOX_MARGIN - PLAYER_SIZE / 2 - 20
CUTSCENE_BOSS_Y = 160

# On-screen name-entry keyboard — D-Pad + Space only, matching art_tools.py's
# pixel-art-naming keyboard's layout/feel (a fresh local implementation, not
# a shared import, since this is the only other place it's needed so far).
NAME_ENTRY_MAX_LENGTH = 12
NAME_KEYBOARD_ROWS = [
    "ABCDEFGHI",
    "JKLMNOPQR",
    "STUVWXYZ0",
    "123456789",
]
NAME_ACTIONS = ["Del", "Done"]
NAME_KEY_PX = 40
NAME_KEYBOARD_LEFT = (SCREEN_WIDTH - len(NAME_KEYBOARD_ROWS[0]) * NAME_KEY_PX) // 2
NAME_KEYBOARD_TOP = 260
NAME_ACTIONS_Y = NAME_KEYBOARD_TOP + len(NAME_KEYBOARD_ROWS) * NAME_KEY_PX + 30
NAME_DEFAULT = "Cowboy"
SELECTED_KEY_COLOR = (255, 220, 0)  # matches the game's established yellow accent

STAR_COUNT = 60

BG_COLOR = (5, 5, 18)
STAR_COLOR = (200, 200, 220)
PLAYER_LASER_COLOR = (255, 255, 255)
ENEMY_LASER_COLOR = (230, 60, 60)
TEXT_COLOR = (255, 255, 255)
PARTICLE_COLOR = (255, 255, 255)
SHIELD_COLOR = (120, 190, 255, 90)  # faint translucent blue ring
NPC_PORTRAIT_COLOR = (220, 220, 220)  # matches dialogue.py's NPC_COLOR — a stick figure has no face

_image_cache = {}


def _load_image(name, size):
    key = (name, size)
    if key not in _image_cache:
        raw = pygame.image.load(os.path.join(ASSET_DIR, f"{name}.png"))
        _image_cache[key] = pygame.transform.scale(raw, (size, size))
    return _image_cache[key]


def _dist(x1, y1, x2, y2):
    return math.hypot(x1 - x2, y1 - y2)


def _score_for_kill(target):
    if isinstance(target, Launcher):
        return SCORE_PER_LAUNCHER_KILL
    if isinstance(target, Seeker):
        return SCORE_PER_SEEKER_KILL
    return SCORE_PER_KILL


def _reveal_tokens(line):
    """Splits `line` into typewriter reveal tokens: normally one token per
    word, but a stretched run of 3+ identical letters within a word (e.g.
    "Noooooo") keeps only the run's first letter attached to its word and
    reveals each further repeat as its own token, so it builds up fast one
    letter at a time — a comedic emphasis effect, not just word-by-word.
    Each token already carries any leading space it needs, so the visible
    text so far is reconstructed with a plain "".join(tokens[:n])."""
    tokens = []
    for wi, word in enumerate(line.split()):
        word_tokens = []
        buffer = ""
        for ch, group in itertools.groupby(word):
            run = len(list(group))
            if run >= 3:
                buffer += ch
                word_tokens.append(buffer)
                buffer = ""
                word_tokens.extend([ch] * (run - 1))
            else:
                buffer += ch * run
        if buffer:
            word_tokens.append(buffer)
        if not word_tokens:
            continue
        word_tokens[0] = (" " if wi > 0 else "") + word_tokens[0]
        tokens.extend(word_tokens)
    return tokens


def _wrap_text(text, font, max_width):
    words = text.split()
    lines, current = [], ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if font.size(candidate)[0] <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _wrap_x(x):
    """A ship that crosses one screen edge reappears at the other, same
    height, still moving the same direction — applied to every ship
    (player, Swarm, Launcher), never to lasers or particles."""
    if x < 0:
        return x + SCREEN_WIDTH
    if x > SCREEN_WIDTH:
        return x - SCREEN_WIDTH
    return x


def _move_toward(current, target, speed, dt):
    """Steps `current` toward `target` at `speed` px/s, clamped so it lands
    exactly on `target` instead of overshooting — used for the cutscene's
    auto-piloted ship movement (no player input involved)."""
    diff = target - current
    step = speed * dt
    if abs(diff) <= step:
        return target
    return current + step * (1 if diff > 0 else -1)


_sfx_cache = {}


def _load_sfx(path, synth_fn):
    """Generate `path` via `synth_fn` if it doesn't exist yet, then load and
    cache it as a pygame.mixer.Sound — same lazy, generate-then-cache shape
    as _load_image above, just for audio. Returns None if the audio backend
    isn't available (matches game.py's own defensive handling)."""
    if path not in _sfx_cache:
        if not os.path.exists(path):
            synth_fn(path)
        try:
            _sfx_cache[path] = pygame.mixer.Sound(path)
        except pygame.error:
            _sfx_cache[path] = None
    return _sfx_cache[path]


class SpaceWarsScene(Scene):
    def __init__(self, on_finish=None, rng_seed=None, stage="1-1", starting_score=0,
                 starting_lives=STARTING_EXTRA_LIVES, starting_life_bonus_threshold=LIFE_BONUS_INTERVAL,
                 starting_charge_unlocked=False, starting_friendly_shield_visible=True):
        self.on_finish = on_finish
        self.rng = random.Random(rng_seed)

        self.stage = stage
        self.stage_config = STAGES[stage]

        self.player_x = SCREEN_WIDTH / 2
        self.player_y = BASE_Y
        self.shot_cooldown = 0.0
        self.invulnerable_timer = 0.0
        self.lives_remaining = starting_lives
        self.score = starting_score
        self.next_life_bonus_threshold = starting_life_bonus_threshold
        self.life_bonus_flash_timer = 0.0

        self.player_lasers = []
        self.enemy_lasers = []
        self.particles = []

        self.enemies, self.launchers, self.seekers, self.wave_bounds = self._build_waves()
        self.stage_enemy_count = len(self.enemies)  # ships added later (Launcher spawns) skip wave-gating
        self.released_waves = 1  # the first wave is always active from the start
        self.wave_timer = WAVE_DELAY  # only consulted when this stage's gate is "timer"
        self.wave_clear_timer = None  # only consulted when this stage's gate is "clear"; None = not yet cleared

        self.has_friendly = self.stage_config.get("friendly", False)
        self.friendly_x = self.player_x + FRIENDLY_OFFSET_X
        self.friendly_y = self.player_y
        self.friendly_shield_visible = starting_friendly_shield_visible
        self.friendly_depart_timer = 0.0  # only consulted in "friendly_departure"
        self.friendly_depart_speed = FRIENDLY_DEPART_SPEED
        self.friendly_scale = 1.0

        self.has_boss = self.stage_config.get("boss", False)
        self.boss = self._build_boss() if self.has_boss else None

        self.cutscene_timer = 0.0  # only consulted in "post_win_wait"
        self.dialogue_index = 0    # only consulted in "dialogue"
        self.dialogue_words_shown = 0    # how many tokens of the current line are revealed so far
        self.dialogue_reveal_timer = 0.0
        self.game_over_words_shown = 0   # same typewriter reveal, for the game-over reaction line
        self.game_over_reveal_timer = WORD_REVEAL_INTERVAL

        self.charge_unlocked = starting_charge_unlocked
        self.space_was_down = False       # edge-detection for the Charge Shot's tap-vs-hold behavior
        self.space_hold_time = 0.0
        self.charge_reveal_phase = None   # "flashing" | "revealed", only during "charge_reveal"
        self.charge_reveal_timer = 0.0

        self.boss_defeat_timer = 0.0      # only consulted in "boss_defeated"

        self.player_name = None           # set once the ending cutscene's name entry is confirmed
        self.name_text = ""
        self.name_key_x = 0
        self.name_key_y = 0
        self.name_focus = "keyboard"      # "keyboard" | "actions"
        self.name_action_index = 0

        # "playing" | "won" | "game_over" | "post_win_wait" | "friendly_arrival" |
        # "friendly_departure" | "transmission_prompt" | "dialogue" | "charge_reveal" |
        # "name_entry" | "boss_defeated"
        self.state = "playing"

        self.stars = [(self.rng.uniform(0, SCREEN_WIDTH), self.rng.uniform(0, SCREEN_HEIGHT))
                      for _ in range(STAR_COUNT)]

        self._font = None
        self._small_font = None
        self._dialogue_font = None

        self.player_laser_sfx = _load_sfx(PLAYER_LASER_SFX_PATH, synthesize_laser_shot)
        self.enemy_laser_sfx = _load_sfx(ENEMY_LASER_SFX_PATH, synthesize_enemy_laser_shot)
        self.explosion_sfx = _load_sfx(EXPLOSION_SFX_PATH, synthesize_explosion)
        self._play_music(SPACE_SOUNDTRACK_PATH, build_space_theme)

    def _build_waves(self):
        """Builds every Swarm ship, Launcher, and Seeker for the whole
        stage (or, for a "cycle"-gated stage, just its first wave —
        _update_enemies calls _build_wave_batch again to keep cycling
        through the rest forever). Returns (enemies, launchers, seekers,
        wave_bounds) where wave_bounds[i] is ((enemy_start, enemy_end),
        (launcher_start, launcher_end), (seeker_start, seeker_end)), the
        index ranges into `enemies`/`launchers`/`seekers` for wave i."""
        y_offset = BOSS_ENEMY_Y_OFFSET if self.stage_config.get("boss") else 0
        self._formation_y = FORMATION_Y + y_offset
        self._launcher_row_min = LAUNCHER_ROW_MIN + y_offset
        self._launcher_row_max = LAUNCHER_ROW_MAX + y_offset

        enemies = []
        launchers = []
        seekers = []
        wave_bounds = []
        waves = self.stage_config["waves"]
        if self.stage_config.get("gate") == "cycle":
            waves = waves[:1]  # only the first wave is built up front; the rest cycle in at runtime
        for wave in waves:
            wave_bounds.append(self._build_wave_batch(wave, enemies, launchers, seekers))
        return enemies, launchers, seekers, wave_bounds

    def _build_wave_batch(self, wave, enemies, launchers, seekers):
        """Builds one wave's worth of Swarm ships/Launchers/Seekers,
        appending them to the given lists, and returns its wave_bounds
        entry. A group's Swarm ships spawn evenly across their own
        horizontal band (FORMATION_LEFT..FORMATION_RIGHT split evenly
        among the wave's groups, with GROUP_GAP between adjacent bands —
        a single-group wave just gets the entire span) — but if a group
        has more Swarm ships than comfortably fit in one row at
        MIN_SWARM_SPACING, they auto-split into multiple rows stacked
        downward instead of overlapping. Launchers get their own, wider
        band (split across the full SCREEN_WIDTH the same way) since
        they're much bigger and need more room between each other.
        Seekers enter from a screen edge rather than a band, so they
        aren't scoped to a group's band at all."""
        enemy_start = len(enemies)
        launcher_start = len(launchers)
        seeker_start = len(seekers)
        groups = wave["groups"]
        band_width = (FORMATION_RIGHT - FORMATION_LEFT) / len(groups)
        # Launchers are big — spread across the full width (inset so the outermost ones
        # spawn fully on-screen instead of straddling the edge).
        launcher_span_left = LAUNCHER_SIZE / 2
        launcher_span_right = SCREEN_WIDTH - LAUNCHER_SIZE / 2
        launcher_band_width = (launcher_span_right - launcher_span_left) / len(groups)
        for gi, group in enumerate(groups):
            band_left = FORMATION_LEFT + gi * band_width
            band_right = band_left + band_width
            launcher_band_left = launcher_span_left + gi * launcher_band_width
            launcher_band_right = launcher_band_left + launcher_band_width
            if len(groups) > 1:
                band_left += GROUP_GAP / 2
                band_right -= GROUP_GAP / 2
                launcher_band_left += GROUP_GAP / 2
                launcher_band_right -= GROUP_GAP / 2

            swarm_count = group.get("swarm", 0)
            if swarm_count > 0:
                max_per_row = max(1, int(band_width / MIN_SWARM_SPACING) + 1)
                num_rows = math.ceil(swarm_count / max_per_row) if swarm_count > max_per_row else 1
                base, extra = divmod(swarm_count, num_rows)
                for row in range(num_rows):
                    row_count = base + (1 if row < extra else 0)
                    row_spacing = (band_right - band_left) / (row_count - 1) if row_count > 1 else 0
                    row_y = self._formation_y + row * SWARM_ROW_SPACING
                    for i in range(row_count):
                        x = band_left + i * row_spacing
                        stagger = self.rng.uniform(0, 1.5)
                        enemies.append(SwarmEnemy(x, row_y, stagger))

            launcher_count = group.get("launchers", 0)
            launcher_spacing = ((launcher_band_right - launcher_band_left) / (launcher_count - 1)
                                 if launcher_count > 1 else 0)
            for i in range(launcher_count):
                entry_x = launcher_band_left + i * launcher_spacing
                target_y = self.rng.uniform(self._launcher_row_min, self._launcher_row_max)
                launcher_rng = random.Random(self.rng.randint(0, 2**31 - 1))
                launchers.append(Launcher(entry_x, target_y, launcher_rng))

            for _ in range(group.get("seekers", 0)):
                entry_y = self.rng.uniform(self._launcher_row_min, self._launcher_row_max)
                from_left = self.rng.choice([True, False])
                entry_x = -SEEKER_ENTRY_MARGIN if from_left else SCREEN_WIDTH + SEEKER_ENTRY_MARGIN
                direction = 1 if from_left else -1
                seeker_rng = random.Random(self.rng.randint(0, 2**31 - 1))
                seekers.append(Seeker(entry_x, entry_y, direction, seeker_rng))

        return (
            (enemy_start, len(enemies)),
            (launcher_start, len(launchers)),
            (seeker_start, len(seekers)),
        )

    def _build_boss(self):
        boss_rng = random.Random(self.rng.randint(0, 2**31 - 1))
        return Boss(SCREEN_WIDTH / 2, BOSS_Y, boss_rng, max_hp=self.stage_config.get("boss_hp"))

    def _spawn_swarm_ship(self, x, y):
        self.enemies.append(SwarmEnemy(x, y, self.rng.uniform(0, 1.5), instant=True))

    def _play_music(self, path, build_fn):
        try:
            if not os.path.exists(path):
                build_fn(path)
            pygame.mixer.music.load(path)
            pygame.mixer.music.play(loops=-1)
        except pygame.error:
            pass

    # -- input --------------------------------------------------------------

    def handle_event(self, event, manager):
        if event.type != pygame.KEYDOWN:
            return

        if self.state == "name_entry":
            self._handle_name_entry_key(event)
            return

        if event.key != pygame.K_SPACE:
            return

        if self.state == "won":
            cutscene = self.stage_config.get("cutscene")
            if cutscene is not None:
                # a scripted beat plays before actually advancing — see update()/draw()
                self.player_lasers = []
                self.enemy_lasers = []
                self.state = "post_win_wait"
                self.cutscene_timer = cutscene["wait"]
                return
            self._begin_next_stage_transition(manager)

        elif self.state == "transmission_prompt":
            self.state = "dialogue"
            self._begin_dialogue_line(0)

        elif self.state == "dialogue":
            cutscene = self.stage_config["cutscene"]
            tokens = _reveal_tokens(self._format_line(cutscene["lines"][self.dialogue_index]))
            if self.dialogue_words_shown < len(tokens):
                self.dialogue_words_shown = len(tokens)  # first press completes the line instantly
                return
            if self.dialogue_index == cutscene.get("unlocks_charge_shot_after_line", -1) and not self.charge_unlocked:
                self.state = "charge_reveal"
                self.charge_reveal_phase = "flashing"
                self.charge_reveal_timer = CHARGE_REVEAL_FLASH_DURATION
                return
            if self.dialogue_index == cutscene.get("name_entry_after_line", -1) and self.player_name is None:
                self.state = "name_entry"
                return
            next_index = self.dialogue_index + 1
            if next_index >= len(cutscene["lines"]):
                if cutscene.get("friendly_departs") and self.has_friendly:
                    self.state = "friendly_departure"
                    self.friendly_depart_timer = 0.0
                    self.friendly_depart_speed = FRIENDLY_DEPART_SPEED
                    self.friendly_scale = 1.0
                else:
                    self._begin_next_stage_transition(manager)
            else:
                self._begin_dialogue_line(next_index)

        elif self.state == "game_over":
            # game over never auto-advances to a "next" stage, even if this
            # stage has one — it always just hands off to on_finish
            game_over_line = self.stage_config.get("game_over_line")
            if game_over_line is not None:
                tokens = _reveal_tokens(game_over_line["line"])
                if self.game_over_words_shown < len(tokens):
                    self.game_over_words_shown = len(tokens)  # first press completes it instantly
                    return
            self._finish_run(manager)

    def _begin_dialogue_line(self, index):
        self.dialogue_index = index
        self.dialogue_words_shown = 0
        self.dialogue_reveal_timer = WORD_REVEAL_INTERVAL

    def _format_line(self, line):
        if self.player_name is not None and "{name}" in line:
            return line.format(name=self.player_name)
        return line

    # -- name entry (D-Pad + Space on-screen keyboard) -------------------------

    def _handle_name_entry_key(self, event):
        if event.key in (pygame.K_LEFT, pygame.K_a):
            self._move_name_entry(-1, 0)
        elif event.key in (pygame.K_RIGHT, pygame.K_d):
            self._move_name_entry(1, 0)
        elif event.key in (pygame.K_UP, pygame.K_w):
            self._move_name_entry(0, -1)
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self._move_name_entry(0, 1)
        elif event.key == pygame.K_SPACE:
            self._confirm_name_entry()

    def _move_name_entry(self, dx, dy):
        if self.name_focus == "keyboard":
            if dy != 0:
                new_y = self.name_key_y + dy
                if 0 <= new_y < len(NAME_KEYBOARD_ROWS):
                    self.name_key_y = new_y
                    self.name_key_x = min(self.name_key_x, len(NAME_KEYBOARD_ROWS[new_y]) - 1)
                elif new_y >= len(NAME_KEYBOARD_ROWS):
                    self.name_focus = "actions"
            else:
                row = NAME_KEYBOARD_ROWS[self.name_key_y]
                self.name_key_x = max(0, min(len(row) - 1, self.name_key_x + dx))
        else:  # "actions"
            if dy < 0:
                self.name_focus = "keyboard"
            elif dx != 0:
                self.name_action_index = max(0, min(len(NAME_ACTIONS) - 1, self.name_action_index + dx))

    def _confirm_name_entry(self):
        if self.name_focus == "keyboard":
            char = NAME_KEYBOARD_ROWS[self.name_key_y][self.name_key_x]
            if len(self.name_text) < NAME_ENTRY_MAX_LENGTH:
                self.name_text += char
            return
        action = NAME_ACTIONS[self.name_action_index]
        if action == "Del":
            self.name_text = self.name_text[:-1]
        else:  # "Done"
            self.player_name = self.name_text or NAME_DEFAULT
            self.state = "dialogue"
            self._begin_dialogue_line(self.dialogue_index + 1)

    def _begin_next_stage_transition(self, manager):
        """Called once a win (and any cutscene after it) is fully done.
        If the stage we're headed into introduces a Friendly wingman that
        this stage didn't already have, play its "flies down to join" beat
        first; otherwise advance immediately (this covers both stages with
        no wingman at all, and a stage-to-stage continuation where the
        wingman is already flying alongside and shouldn't re-enter)."""
        next_stage = self.stage_config["next"]
        if (next_stage is not None and STAGES[next_stage].get("friendly", False)
                and not self.has_friendly):
            self.state = "friendly_arrival"
            self.friendly_x = self.player_x + FRIENDLY_OFFSET_X
            self.friendly_y = -40.0  # off-screen above, like every ship's entrance in this game
            return
        self._advance_or_finish(manager)

    def _advance_or_finish(self, manager):
        next_stage = self.stage_config["next"]
        if next_stage is not None:
            manager.replace(SpaceWarsScene(
                on_finish=self.on_finish, stage=next_stage, starting_score=self.score,
                starting_lives=self.lives_remaining, starting_life_bonus_threshold=self.next_life_bonus_threshold,
                starting_charge_unlocked=self.charge_unlocked,
                starting_friendly_shield_visible=self.friendly_shield_visible))
            return
        self._finish_run(manager)

    def _finish_run(self, manager):
        if self.on_finish is not None:
            self._play_music(FOREST_SOUNDTRACK_PATH, build_forest_theme)
            self.on_finish(manager, self)

    def update(self, dt, keys, manager):
        self._update_particles(dt)

        if self.state == "post_win_wait":
            # control is taken away — the ship (and, for a boss stage, the
            # Boss too) auto-pilots to center
            target_y = CUTSCENE_PLAYER_Y if self.has_boss else BASE_Y
            self.player_x = _move_toward(self.player_x, SCREEN_WIDTH / 2, AUTOPILOT_SPEED, dt)
            self.player_y = _move_toward(self.player_y, target_y, AUTOPILOT_SPEED, dt)
            if self.has_friendly:
                self.friendly_x = _wrap_x(self.player_x + FRIENDLY_OFFSET_X)
                self.friendly_y = self.player_y
            if self.boss is not None:
                self.boss.x = _move_toward(self.boss.x, SCREEN_WIDTH / 2, AUTOPILOT_SPEED, dt)
                self.boss.y = _move_toward(self.boss.y, CUTSCENE_BOSS_Y, AUTOPILOT_SPEED, dt)
            self.cutscene_timer -= dt
            if self.cutscene_timer <= 0:
                self.state = "transmission_prompt"
            return

        if self.state == "friendly_arrival":
            self.friendly_y = _move_toward(self.friendly_y, self.player_y, AUTOPILOT_SPEED, dt)
            if self.friendly_y >= self.player_y:
                self._advance_or_finish(manager)
            return

        if self.state == "friendly_departure":
            self.friendly_depart_timer += dt
            self.friendly_depart_speed += FRIENDLY_DEPART_ACCEL * dt
            self.friendly_y += self.friendly_depart_speed * dt
            shrink_progress = min(1.0, self.friendly_depart_timer / FRIENDLY_DEPART_SHRINK_DURATION)
            self.friendly_scale = 1.0 - (1.0 - FRIENDLY_DEPART_MIN_SCALE) * shrink_progress
            if self.friendly_y > SCREEN_HEIGHT + FRIENDLY_SIZE:
                self.has_friendly = False
                self._begin_next_stage_transition(manager)
            return

        if self.state == "charge_reveal":
            self.charge_reveal_timer -= dt
            if self.charge_reveal_phase == "flashing":
                if self.charge_reveal_timer <= 0:
                    self.charge_reveal_phase = "revealed"
                    self.friendly_shield_visible = False
                    self.charge_unlocked = True
                    self.charge_reveal_timer = CHARGE_REVEAL_PAUSE
            else:  # "revealed"
                if self.charge_reveal_timer <= 0:
                    self.state = "dialogue"
                    self._begin_dialogue_line(self.dialogue_index + 1)
            return

        if self.state == "name_entry":
            return  # purely event-driven — see _handle_name_entry_key

        if self.state == "boss_defeated":
            self.boss_defeat_timer -= dt
            if self.boss_defeat_timer <= 0:
                self.state = "won"
            return

        if self.state == "dialogue":
            line = self._format_line(self.stage_config["cutscene"]["lines"][self.dialogue_index])
            tokens = _reveal_tokens(line)
            if self.dialogue_words_shown < len(tokens):
                self.dialogue_reveal_timer -= dt
                if self.dialogue_reveal_timer <= 0:
                    self.dialogue_words_shown += 1
                    self.dialogue_reveal_timer = WORD_REVEAL_INTERVAL
            return

        if self.state == "game_over":
            game_over_line = self.stage_config.get("game_over_line")
            if game_over_line is not None:
                tokens = _reveal_tokens(game_over_line["line"])
                if self.game_over_words_shown < len(tokens):
                    self.game_over_reveal_timer -= dt
                    if self.game_over_reveal_timer <= 0:
                        self.game_over_words_shown += 1
                        self.game_over_reveal_timer = WORD_REVEAL_INTERVAL
            return

        if self.state in ("won", "transmission_prompt"):
            return

        if self.invulnerable_timer > 0:
            self.invulnerable_timer = max(0.0, self.invulnerable_timer - dt)
        if self.life_bonus_flash_timer > 0:
            self.life_bonus_flash_timer = max(0.0, self.life_bonus_flash_timer - dt)

        self._update_player_movement(dt, keys)
        self._update_player_shooting(dt, keys)
        self._update_lasers(dt)
        self._update_enemies(dt)
        self._update_launchers(dt)
        self._update_seekers(dt)
        self._update_boss(dt)
        self._check_collisions()
        self._check_win()

    def _update_player_movement(self, dt, keys):
        dx = dy = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            dx -= 1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            dx += 1
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            dy -= 1
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            dy += 1
        self.player_x += dx * PLAYER_SPEED * dt
        self.player_y += dy * PLAYER_SPEED * dt
        self.player_x = _wrap_x(self.player_x)
        self.player_y = max(BASE_Y - VERTICAL_MOVEMENT, min(BASE_Y, self.player_y))

        if self.has_friendly:
            self.friendly_x = _wrap_x(self.player_x + FRIENDLY_OFFSET_X)
            self.friendly_y = self.player_y

    def _update_player_shooting(self, dt, keys):
        if self.shot_cooldown > 0:
            self.shot_cooldown -= dt

        space_down = keys[pygame.K_SPACE]
        just_pressed = space_down and not self.space_was_down
        just_released = (not space_down) and self.space_was_down
        self.space_was_down = space_down

        if not self.charge_unlocked:
            # today's behavior, unaffected: hold = continuous rapid-fire
            if space_down and self.shot_cooldown <= 0:
                self._fire_normal_shot()
            return

        if just_pressed:
            if self.shot_cooldown <= 0:
                self._fire_normal_shot()
            self.space_hold_time = 0.0
            return

        if space_down:
            # held past the initial tap: no repeated normal shots — instead,
            # charge up (capped — the shot fires on release, not automatically)
            self.space_hold_time = min(CHARGE_INTERVAL, self.space_hold_time + dt)
            return

        if just_released:
            if self.space_hold_time >= CHARGE_INTERVAL:
                self._fire_charge_shot()
            self.space_hold_time = 0.0

    def _fire_normal_shot(self):
        self.player_lasers.append({"x": self.player_x, "y": self.player_y - PLAYER_SIZE / 2})
        if self.has_friendly:
            self.player_lasers.append({"x": self.friendly_x, "y": self.friendly_y - FRIENDLY_SIZE / 2})
        self.shot_cooldown = COOLDOWN_TIME
        self.score = max(0, self.score - SCORE_PER_SHOT)
        if self.player_laser_sfx is not None:
            self.player_laser_sfx.play()
        for seeker in self.seekers:
            if seeker.state != DONE:
                seeker.notify_shot(self.player_x, self.player_y)

    def _fire_charge_shot(self):
        self.player_lasers.append({
            "x": self.player_x, "y": self.player_y - PLAYER_SIZE / 2,
            "speed": CHARGE_SHOT_SPEED, "charge": True,
        })
        self.score = max(0, self.score - SCORE_PER_SHOT)
        if self.player_laser_sfx is not None:
            self.player_laser_sfx.play()
        for seeker in self.seekers:
            if seeker.state != DONE:
                seeker.notify_shot(self.player_x, self.player_y)

    def _update_lasers(self, dt):
        for laser in self.player_lasers:
            laser["y"] -= laser.get("speed", LASER_SPEED) * dt
            if laser.get("charge"):
                self._spawn_charge_trail_particle(laser["x"], laser["y"])
        self.player_lasers = [l for l in self.player_lasers if l["y"] > -20]

        for laser in self.enemy_lasers:
            laser["x"] += laser["vx"] * dt
            laser["y"] += laser["vy"] * dt
        self.enemy_lasers = [l for l in self.enemy_lasers if l["y"] < SCREEN_HEIGHT + 20]

    def _enemies_active_end(self):
        return self.wave_bounds[self.released_waves - 1][0][1] if self.wave_bounds else 0

    def _update_enemies(self, dt):
        gate = self.stage_config["gate"]
        if gate == "timer":
            if self.wave_bounds and self.released_waves < len(self.wave_bounds):
                self.wave_timer -= dt
                if self.wave_timer <= 0:
                    self.released_waves += 1
                    self.wave_timer = WAVE_DELAY
        else:  # "clear" or "cycle" — next wave waits until the previous one (ships, Launchers,
               # Seekers) is fully gone, then an extra pause (WAVE_CLEAR_INTERVAL). "clear" stops
               # once every precomputed wave has released; "cycle" has no such stopping point —
               # it builds the next wave in the loop fresh, on demand, forever.
            still_has_more = gate == "cycle" or self.released_waves < len(self.wave_bounds)
            if still_has_more:
                (e_start, e_end), (l_start, l_end), (sk_start, sk_end) = self.wave_bounds[self.released_waves - 1]
                enemies_done = all(e.state == DONE for e in self.enemies[e_start:e_end])
                launchers_done = all(l.state == DONE for l in self.launchers[l_start:l_end])
                seekers_done = all(s.state == DONE for s in self.seekers[sk_start:sk_end])
                if enemies_done and launchers_done and seekers_done:
                    if self.wave_clear_timer is None:
                        self.wave_clear_timer = WAVE_CLEAR_INTERVAL
                    self.wave_clear_timer -= dt
                    if self.wave_clear_timer <= 0:
                        self.wave_clear_timer = None
                        if gate == "cycle":
                            waves = self.stage_config["waves"]
                            next_wave = waves[self.released_waves % len(waves)]
                            self.wave_bounds.append(
                                self._build_wave_batch(next_wave, self.enemies, self.launchers, self.seekers))
                        self.released_waves += 1
                else:
                    self.wave_clear_timer = None
        enemies_active_end = self._enemies_active_end()

        for i, enemy in enumerate(self.enemies):
            if enemy.state == DONE:
                continue
            if i < self.stage_enemy_count and i >= enemies_active_end:
                continue  # part of this stage's original waves, not yet released
            shots = enemy.update(dt, self.player_x, self.player_y)
            for (sx, sy) in shots:
                self.enemy_lasers.append({"x": sx, "y": sy, "vx": 0.0, "vy": ENEMY_LASER_SPEED})
                if self.enemy_laser_sfx is not None:
                    self.enemy_laser_sfx.play()
            enemy.x = _wrap_x(enemy.x)
            if enemy.state == DIVING and enemy.y > SCREEN_HEIGHT + 40:
                enemy.state = DONE
                self._spawn_particles(enemy.x, SCREEN_HEIGHT - 10, PARTICLE_COUNT_ENEMY)

    def _launchers_active_end(self):
        return self.wave_bounds[self.released_waves - 1][1][1] if self.wave_bounds else 0

    def _update_launchers(self, dt):
        launchers_active_end = self._launchers_active_end()

        for i, launcher in enumerate(self.launchers):
            if launcher.state == DONE:
                continue
            if i >= launchers_active_end:
                continue  # part of a later wave that hasn't been released yet
            shots, spawn_requested = launcher.update(dt)
            for (sx, sy, dx, dy) in shots:
                self.enemy_lasers.append({
                    "x": sx, "y": sy,
                    "vx": dx * ENEMY_LASER_SPEED, "vy": dy * ENEMY_LASER_SPEED,
                })
                if self.enemy_laser_sfx is not None:
                    self.enemy_laser_sfx.play()
            if spawn_requested:
                for _ in range(LAUNCHER_SPAWN_COUNT):
                    self._spawn_swarm_ship(launcher.x, launcher.y)
            launcher.x = _wrap_x(launcher.x)

    def _seekers_active_end(self):
        return self.wave_bounds[self.released_waves - 1][2][1] if self.wave_bounds else 0

    def _update_seekers(self, dt):
        seekers_active_end = self._seekers_active_end()

        for i, seeker in enumerate(self.seekers):
            if seeker.state == DONE:
                continue
            if i >= seekers_active_end:
                continue  # part of a later wave that hasn't been released yet
            shots = seeker.update(dt)
            for (sx, sy, dx, dy) in shots:
                self.enemy_lasers.append({
                    "x": sx, "y": sy,
                    "vx": dx * ENEMY_LASER_SPEED, "vy": dy * ENEMY_LASER_SPEED,
                })
                if self.enemy_laser_sfx is not None:
                    self.enemy_laser_sfx.play()
            seeker.x = _wrap_x(seeker.x)
            if seeker.y >= SCREEN_HEIGHT * SEEKER_BOTTOM_BAND:
                burst = seeker.explode()
                for (sx, sy, dx, dy) in burst:
                    self.enemy_lasers.append({
                        "x": sx, "y": sy,
                        "vx": dx * ENEMY_LASER_SPEED, "vy": dy * ENEMY_LASER_SPEED,
                        "shape": "square",  # a radial burst reads as mine-like shrapnel, not a laser line
                    })
                if self.enemy_laser_sfx is not None:
                    self.enemy_laser_sfx.play()
                self._spawn_particles(seeker.x, seeker.y, PARTICLE_COUNT_ENEMY)

    def _update_boss(self, dt):
        if self.boss is None:
            return
        shots = self.boss.update(dt, BOSS_SIZE / 2, SCREEN_WIDTH - BOSS_SIZE / 2)
        for (sx, sy, dx, dy, kind) in shots:
            laser = {"x": sx, "y": sy, "vx": dx * ENEMY_LASER_SPEED, "vy": dy * ENEMY_LASER_SPEED}
            if kind == "bomb":
                laser["shape"] = "square"  # reads as a dropped mine/bomb, not a laser line
            self.enemy_lasers.append(laser)
        if shots and self.enemy_laser_sfx is not None:
            self.enemy_laser_sfx.play()

    def _active_targets(self):
        """Enemies/Launchers/Seekers currently released for this stage.
        A not-yet-released one (waiting for a later wave) sits off-screen
        and isn't drawn — it's excluded here too, so a laser passing
        through that off-screen spot can't hit something the player can't
        even see yet, and it can't hit the player either."""
        enemies_active_end = self._enemies_active_end()
        launchers_active_end = self._launchers_active_end()
        seekers_active_end = self._seekers_active_end()
        targets = [e for i, e in enumerate(self.enemies)
                   if not (i < self.stage_enemy_count and i >= enemies_active_end)]
        targets += [l for i, l in enumerate(self.launchers) if i < launchers_active_end]
        targets += [s for i, s in enumerate(self.seekers) if i < seekers_active_end]
        return targets

    def _check_collisions(self):
        active_targets = self._active_targets()
        for laser in list(self.player_lasers):
            is_charge = laser.get("charge", False)
            for target in active_targets:
                if target.state == DONE:
                    continue
                is_launcher = isinstance(target, Launcher)
                shielded = is_launcher and target.shield_active
                hit_radius = LAUNCHER_SHIELD_RADIUS if shielded else (
                    LAUNCHER_HIT_RADIUS_ENEMY if is_launcher else HIT_RADIUS_ENEMY)
                if _dist(laser["x"], laser["y"], target.x, target.y) < hit_radius:
                    if shielded:
                        target.shield_active = False  # shield absorbs this hit; ship untouched
                    else:
                        target.state = DONE
                        self.score += _score_for_kill(target)
                        self._check_life_bonus()
                        self._spawn_particles(target.x, target.y, PARTICLE_COUNT_ENEMY)
                    if is_charge:
                        continue  # a charge shot pierces through — keeps flying, hits everything in its path
                    if laser in self.player_lasers:
                        self.player_lasers.remove(laser)
                    break

        self._check_boss_hits()

        if self.invulnerable_timer > 0:
            return  # fresh respawn — can't be hit right now, but can still shoot

        for laser in list(self.enemy_lasers):
            if _dist(laser["x"], laser["y"], self.player_x, self.player_y) < HIT_RADIUS_PLAYER:
                self.enemy_lasers.remove(laser)
                self._on_player_hit()
                return

        for target in active_targets:
            if target.state == DONE:
                continue
            hit_radius = LAUNCHER_HIT_RADIUS_PLAYER if isinstance(target, Launcher) else HIT_RADIUS_PLAYER
            if _dist(target.x, target.y, self.player_x, self.player_y) < hit_radius:
                target.state = DONE
                self._spawn_particles(target.x, target.y, PARTICLE_COUNT_ENEMY)
                self._on_player_hit()
                return

    def _check_boss_hits(self):
        """The Boss is never in _active_targets() — it's handled entirely
        separately here. Only a charge shot can affect its shield; once
        the shield is fully gone, any shot (normal or charge) damages its
        HP, if it has one (stage 1's Boss has no max_hp, so this is a
        permanent no-op for it)."""
        if self.boss is None:
            return
        for laser in list(self.player_lasers):
            is_charge = laser.get("charge", False)
            if not self.boss.shield_removed:
                if not is_charge or laser.get("hit_boss_shield"):
                    continue
                if _dist(laser["x"], laser["y"], self.boss.x, self.boss.y) < BOSS_SHIELD_RADIUS:
                    self.boss.hit_shield()
                    laser["hit_boss_shield"] = True
            elif self.boss.max_hp is not None and not self.boss.defeated:
                if laser.get("hit_boss_body"):
                    continue
                if _dist(laser["x"], laser["y"], self.boss.x, self.boss.y) < BOSS_SIZE / 2:
                    self.boss.damage(CHARGE_SHOT_DAMAGE if is_charge else NORMAL_SHOT_DAMAGE)
                    if is_charge:
                        laser["hit_boss_body"] = True  # keeps piercing, but only counts once
                    elif laser in self.player_lasers:
                        self.player_lasers.remove(laser)

    def _check_win(self):
        if self.boss is not None and self.boss.max_hp is not None:
            # boss-HP stages never win by clearing waves — they cycle forever
            # until the boss itself is defeated (checked here instead)
            if self.boss.defeated:
                self._begin_boss_defeat_sequence()
            return
        if (all(e.state == DONE for e in self.enemies)
                and all(l.state == DONE for l in self.launchers)
                and all(s.state == DONE for s in self.seekers)):
            self.state = "won"

    def _begin_boss_defeat_sequence(self):
        for target in itertools.chain(self.enemies, self.launchers, self.seekers):
            if target.state != DONE:
                target.state = DONE
                self._spawn_particles(target.x, target.y, PARTICLE_COUNT_ENEMY)  # explodes harmlessly, no score
        self._spawn_particles(self.boss.x, self.boss.y, BOSS_EXPLOSION_PARTICLE_COUNT)
        self.state = "boss_defeated"
        self.boss_defeat_timer = BOSS_DEFEAT_DURATION

    def _check_life_bonus(self):
        """Grants an extra life every LIFE_BONUS_INTERVAL points (3000,
        6000, 9000, ...). The threshold only ever moves forward, so losing
        points afterward (e.g. from shooting) can't re-cross an
        already-passed threshold and cheese another life out of the same
        milestone."""
        while self.score >= self.next_life_bonus_threshold:
            self.lives_remaining += 1
            self.next_life_bonus_threshold += LIFE_BONUS_INTERVAL
            self.life_bonus_flash_timer = LIFE_BONUS_FLASH_DURATION

    # -- player death ---------------------------------------------------------

    def _on_player_hit(self):
        """Instant arcade-style respawn: burst plays, and (if a life remains)
        a new ship appears immediately right where the old one died,
        invulnerable and flashing for INVULNERABLE_DURATION — no dead time
        with nothing on screen, and no snapping back to center."""
        self._spawn_particles(self.player_x, self.player_y, PARTICLE_COUNT_PLAYER)

        if self.lives_remaining > 0:
            self.lives_remaining -= 1
            self.player_lasers = []
            self.enemy_lasers = []
            self.invulnerable_timer = INVULNERABLE_DURATION
        else:
            self.state = "game_over"

    # -- particles ------------------------------------------------------------

    def _spawn_particles(self, x, y, count):
        if self.explosion_sfx is not None:
            self.explosion_sfx.play()
        for _ in range(count):
            angle = self.rng.uniform(0, 2 * math.pi)
            speed = self.rng.uniform(PARTICLE_SPEED * 0.4, PARTICLE_SPEED)
            self.particles.append({
                "x": x, "y": y,
                "vx": math.cos(angle) * speed, "vy": math.sin(angle) * speed,
                "age": 0.0,
            })

    def _spawn_charge_trail_particle(self, x, y):
        angle = self.rng.uniform(0, 2 * math.pi)
        speed = self.rng.uniform(10, 40)
        self.particles.append({
            "x": x + self.rng.uniform(-CHARGE_TRAIL_PARTICLE_SPREAD, CHARGE_TRAIL_PARTICLE_SPREAD),
            "y": y + self.rng.uniform(-CHARGE_TRAIL_PARTICLE_SPREAD, CHARGE_TRAIL_PARTICLE_SPREAD),
            "vx": math.cos(angle) * speed, "vy": math.sin(angle) * speed,
            "age": 0.0, "lifetime": CHARGE_TRAIL_PARTICLE_LIFETIME,
            "color": CHARGE_SHOT_COLOR, "size": CHARGE_TRAIL_PARTICLE_SIZE,
        })

    def _update_particles(self, dt):
        for p in self.particles:
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            p["age"] += dt
        self.particles = [p for p in self.particles if p["age"] < p.get("lifetime", PARTICLE_LIFETIME)]

    # -- drawing --------------------------------------------------------------

    def draw(self, surface):
        if self._font is None:
            self._font = pygame.font.SysFont(None, 34)
            self._small_font = pygame.font.SysFont(None, 20)
            self._dialogue_font = pygame.font.SysFont(None, DIALOGUE_FONT_SIZE)

        surface.fill(BG_COLOR)
        for (sx, sy) in self.stars:
            surface.set_at((int(sx), int(sy)), STAR_COLOR)

        self._draw_boss(surface)
        self._draw_enemies(surface)
        self._draw_lasers(surface)
        self._draw_player(surface)
        if self.has_friendly or self.state in ("friendly_arrival", "friendly_departure"):
            self._draw_friendly(surface)
        self._draw_particles(surface)
        self._draw_hud(surface)
        if self.has_boss and self.boss is not None and self.boss.max_hp is not None:
            self._draw_boss_health_bar(surface)
        if self.charge_unlocked:
            self._draw_charge_meter(surface)

        if self.state == "won":
            next_stage = self.stage_config["next"]
            hint = f"SPACE for Stage {next_stage}" if next_stage else "SPACE to continue"
            self._draw_end_box(surface, f"Stage {self.stage} Clear!", hint)
        elif self.state == "game_over":
            self._draw_end_box(surface, "GAME OVER")
            game_over_line = self.stage_config.get("game_over_line")
            if game_over_line is not None:
                self._draw_dialogue_box(surface, game_over_line["speaker"], game_over_line["line"],
                                         words_shown=self.game_over_words_shown)
        elif self.state == "transmission_prompt":
            cutscene = self.stage_config["cutscene"]
            self._draw_end_box(surface, cutscene["transmission_text"], "Spacebar to Accept")
        elif self.state == "dialogue":
            cutscene = self.stage_config["cutscene"]
            line = self._format_line(cutscene["lines"][self.dialogue_index])
            self._draw_dialogue_box(surface, cutscene["speaker"], line, words_shown=self.dialogue_words_shown)
        elif self.state == "name_entry":
            self._draw_name_entry(surface)
        elif self.state == "boss_defeated":
            self._draw_boss_defeat_flash(surface)

    def _draw_enemies(self, surface):
        image = _load_image("ENEMY01", ENEMY_SIZE)
        for enemy in self.enemies:
            if enemy.state == DONE:
                continue
            surface.blit(image, image.get_rect(center=(enemy.x, enemy.y)))

        launcher_image = _load_image("ENEMY02", LAUNCHER_SIZE)
        launchers_active_end = self._launchers_active_end()
        for i, launcher in enumerate(self.launchers):
            if launcher.state == DONE:
                continue
            if i >= launchers_active_end:
                continue  # not yet released — stays fully hidden, not just off-screen
            if launcher.shield_active:
                self._draw_shield(surface, launcher.x, launcher.y, LAUNCHER_SHIELD_RADIUS)
            surface.blit(launcher_image, launcher_image.get_rect(center=(launcher.x, launcher.y)))

        seeker_image = _load_image("ENEMY03", ENEMY_SIZE)
        seekers_active_end = self._seekers_active_end()
        for i, seeker in enumerate(self.seekers):
            if seeker.state == DONE:
                continue
            if i >= seekers_active_end:
                continue  # not yet released — stays fully hidden, not just off-screen
            surface.blit(seeker_image, seeker_image.get_rect(center=(seeker.x, seeker.y)))

    def _draw_shield(self, surface, x, y, radius, color=SHIELD_COLOR):
        radius = int(radius)
        size = radius * 2 + 4
        shield_surface = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(shield_surface, color, (size // 2, size // 2), radius, width=3)
        surface.blit(shield_surface, shield_surface.get_rect(center=(x, y)))

    def _draw_boss(self, surface):
        if self.boss is None or self.boss.defeated:
            return
        if not self.boss.shield_removed:
            if self.boss.shield_flash_timer > 0:
                blink_on = int(self.boss.shield_flash_timer / FLASH_INTERVAL) % 2 == 0
                if blink_on:
                    self._draw_shield(surface, self.boss.x, self.boss.y, BOSS_SHIELD_RADIUS,
                                       color=BOSS_SHIELD_COLOR_DAMAGED)
            else:
                color = BOSS_SHIELD_COLOR_DAMAGED if self.boss.shield_hits >= 1 else BOSS_SHIELD_COLOR
                self._draw_shield(surface, self.boss.x, self.boss.y, BOSS_SHIELD_RADIUS, color=color)
        image = _load_image("BOSS01", BOSS_SIZE)
        surface.blit(image, image.get_rect(center=(self.boss.x, self.boss.y)))

    def _draw_boss_health_bar(self, surface):
        if self.boss.defeated:
            return
        label = self._font.render("BOSS:", True, TEXT_COLOR)
        bar = pygame.Rect(0, 0, BOSS_HEALTH_BAR_WIDTH, BOSS_HEALTH_BAR_HEIGHT)
        total_width = label.get_width() + 12 + bar.width
        x = (SCREEN_WIDTH - total_width) // 2
        y = 12
        surface.blit(label, (x, y))
        bar.topleft = (x + label.get_width() + 12, y)
        pygame.draw.rect(surface, (20, 20, 20), bar)
        fraction = self.boss.hp / self.boss.max_hp
        fill = bar.copy()
        fill.width = int(bar.width * fraction)
        if fill.width > 0:
            pygame.draw.rect(surface, BOSS_HEALTH_BAR_COLOR, fill)
        pygame.draw.rect(surface, TEXT_COLOR, bar, 2)

    def _draw_boss_defeat_flash(self, surface):
        progress = 1.0 - (self.boss_defeat_timer / BOSS_DEFEAT_DURATION)
        alpha = int(BOSS_DEFEAT_FLASH_MAX_ALPHA * math.sin(min(1.0, max(0.0, progress)) * math.pi))
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((255, 255, 255, max(0, alpha)))
        surface.blit(overlay, (0, 0))

    def _draw_charge_meter(self, surface):
        box = pygame.Rect(0, 0, CHARGE_METER_WIDTH, CHARGE_METER_HEIGHT)
        box.midbottom = (SCREEN_WIDTH // 2, SCREEN_HEIGHT - CHARGE_METER_MARGIN_BOTTOM)
        pygame.draw.rect(surface, (20, 20, 20), box)
        progress = min(1.0, self.space_hold_time / CHARGE_INTERVAL)
        fill_width = int((box.width - 4) * progress)
        if fill_width > 0:
            fill_rect = pygame.Rect(box.left + 2, box.top + 2, fill_width, box.height - 4)
            pygame.draw.rect(surface, CHARGE_SHOT_COLOR, fill_rect)
        pygame.draw.rect(surface, TEXT_COLOR, box, 2)
        label = self._small_font.render("CHARGE", True, TEXT_COLOR)
        surface.blit(label, label.get_rect(midbottom=(box.centerx, box.top - 2)))

    def _draw_lasers(self, surface):
        for laser in self.player_lasers:
            if laser.get("charge"):
                pygame.draw.circle(surface, CHARGE_SHOT_COLOR,
                                    (int(laser["x"]), int(laser["y"])), CHARGE_SHOT_RADIUS)
                continue
            rect = pygame.Rect(0, 0, LASER_W, LASER_H)
            rect.center = (laser["x"], laser["y"])
            pygame.draw.rect(surface, PLAYER_LASER_COLOR, rect)
        for laser in self.enemy_lasers:
            if laser.get("shape") == "square":
                rect = pygame.Rect(0, 0, EXPLOSION_SHOT_SIZE, EXPLOSION_SHOT_SIZE)
            else:
                rect = pygame.Rect(0, 0, LASER_W, LASER_H)
            rect.center = (laser["x"], laser["y"])
            pygame.draw.rect(surface, ENEMY_LASER_COLOR, rect)

    def _draw_player(self, surface):
        if self.invulnerable_timer > 0:
            blink_on = int(self.invulnerable_timer / FLASH_INTERVAL) % 2 == 0
            if not blink_on:
                return
        image = _load_image("PLAYERSHIP", PLAYER_SIZE)
        surface.blit(image, image.get_rect(center=(self.player_x, self.player_y)))

    def _draw_friendly(self, surface):
        if self.friendly_shield_visible:
            show_shield = True
            if self.state == "charge_reveal" and self.charge_reveal_phase == "flashing":
                show_shield = int(self.charge_reveal_timer / FLASH_INTERVAL) % 2 == 0
            if show_shield:
                self._draw_shield(surface, self.friendly_x, self.friendly_y, FRIENDLY_SHIELD_RADIUS)
        size = max(4, int(FRIENDLY_SIZE * self.friendly_scale))
        image = _load_image("FRIENDLY01", size)
        surface.blit(image, image.get_rect(center=(self.friendly_x, self.friendly_y)))

    def _draw_particles(self, surface):
        for p in self.particles:
            size = p.get("size", PARTICLE_SIZE)
            rect = pygame.Rect(0, 0, size, size)
            rect.center = (p["x"], p["y"])
            pygame.draw.rect(surface, p.get("color", PARTICLE_COLOR), rect)

    def _draw_hud(self, surface):
        stage_label = self._font.render(f"Stage {self.stage}", True, TEXT_COLOR)
        surface.blit(stage_label, stage_label.get_rect(topright=(SCREEN_WIDTH - 16, 12)))

        flashing = self.life_bonus_flash_timer > 0
        blink_on = flashing and int(self.life_bonus_flash_timer / FLASH_INTERVAL) % 2 == 0
        score_color = LIFE_BONUS_FLASH_COLOR if blink_on else TEXT_COLOR
        score_label = self._font.render(f"SCORE: {self.score:04d}", True, score_color)
        score_rect = score_label.get_rect(topleft=(16, 12))
        surface.blit(score_label, score_rect)

        if blink_on:
            bonus_label = self._font.render("BONUS LIFE", True, LIFE_BONUS_FLASH_COLOR)
            surface.blit(bonus_label, (score_rect.right + 16, score_rect.top))

        life_image = _load_image("PLAYERSHIP", LIFE_ICON_SIZE)
        for i in range(self.lives_remaining):
            x = SCREEN_WIDTH - 16 - LIFE_ICON_SIZE / 2 - i * (LIFE_ICON_SIZE + 8)
            y = SCREEN_HEIGHT - 16 - LIFE_ICON_SIZE / 2
            surface.blit(life_image, life_image.get_rect(center=(x, y)))

    def _draw_end_box(self, surface, title, hint_text="SPACE to continue"):
        box = pygame.Rect(0, 0, 320, 120)
        box.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
        pygame.draw.rect(surface, (20, 20, 20), box)
        pygame.draw.rect(surface, TEXT_COLOR, box, 2)

        title_label = self._font.render(title, True, TEXT_COLOR)
        surface.blit(title_label, title_label.get_rect(midtop=(box.centerx, box.top + 16)))

        hint = self._small_font.render(hint_text, True, TEXT_COLOR)
        surface.blit(hint, hint.get_rect(midbottom=(box.centerx, box.bottom - 12)))

    def _draw_dialogue_box(self, surface, speaker, line, words_shown=None):
        """The bottom-anchored, full-width "incoming transmission" box: a
        square portrait on the left, speaker + word-wrapped line to its
        right — distinct from _draw_end_box, which is the small centered
        stage-clear/game-over/transmission-prompt box. `words_shown`, when
        given, reveals only that many of the line's _reveal_tokens (a
        typewriter effect, letter-by-letter through any stretched word like
        "Noooooo"); omit it to show the whole line at once."""
        box = pygame.Rect(DIALOGUE_BOX_MARGIN, SCREEN_HEIGHT - DIALOGUE_BOX_HEIGHT - DIALOGUE_BOX_MARGIN,
                           SCREEN_WIDTH - 2 * DIALOGUE_BOX_MARGIN, DIALOGUE_BOX_HEIGHT)
        pygame.draw.rect(surface, (20, 20, 20), box)
        pygame.draw.rect(surface, TEXT_COLOR, box, 2)

        portrait_rect = pygame.Rect(box.left, box.top, box.height, box.height)
        pygame.draw.rect(surface, TEXT_COLOR, portrait_rect, 2)
        self._draw_portrait(surface, portrait_rect)

        text_left = portrait_rect.right + 16
        text_width = box.right - text_left - 16

        speaker_label = self._small_font.render(speaker, True, TEXT_COLOR)
        y = box.top + 12
        surface.blit(speaker_label, (text_left, y))
        y += speaker_label.get_height() + 8

        tokens = _reveal_tokens(line)
        visible_text = "".join(tokens if words_shown is None else tokens[:words_shown])
        for wrapped_line in _wrap_text(visible_text, self._dialogue_font, text_width):
            label = self._dialogue_font.render(wrapped_line, True, TEXT_COLOR)
            surface.blit(label, (text_left, y))
            y += label.get_height() + 2

        hint = self._small_font.render("SPACE to continue", True, TEXT_COLOR)
        surface.blit(hint, hint.get_rect(bottomright=(box.right - 12, box.bottom - 10)))

    def _draw_portrait(self, surface, rect):
        """Just a head — the game's whole art style is a stick figure with
        no face (see stick_figure.py/dialogue.py), so a portrait is only
        ever a plain circle."""
        radius = rect.height * 0.32
        pygame.draw.circle(surface, NPC_PORTRAIT_COLOR, rect.center, int(radius))

    def _draw_name_entry(self, surface):
        prompt = self._small_font.render("Enter your name:", True, TEXT_COLOR)
        surface.blit(prompt, prompt.get_rect(midtop=(SCREEN_WIDTH // 2, NAME_KEYBOARD_TOP - 60)))

        name_box = pygame.Rect(0, 0, 220, 34)
        name_box.midtop = (SCREEN_WIDTH // 2, NAME_KEYBOARD_TOP - 40)
        pygame.draw.rect(surface, (20, 20, 20), name_box)
        pygame.draw.rect(surface, TEXT_COLOR, name_box, 2)
        name_label = self._font.render(self.name_text, True, TEXT_COLOR)
        surface.blit(name_label, name_label.get_rect(center=name_box.center))

        for row_i, row in enumerate(NAME_KEYBOARD_ROWS):
            for col_i, ch in enumerate(row):
                rect = pygame.Rect(NAME_KEYBOARD_LEFT + col_i * NAME_KEY_PX,
                                    NAME_KEYBOARD_TOP + row_i * NAME_KEY_PX,
                                    NAME_KEY_PX - 2, NAME_KEY_PX - 2)
                focused = self.name_focus == "keyboard" and self.name_key_x == col_i and self.name_key_y == row_i
                self._draw_name_key(surface, rect, ch, focused)

        for i, action in enumerate(NAME_ACTIONS):
            rect = pygame.Rect(0, 0, 90, 34)
            rect.topleft = (NAME_KEYBOARD_LEFT + i * 100, NAME_ACTIONS_Y)
            focused = self.name_focus == "actions" and self.name_action_index == i
            self._draw_name_key(surface, rect, action, focused)

    def _draw_name_key(self, surface, rect, label_text, focused):
        bg = SELECTED_KEY_COLOR if focused else (40, 40, 40)
        fg = (20, 20, 20) if focused else TEXT_COLOR
        pygame.draw.rect(surface, bg, rect)
        pygame.draw.rect(surface, TEXT_COLOR, rect, 1)
        label = self._small_font.render(label_text, True, fg)
        surface.blit(label, label.get_rect(center=rect.center))
