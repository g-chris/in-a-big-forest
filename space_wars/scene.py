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

from .enemies import DIVING, DONE, Launcher, SwarmEnemy

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
COOLDOWN_TIME = 0.25      # seconds between player shots — tune freely

LASER_SPEED = 420
ENEMY_LASER_SPEED = 260
LASER_W, LASER_H = 3, 16

FORMATION_Y = 110
FORMATION_LEFT = 140
FORMATION_RIGHT = 760
GROUP_GAP = 40            # horizontal gap between adjacent groups in a multi-group wave — tune freely
WAVE_DELAY = 3.0          # seconds before a "timer"-gated wave starts entering — tune freely

LAUNCHER_ROW_MIN = 60             # top of the Launcher's patrol band, in px
LAUNCHER_ROW_MAX = SCREEN_HEIGHT / 3  # "top third of the playing area"
LAUNCHER_SPAWN_COUNT = 2          # Swarm ships created per "spawn" action — tune freely

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
        # placeholder layout — just enough to test the cutscene + wingman;
        # the real stage 2-1 enemy design is a separate follow-up.
        "waves": [{"groups": [{"swarm": 4}]}, {"groups": [{"swarm": 4}]}],
        "gate": "timer", "next": None,
        "friendly": True,
        "game_over_line": {"speaker": "Bowling Alley Guy", "line": "Cowboy! Nooooooo !!"},
    },
}

SCORE_PER_KILL = 25       # points for a Swarm ship destroyed by a player laser
SCORE_PER_LAUNCHER_KILL = 150  # points for a Launcher destroyed by a player laser
SCORE_PER_SHOT = 1        # points deducted for each shot fired, floored at 0

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

