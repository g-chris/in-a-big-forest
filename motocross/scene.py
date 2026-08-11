"""motocross/scene.py — the MotoCross mini-game screen. Top-down: the
player always moves forward, Space accelerates, Left/Right snap between
lanes (no free steering — the bike always occupies a whole lane). Holding
Left/Right keeps stepping through lanes one at a time at the same cadence,
so a long hold can cross multiple lanes in one motion. Up/Down shift gears
1-5 — each gear raises the top speed you can reach (MAX_SPEED) by a flat
amount; speed itself always changes gradually (never jumps on a shift), so
a higher gear just means more room to keep climbing while holding Space.
Track hazards
are a stationary Cactus and a moving Racer (see .obstacles); hitting either
drops speed to 0 and ramps it back up to BASE_SPEED over the current gear's
ACCEL_TIME, during which the player is flashing and Space is inert — same
penalty for both kinds, racers are just harder to deal with because they're
moving.
"""

import math
import random

import pygame

from cactus_icon import BODY_COLOR as CACTUS_COLOR
from cactus_icon import draw_cactus
from constants import SCREEN_HEIGHT, SCREEN_WIDTH
from racer_icon import draw_racer
from scene import Scene

from .obstacles import CACTUS, spawn_obstacles

LANE_COUNT = 5
TRACK_LEFT, TRACK_RIGHT = 300, 600
LANE_WIDTH = (TRACK_RIGHT - TRACK_LEFT) / LANE_COUNT
LANE_CENTERS = [TRACK_LEFT + LANE_WIDTH * (i + 0.5) for i in range(LANE_COUNT)]
START_LANE = LANE_COUNT // 2  # middle

PLAYER_Y = 480
PLAYER_HEIGHT = 50

BASE_SPEED = 250   # px/s equivalent "distance" — always-present forward crawl
MAX_SPEED = 500
ACCEL_TIME = 1.5   # seconds to ramp BASE -> MAX while holding Space
DECEL_TIME = 0.5   # seconds to ramp back down to BASE when released
LANE_CHANGE_TIME = 0.15  # seconds to glide from one lane center to the next
LANE_CHANGE_SPEED = LANE_WIDTH / LANE_CHANGE_TIME

TRACK_DISTANCE = 30000  # total distance to the finish line

DASH_LENGTH = 20
DASH_GAP = 20

RACER_SPEED_MULTIPLIER = 1.5  # vs. BASE_SPEED; tune after playing
HIT_WINDOW = 28               # px of screen-y tolerance for a collision
CACTUS_HEIGHT = 55
FLASH_INTERVAL = 0.1          # seconds per blink half-cycle

GEAR_COUNT = 5
START_GEAR = 1
GEAR_ACCEL_STEP = 0.5   # seconds to gain one gear-step's worth of top speed while accelerating
GEAR_MAX_SPEED_STEP = 300  # added to MAX_SPEED per gear above 1st
ACCEL_RATE = GEAR_MAX_SPEED_STEP / GEAR_ACCEL_STEP  # px/s^2 while holding Space, below the current gear's cap
ABSOLUTE_MAX_SPEED = MAX_SPEED + GEAR_MAX_SPEED_STEP * (GEAR_COUNT - 1)  # top of gear 5 — the speedometer's full scale

FINISH_LINE_HEIGHT = 30  # world-distance thickness of the checkered band
FINISH_CHECKER_COLS = 8

SPEEDO_RADIUS = 45
SPEEDO_CENTER = (SCREEN_WIDTH - 70, SCREEN_HEIGHT - 140)  # right side, above the gear box

BG_COLOR = (10, 40, 15)
TRACK_COLOR = (210, 180, 120)
DASH_COLOR = (140, 100, 60)
PLAYER_COLOR = (255, 220, 0)
TEXT_COLOR = (255, 255, 255)
HUD_BG = (20, 20, 20)
FLASH_COLOR = (255, 255, 255)
GEAR_BOX_COLOR = (255, 255, 255)
GEAR_TEXT_COLOR = (20, 20, 20)
FINISH_LIGHT_COLOR = (240, 240, 240)
FINISH_DARK_COLOR = (20, 20, 20)


