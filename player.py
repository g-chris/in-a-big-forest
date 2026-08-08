"""player.py — the player character: movement, tree collision, footstep/bump
cues, and the walking/riding drawing.
"""

import math

import pygame

from constants import SCREEN_HEIGHT, SCREEN_WIDTH, SHADED_YELLOW, YELLOW
from motorcycle_icon import draw_motorcycle
from stick_figure import draw_stick_figure

WALK_SPEED = 225        # pixels per second, unchanged from before riding existed
RIDE_TOP_SPEED = 450    # double, once fully spun up
RIDE_ACCEL_TIME = 1.5   # seconds to reach top speed from a stop while riding
RIDE_STEP_INTERVAL = 0.09  # faster than walking's step_interval — reads as
                            # an engine rumble rather than discrete footsteps
HELMET_COLOR = (110, 110, 115)  # grey, to match the motorcycle's grey body


def draw_helmet(surface, head_center, height, color=HELMET_COLOR):
    """Draw the Motorcycle Helmet's black... er, grey half-dome on top of a
    head_center returned by draw_stick_figure/draw_motorcycle. Standalone
    (not a Player method) so dialogue.py's separately-drawn player figure
    can show it too.
    """
    head_r = height * 0.14
    radius = head_r * 1.25
    cx, cy = head_center[0], head_center[1] - head_r * 0.3
    samples = 12
    points = [
        (cx + radius * math.cos(math.pi + math.pi * i / samples),
         cy + radius * math.sin(math.pi + math.pi * i / samples))
        for i in range(samples + 1)
    ]
    pygame.draw.polygon(surface, color, points)


class Player:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.height = 50
        self.moving = False
        self.facing = 1  # 1 = right, -1 = left
        self.anim_timer = 0.0
        self.anim_speed = 8  # cycles per second while walking
        self.collision_radius = self.height * 0.16
        self.step_interval = 0.28  # seconds between footstep sounds while walking
        self.step_timer = 0.0
        self.stepped = False  # set for one frame each time a footstep lands
        self.bumped = False   # set for one frame each time movement is blocked
        self.exit_edge = None  # "left" | "right" | "top" | "bottom" | None this frame

        self.riding = False          # 1957 Vincent Black Shadow equipped
        self.ride_speed_scale = 0.0  # 0..1, ramps up/down while riding
        self.wearing_helmet = False  # Motorcycle Helmet equipped

    def toggle_riding(self):
        self.riding = not self.riding
        self.ride_speed_scale = 0.0  # always start a fresh ramp-up next time

    def toggle_helmet(self):
        self.wearing_helmet = not self.wearing_helmet

    def update(self, dt, keys, obstacles=()):
        dx = 0
        dy = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            dx -= 1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            dx += 1
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            dy -= 1
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            dy += 1

        self.moving = dx != 0 or dy != 0

        if dx != 0 and dy != 0:
            norm = math.sqrt(2) / 2
            dx *= norm
            dy *= norm

        if dx != 0:
            self.facing = 1 if dx > 0 else -1

        if self.riding:
            # the motorcycle takes a moment to get up to speed, and to spin
            # back down when you stop — walking is untouched, instant as ever
            target = 1.0 if self.moving else 0.0
            step = dt / RIDE_ACCEL_TIME
            self.ride_speed_scale += max(-step, min(step, target - self.ride_speed_scale))
            speed = RIDE_TOP_SPEED * self.ride_speed_scale
        else:
            speed = WALK_SPEED

        new_x = self.x + dx * speed * dt
        new_y = self.y + dy * speed * dt

        # resolve collisions per axis so the player slides along an
        # obstacle's edge instead of getting stuck when only one axis blocked
        blocked_x = dx != 0 and self._collides(new_x, self.y, obstacles)
        blocked_y = dy != 0 and self._collides(self.x, new_y, obstacles)
        if not blocked_x:
            self.x = new_x
        if not blocked_y:
            self.y = new_y
        self.bumped = blocked_x or blocked_y

        # note which edge (if any) we're pressing past — a screen transition
        # (handled by World.handle_transition) may override the clamp below
        self.exit_edge = None
        if self.x < self.height / 2:
            self.exit_edge = "left"
        elif self.x > SCREEN_WIDTH - self.height / 2:
            self.exit_edge = "right"
        if self.y < self.height:
            self.exit_edge = "top"
        elif self.y > SCREEN_HEIGHT - 10:
            self.exit_edge = "bottom"

        # always keep the player fully on-screen by default; this makes
        # Player safe to use/test on its own even without a World around it
        self.x = max(self.height / 2, min(SCREEN_WIDTH - self.height / 2, self.x))
        self.y = max(self.height, min(SCREEN_HEIGHT - 10, self.y))

        self.stepped = False
        if self.moving:
            self.anim_timer += dt * self.anim_speed
            self.step_timer += dt
            interval = RIDE_STEP_INTERVAL if self.riding else self.step_interval
            if self.step_timer >= interval:
                self.step_timer -= interval
                self.stepped = True
        else:
            self.anim_timer = 0.0
            self.step_timer = 0.0

    def _collides(self, x, y, obstacles):
        return any(o.blocks(x, y, self.collision_radius) for o in obstacles)

    def draw(self, surface, trees=()):
        # chest-height point used to test whether we're standing under a canopy
        under_canopy = any(tree.covers(self.x, self.y - self.height * 0.5) for tree in trees)
        color = SHADED_YELLOW if under_canopy else YELLOW

        if self.riding:
            head_center = draw_motorcycle(surface, self.x, self.y, self.height, color)
        else:
            swing = math.sin(self.anim_timer) * (0.6 if self.moving else 0.0)
            head_center = draw_stick_figure(surface, self.x, self.y, self.height, color, swing)

        if self.wearing_helmet:
            draw_helmet(surface, head_center, self.height)