DIALOGUE_BOX_MARGIN = 20  # inset from the screen edges — tune freely
DIALOGUE_BOX_HEIGHT = 140

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
    def __init__(self, on_finish=None, rng_seed=None, stage="1-1", starting_score=0):
        self.on_finish = on_finish
        self.rng = random.Random(rng_seed)

        self.stage = stage
        self.stage_config = STAGES[stage]

        self.player_x = SCREEN_WIDTH / 2
        self.player_y = BASE_Y
        self.shot_cooldown = 0.0
        self.invulnerable_timer = 0.0
        self.lives_remaining = STARTING_EXTRA_LIVES
        self.score = starting_score

        self.player_lasers = []
        self.enemy_lasers = []
        self.particles = []

        self.enemies, self.launchers, self.wave_bounds = self._build_waves()
        self.stage_enemy_count = len(self.enemies)  # ships added later (Launcher spawns) skip wave-gating
        self.released_waves = 1  # the first wave is always active from the start
        self.wave_timer = WAVE_DELAY  # only consulted when this stage's gate is "timer"

        self.has_friendly = self.stage_config.get("friendly", False)
        self.friendly_x = self.player_x + FRIENDLY_OFFSET_X
        self.friendly_y = self.player_y

        self.cutscene_timer = 0.0  # only consulted in "post_win_wait"
        self.dialogue_index = 0    # only consulted in "dialogue"

        # "playing" | "won" | "game_over" | "post_win_wait" | "transmission_prompt" | "dialogue"
        self.state = "playing"

        self.stars = [(self.rng.uniform(0, SCREEN_WIDTH), self.rng.uniform(0, SCREEN_HEIGHT))
                      for _ in range(STAR_COUNT)]

        self._font = None
        self._small_font = None

        self.player_laser_sfx = _load_sfx(PLAYER_LASER_SFX_PATH, synthesize_laser_shot)
        self.enemy_laser_sfx = _load_sfx(ENEMY_LASER_SFX_PATH, synthesize_enemy_laser_shot)
        self.explosion_sfx = _load_sfx(EXPLOSION_SFX_PATH, synthesize_explosion)
        self._play_music(SPACE_SOUNDTRACK_PATH, build_space_theme)

    def _build_waves(self):
        """Builds every Swarm ship and Launcher for the whole stage. Each
        wave is a list of groups; a group's ships spawn together in their
        own horizontal band (FORMATION_LEFT..FORMATION_RIGHT split evenly
        among that wave's groups, with GROUP_GAP between adjacent bands —
        a single-group wave just gets the entire span, unchanged from
        before). Returns (enemies, launchers, wave_bounds) where
        wave_bounds[i] is ((enemy_start, enemy_end), (launcher_start,
        launcher_end)), the index ranges into `enemies`/`launchers` for
        wave i."""
        enemies = []
        launchers = []
        wave_bounds = []
        for wave in self.stage_config["waves"]:
            enemy_start = len(enemies)
            launcher_start = len(launchers)
            groups = wave["groups"]
            band_width = (FORMATION_RIGHT - FORMATION_LEFT) / len(groups)
            for gi, group in enumerate(groups):
                band_left = FORMATION_LEFT + gi * band_width
                band_right = band_left + band_width
                if len(groups) > 1:
                    band_left += GROUP_GAP / 2
                    band_right -= GROUP_GAP / 2

                swarm_count = group.get("swarm", 0)
                spacing = (band_right - band_left) / (swarm_count - 1) if swarm_count > 1 else 0
                for i in range(swarm_count):
                    x = band_left + i * spacing
                    stagger = self.rng.uniform(0, 1.5)
                    enemies.append(SwarmEnemy(x, FORMATION_Y, stagger))

                for _ in range(group.get("launchers", 0)):
                    entry_x = self.rng.uniform(band_left, band_right)
                    target_y = self.rng.uniform(LAUNCHER_ROW_MIN, LAUNCHER_ROW_MAX)
                    launcher_rng = random.Random(self.rng.randint(0, 2**31 - 1))
                    launchers.append(Launcher(entry_x, target_y, launcher_rng))

            wave_bounds.append(((enemy_start, len(enemies)), (launcher_start, len(launchers))))
        return enemies, launchers, wave_bounds

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
        if event.type != pygame.KEYDOWN or event.key != pygame.K_SPACE:
            return

        if self.state == "won":
            cutscene = self.stage_config.get("cutscene")
            if cutscene is not None:
                # a scripted beat plays before actually advancing — see update()/draw()
                self.state = "post_win_wait"
                self.cutscene_timer = cutscene["wait"]
                return
            self._advance_or_finish(manager)

        elif self.state == "transmission_prompt":
            self.state = "dialogue"
            self.dialogue_index = 0

        elif self.state == "dialogue":
            self.dialogue_index += 1
            if self.dialogue_index >= len(self.stage_config["cutscene"]["lines"]):
                self._advance_or_finish(manager)

        elif self.state == "game_over":
            self._advance_or_finish(manager)

    def _advance_or_finish(self, manager):
        next_stage = self.stage_config["next"]
        if next_stage is not None:
            manager.replace(SpaceWarsScene(on_finish=self.on_finish, stage=next_stage, starting_score=self.score))
            return
        if self.on_finish is not None:
            self._play_music(FOREST_SOUNDTRACK_PATH, build_forest_theme)
            self.on_finish(manager, self)

    def update(self, dt, keys, manager):
        self._update_particles(dt)

        if self.state == "post_win_wait":
            self.cutscene_timer -= dt
            if self.cutscene_timer <= 0:
                self.state = "transmission_prompt"
            return

        if self.state in ("won", "game_over", "transmission_prompt", "dialogue"):
            return

        if self.invulnerable_timer > 0:
            self.invulnerable_timer = max(0.0, self.invulnerable_timer - dt)

        self._update_player_movement(dt, keys)
        self._update_player_shooting(dt, keys)
        self._update_lasers(dt)
        self._update_enemies(dt)
        self._update_launchers(dt)
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
        if keys[pygame.K_SPACE] and self.shot_cooldown <= 0:
            self.player_lasers.append({"x": self.player_x, "y": self.player_y - PLAYER_SIZE / 2})
            if self.has_friendly:
                self.player_lasers.append({"x": self.friendly_x, "y": self.friendly_y - FRIENDLY_SIZE / 2})
            self.shot_cooldown = COOLDOWN_TIME
            self.score = max(0, self.score - SCORE_PER_SHOT)
            if self.player_laser_sfx is not None:
                self.player_laser_sfx.play()

    def _update_lasers(self, dt):
        for laser in self.player_lasers:
            laser["y"] -= LASER_SPEED * dt
        self.player_lasers = [l for l in self.player_lasers if l["y"] > -20]

        for laser in self.enemy_lasers:
            laser["x"] += laser["vx"] * dt
            laser["y"] += laser["vy"] * dt
        self.enemy_lasers = [l for l in self.enemy_lasers if l["y"] < SCREEN_HEIGHT + 20]

    def _update_enemies(self, dt):
        enemies_active_end = 0
        if self.wave_bounds:
            if self.released_waves < len(self.wave_bounds):
                if self.stage_config["gate"] == "timer":
                    self.wave_timer -= dt
                    if self.wave_timer <= 0:
                        self.released_waves += 1
                        self.wave_timer = WAVE_DELAY
                else:  # "clear" — next wave waits until the previous one (ships AND Launchers) is fully gone
                    (e_start, e_end), (l_start, l_end) = self.wave_bounds[self.released_waves - 1]
                    enemies_done = all(e.state == DONE for e in self.enemies[e_start:e_end])
                    launchers_done = all(l.state == DONE for l in self.launchers[l_start:l_end])
                    if enemies_done and launchers_done:
                        self.released_waves += 1
            enemies_active_end = self.wave_bounds[self.released_waves - 1][0][1]

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

    def _check_collisions(self):
        for laser in list(self.player_lasers):
            for target in itertools.chain(self.enemies, self.launchers):
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
                        self.score += SCORE_PER_LAUNCHER_KILL if is_launcher else SCORE_PER_KILL
                        self._spawn_particles(target.x, target.y, PARTICLE_COUNT_ENEMY)
                    if laser in self.player_lasers:
                        self.player_lasers.remove(laser)
                    break

        if self.invulnerable_timer > 0:
            return  # fresh respawn — can't be hit right now, but can still shoot

        for laser in list(self.enemy_lasers):
            if _dist(laser["x"], laser["y"], self.player_x, self.player_y) < HIT_RADIUS_PLAYER:
                self.enemy_lasers.remove(laser)
                self._on_player_hit()
                return

        for target in itertools.chain(self.enemies, self.launchers):
            if target.state == DONE:
                continue
            hit_radius = LAUNCHER_HIT_RADIUS_PLAYER if isinstance(target, Launcher) else HIT_RADIUS_PLAYER
            if _dist(target.x, target.y, self.player_x, self.player_y) < hit_radius:
                target.state = DONE
                self._spawn_particles(target.x, target.y, PARTICLE_COUNT_ENEMY)
                self._on_player_hit()
                return

    def _check_win(self):
        if (all(e.state == DONE for e in self.enemies)
                and all(l.state == DONE for l in self.launchers)):
            self.state = "won"

    # -- player death ---------------------------------------------------------

    def _on_player_hit(self):
        """Instant arcade-style respawn: burst plays, and (if a life remains)
        a new ship appears immediately at the respawn point, invulnerable
        and flashing for INVULNERABLE_DURATION — no dead time with nothing
        on screen."""
        self._spawn_particles(self.player_x, self.player_y, PARTICLE_COUNT_PLAYER)

        if self.lives_remaining > 0:
            self.lives_remaining -= 1
            self.player_x = SCREEN_WIDTH / 2
            self.player_y = BASE_Y
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

    def _update_particles(self, dt):
        for p in self.particles:
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            p["age"] += dt
        self.particles = [p for p in self.particles if p["age"] < PARTICLE_LIFETIME]

    # -- drawing --------------------------------------------------------------

    def draw(self, surface):
        if self._font is None:
            self._font = pygame.font.SysFont(None, 34)
            self._small_font = pygame.font.SysFont(None, 20)

        surface.fill(BG_COLOR)
        for (sx, sy) in self.stars:
            surface.set_at((int(sx), int(sy)), STAR_COLOR)

        self._draw_enemies(surface)
        self._draw_lasers(surface)
        self._draw_player(surface)
        if self.has_friendly:
            self._draw_friendly(surface)
        self._draw_particles(surface)
        self._draw_hud(surface)

        if self.state == "won":
            next_stage = self.stage_config["next"]
            hint = f"SPACE for Stage {next_stage}" if next_stage else "SPACE to continue"
            self._draw_end_box(surface, f"Stage {self.stage} Clear!", hint)
        elif self.state == "game_over":
            self._draw_end_box(surface, "GAME OVER")
            game_over_line = self.stage_config.get("game_over_line")
            if game_over_line is not None:
                self._draw_dialogue_box(surface, game_over_line["speaker"], game_over_line["line"])
        elif self.state == "transmission_prompt":
            cutscene = self.stage_config["cutscene"]
            self._draw_end_box(surface, cutscene["transmission_text"], "Spacebar to Accept")
        elif self.state == "dialogue":
            cutscene = self.stage_config["cutscene"]
            self._draw_dialogue_box(surface, cutscene["speaker"], cutscene["lines"][self.dialogue_index])

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

    def _draw_shield(self, surface, x, y, radius):
        radius = int(radius)
        size = radius * 2 + 4
        shield_surface = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(shield_surface, SHIELD_COLOR, (size // 2, size // 2), radius, width=3)
        surface.blit(shield_surface, shield_surface.get_rect(center=(x, y)))

    def _draw_lasers(self, surface):
        for laser in self.player_lasers:
            rect = pygame.Rect(0, 0, LASER_W, LASER_H)
            rect.center = (laser["x"], laser["y"])
            pygame.draw.rect(surface, PLAYER_LASER_COLOR, rect)
        for laser in self.enemy_lasers:
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
        self._draw_shield(surface, self.friendly_x, self.friendly_y, FRIENDLY_SHIELD_RADIUS)
        image = _load_image("FRIENDLY01", FRIENDLY_SIZE)
        surface.blit(image, image.get_rect(center=(self.friendly_x, self.friendly_y)))

    def _draw_particles(self, surface):
        for p in self.particles:
            rect = pygame.Rect(0, 0, PARTICLE_SIZE, PARTICLE_SIZE)
            rect.center = (p["x"], p["y"])
            pygame.draw.rect(surface, PARTICLE_COLOR, rect)

    def _draw_hud(self, surface):
        stage_label = self._font.render(f"Stage {self.stage}", True, TEXT_COLOR)
        surface.blit(stage_label, stage_label.get_rect(topright=(SCREEN_WIDTH - 16, 12)))

        score_label = self._font.render(f"SCORE: {self.score:04d}", True, TEXT_COLOR)
        surface.blit(score_label, score_label.get_rect(topleft=(16, 12)))

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

    def _draw_dialogue_box(self, surface, speaker, line):
        """The bottom-anchored, full-width "incoming transmission" box: a
        square portrait on the left, speaker + word-wrapped line to its
        right — distinct from _draw_end_box, which is the small centered
        stage-clear/game-over/transmission-prompt box."""
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
        y += speaker_label.get_height() + 6

        for wrapped_line in _wrap_text(line, self._small_font, text_width):
            label = self._small_font.render(wrapped_line, True, TEXT_COLOR)
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