class MotocrossScene(Scene):
    def __init__(self, on_finish=None, rng_seed=None):
        self.on_finish = on_finish

        self.lane = START_LANE
        self.x = LANE_CENTERS[self.lane]
        self.gear = START_GEAR  # 1..GEAR_COUNT
        self.distance_traveled = 0.0
        self.race_time = 0.0
        self.speed = BASE_SPEED  # current px/s, tracked for the speedometer
        self.state = "racing"  # "racing" | "result"

        self.obstacle_rng = random.Random(rng_seed)
        self.obstacles = spawn_obstacles(self.obstacle_rng, TRACK_DISTANCE, BASE_SPEED, RACER_SPEED_MULTIPLIER)
        self.flashing = False       # True while recovering from a crash
        self.penalty_timer = 0.0    # seconds into the current 0 -> BASE_SPEED ramp
        self.hit_obstacle = None    # the specific obstacle currently flashing alongside the player

        self._font = None
        self._small_font = None
        self._gear_font = None

    def _accel_time(self):
        return ACCEL_TIME + GEAR_ACCEL_STEP * (self.gear - 1)

    def _max_speed(self):
        return MAX_SPEED + GEAR_MAX_SPEED_STEP * (self.gear - 1)

    # -- input --------------------------------------------------------------

    def handle_event(self, event, manager):
        if event.type != pygame.KEYDOWN:
            return
        if self.state == "racing":
            if event.key == pygame.K_UP:
                self.gear = min(GEAR_COUNT, self.gear + 1)
            elif event.key == pygame.K_DOWN:
                self.gear = max(1, self.gear - 1)
        elif self.state == "result" and event.key == pygame.K_SPACE:
            if self.on_finish is not None:
                self.on_finish(manager, self)

    def update(self, dt, keys, manager):
        if self.state != "racing":
            return

        accel_time = self._accel_time()  # current gear's accel time — only the crash-recovery
                                          # ramp uses this; normal acceleration uses ACCEL_RATE
        if self.flashing:
            self.penalty_timer += dt
            progress = min(1.0, self.penalty_timer / accel_time)
            speed = BASE_SPEED * progress  # 0 -> BASE_SPEED over accel_time, Space is ignored
            if self.penalty_timer >= accel_time:
                self.flashing = False  # self.speed is already exactly BASE_SPEED here — seamless handoff
                if self.hit_obstacle is not None and self.hit_obstacle.kind == CACTUS:
                    self.hit_obstacle.destroyed = True  # disappears exactly as the flash ends
                self.hit_obstacle = None
        else:
            # speed is tracked directly (not as a 0..1 fraction of a range) so
            # shifting gears never causes a jump: the ceiling (_max_speed())
            # can move, but current speed only ever changes gradually toward
            # it — a shift up just means more room to keep climbing, a shift
            # down while already above the new cap just means holding Space
            # won't gain any more until you're back under it or shift up again
            space_held = keys[pygame.K_SPACE]
            target_max = self._max_speed()
            if space_held:
                if self.speed < target_max:
                    self.speed = min(target_max, self.speed + ACCEL_RATE * dt)
            else:
                decel_rate = (target_max - BASE_SPEED) / DECEL_TIME
                self.speed = max(BASE_SPEED, self.speed - decel_rate * dt)
            speed = self.speed

        self.speed = speed
        self.distance_traveled += speed * dt
        self.race_time += dt

        # only start a new lane step once we've settled on the current one
        # — this makes a quick tap move exactly one lane, while holding the
        # key keeps queuing the next step as soon as each glide finishes,
        # so a long hold can cross multiple lanes in one smooth motion
        if self.x == LANE_CENTERS[self.lane]:
            left_held = keys[pygame.K_LEFT] or keys[pygame.K_a]
            right_held = keys[pygame.K_RIGHT] or keys[pygame.K_d]
            if left_held and self.lane > 0:
                self.lane -= 1
            elif right_held and self.lane < LANE_COUNT - 1:
                self.lane += 1

        # glide toward the target lane's center — a short slide, not free
        # steering, so switching still reads as "picking a lane" not drifting
        target_x = LANE_CENTERS[self.lane]
        max_step = LANE_CHANGE_SPEED * dt
        if abs(target_x - self.x) <= max_step:
            self.x = target_x
        else:
            self.x += max_step if target_x > self.x else -max_step

        for obs in self.obstacles:
            if obs.kind != CACTUS:
                obs.update(dt)

        if not self.flashing:
            self._check_collision()

        if self.distance_traveled >= TRACK_DISTANCE:
            self.distance_traveled = TRACK_DISTANCE
            self.state = "result"

    def _check_collision(self):
        """Only called when not already flashing — a destroyed cactus can't
        re-hit (it's gone), and a racer can't immediately re-hit either since
        it keeps moving during the flash and will have pulled away by the
        time collision checks resume."""
        for obs in self.obstacles:
            if obs.kind == CACTUS and obs.destroyed:
                continue
            if obs.lane != self.lane:
                continue
            obs_y = PLAYER_Y - (obs.distance - self.distance_traveled)
            if abs(obs_y - PLAYER_Y) <= HIT_WINDOW:
                self.flashing = True
                self.penalty_timer = 0.0
                self.hit_obstacle = obs
                return

    def _flash_visible(self):
        return int(self.penalty_timer / FLASH_INTERVAL) % 2 == 0

    # -- drawing --------------------------------------------------------------

    def draw(self, surface):
        if self._font is None:
            self._font = pygame.font.SysFont(None, 30)
            self._small_font = pygame.font.SysFont(None, 22)
            self._gear_font = pygame.font.SysFont(None, 26, bold=True)

        surface.fill(BG_COLOR)

        track_rect = pygame.Rect(TRACK_LEFT, 0, TRACK_RIGHT - TRACK_LEFT, SCREEN_HEIGHT)
        pygame.draw.rect(surface, TRACK_COLOR, track_rect)
        self._draw_lane_dividers(surface)
        self._draw_finish_line(surface)
        self._draw_obstacles(surface)
        self._draw_player(surface)
        self._draw_hud(surface)
        self._draw_gear_indicator(surface)
        self._draw_speedometer(surface)

        if self.state == "result":
            self._draw_result(surface)

    def _draw_lane_dividers(self, surface):
        offset = self.distance_traveled % (DASH_LENGTH + DASH_GAP)
        for i in range(1, LANE_COUNT):
            div_x = TRACK_LEFT + LANE_WIDTH * i
            y = offset - (DASH_LENGTH + DASH_GAP)
            while y < SCREEN_HEIGHT:
                pygame.draw.line(surface, DASH_COLOR, (div_x, y), (div_x, y + DASH_LENGTH), 3)
                y += DASH_LENGTH + DASH_GAP

    def _draw_finish_line(self, surface):
        y_center = PLAYER_Y - (TRACK_DISTANCE - self.distance_traveled)
        if y_center < -100 or y_center > SCREEN_HEIGHT + 100:
            return  # well off screen, don't bother drawing

        col_w = (TRACK_RIGHT - TRACK_LEFT) / FINISH_CHECKER_COLS
        row_h = FINISH_LINE_HEIGHT / 2
        top = y_center - FINISH_LINE_HEIGHT / 2
        for row in range(2):
            for col in range(FINISH_CHECKER_COLS):
                color = FINISH_LIGHT_COLOR if (row + col) % 2 == 0 else FINISH_DARK_COLOR
                square = pygame.Rect(TRACK_LEFT + col * col_w, top + row * row_h, col_w, row_h)
                pygame.draw.rect(surface, color, square)

    def _draw_obstacles(self, surface):
        for obs in self.obstacles:
            if obs.kind == CACTUS and obs.destroyed:
                continue
            y = PLAYER_Y - (obs.distance - self.distance_traveled)
            if y < -100 or y > SCREEN_HEIGHT + 100:
                continue  # well off screen, don't bother drawing
            x = LANE_CENTERS[obs.lane]

            is_flashing_this = self.flashing and obs is self.hit_obstacle
            flash_on = is_flashing_this and self._flash_visible()

            if obs.kind == CACTUS:
                color = FLASH_COLOR if flash_on else CACTUS_COLOR
                draw_cactus(surface, x, y, CACTUS_HEIGHT, obs.arms, color=color)
            else:
                helmet_color = FLASH_COLOR if flash_on else obs.helmet_color
                rider_color = FLASH_COLOR if flash_on else PLAYER_COLOR
                draw_racer(surface, x, y, PLAYER_HEIGHT, rider_color, helmet_color=helmet_color)

    def _draw_player(self, surface):
        # top-down/rear view, facing up the screen — draw_racer bakes the
        # helmet into the rider's head already (reaching this scene means
        # it's equipped; the overworld gear gate checks that beforehand)
        if self.flashing and self._flash_visible():
            draw_racer(surface, self.x, PLAYER_Y, PLAYER_HEIGHT, FLASH_COLOR,
                       body_color=FLASH_COLOR, helmet_color=FLASH_COLOR)
        else:
            draw_racer(surface, self.x, PLAYER_Y, PLAYER_HEIGHT, PLAYER_COLOR)

    def _draw_hud(self, surface):
        hud_rect = pygame.Rect(0, 0, SCREEN_WIDTH, 30)
        pygame.draw.rect(surface, HUD_BG, hud_rect)

        remaining = max(0.0, TRACK_DISTANCE - self.distance_traveled)
        text = f"Distance Remaining: {remaining:.0f}m   |   Time: {self.race_time:.1f}s"
        label = self._small_font.render(text, True, TEXT_COLOR)
        surface.blit(label, (8, 6))

    def _draw_gear_indicator(self, surface):
        label = self._gear_font.render(f"GEAR {self.gear}", True, GEAR_TEXT_COLOR)
        box = label.get_rect().inflate(20, 14)
        box.bottomright = (SCREEN_WIDTH - 12, SCREEN_HEIGHT - 12)
        pygame.draw.rect(surface, GEAR_BOX_COLOR, box)
        pygame.draw.rect(surface, GEAR_TEXT_COLOR, box, 2)
        surface.blit(label, label.get_rect(center=box.center))

    def _draw_speedometer(self, surface):
        # a classic half-circle gauge: needle sweeps through the top half,
        # from pointing left (0 speed) to pointing right (ABSOLUTE_MAX_SPEED
        # — gear 5's top speed). A lower gear's needle simply can't swing as
        # far right, since its own max speed is a smaller fraction of the
        # full scale — that's the "stops moving up" cue you're after.
        cx, cy = SPEEDO_CENTER
        pygame.draw.circle(surface, HUD_BG, (cx, cy), SPEEDO_RADIUS + 10)

        dial_rect = pygame.Rect(cx - SPEEDO_RADIUS, cy - SPEEDO_RADIUS, SPEEDO_RADIUS * 2, SPEEDO_RADIUS * 2)
        pygame.draw.arc(surface, TEXT_COLOR, dial_rect, 0, math.pi, 3)

        fraction = max(0.0, min(1.0, self.speed / ABSOLUTE_MAX_SPEED))
        angle = math.radians(180 - 180 * fraction)
        needle_len = SPEEDO_RADIUS - 6
        needle_end = (cx + math.cos(angle) * needle_len, cy - math.sin(angle) * needle_len)
        pygame.draw.line(surface, PLAYER_COLOR, (cx, cy), needle_end, 3)
        pygame.draw.circle(surface, TEXT_COLOR, (cx, cy), 4)

    def _draw_result(self, surface):
        box = pygame.Rect(0, 0, 320, 140)
        box.center = (SCREEN_WIDTH // 2, 300)
        pygame.draw.rect(surface, (20, 20, 20), box)
        pygame.draw.rect(surface, TEXT_COLOR, box, 2)

        title = self._font.render("Race Complete", True, TEXT_COLOR)
        surface.blit(title, title.get_rect(midtop=(box.centerx, box.top + 10)))

        time_label = self._font.render(f"Time: {self.race_time:.1f}s", True, TEXT_COLOR)
        surface.blit(time_label, time_label.get_rect(center=(box.centerx, box.centery)))

        hint = self._small_font.render("SPACE to continue", True, TEXT_COLOR)
        surface.blit(hint, hint.get_rect(midbottom=(box.centerx, box.bottom - 8)))
