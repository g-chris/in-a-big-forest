"""bowling/scene.py — the bowling mini-game screen. Wires bowling.match
(turn/frame state) and bowling.lane (roll physics) into a small pygame
Scene: aim, a timed power gauge, ball/pin rendering, and a live scoreboard.
"""

import pygame

from constants import SCREEN_WIDTH
from pin_icon import draw_pin_icon
from scene import Scene
from stick_figure import draw_stick_figure

from .lane import STRIKE_WINDOW, power_meter_value, resolve_roll
from .match import BowlingMatch
from .pins import PIN_HEIGHT, apply_hit, build_rack
from .scoring import frame_breakdown

LANE_LEFT = 300
LANE_RIGHT = 600
LANE_TOP = 120      # pins rack near here
LANE_BOTTOM = 520   # player stands near here
RACK_Y = LANE_TOP + 80  # gives the larger, wider-spaced pins headroom below LANE_TOP

AIM_SPEED = 1.2       # aim units (-1..1) per second while adjusting
ROLL_DURATION = 0.75  # seconds for the ball's travel animation
BALL_EASE_POWER = 1.6  # >1 = slow launch, gathering speed toward the pins —
                        # a cheap stand-in for a heavy ball's momentum
BALL_RADIUS_NEAR = 10  # near the player (foreground)
BALL_RADIUS_FAR = 5    # near the pins (perspective shrink as it recedes)

BAR_X, BAR_Y, BAR_W, BAR_H = 250, 550, 400, 22
BAR_FLASH_DURATION = 0.35  # seconds the bar flashes after a release

BG_COLOR = (10, 40, 15)
LANE_COLOR = (180, 140, 90)
GUTTER_COLOR = (40, 40, 40)
BALL_COLOR = (40, 40, 200)
BALL_SHADOW_COLOR = (140, 108, 66)
PLAYER_COLOR = (255, 220, 0)
TEXT_COLOR = (255, 255, 255)
CURRENT_TURN_COLOR = (255, 220, 0)
BAR_BG_COLOR = (60, 60, 60)
BAR_WINDOW_COLOR = (0, 190, 90)
BAR_MARKER_COLOR = (255, 255, 255)
BAR_FLASH_HIT_COLOR = (30, 255, 100)
BAR_FLASH_MISS_COLOR = (230, 40, 40)


class BowlingScene(Scene):
    def __init__(self, player_names, bumpers=True, on_finish=None):
        self.match = BowlingMatch(player_names, bumpers=bumpers)
        self.on_finish = on_finish

        self.state = "aiming"  # "aiming" | "charging" | "rolling" | "result"
        self.aim_offset = 0.0
        self.charge_elapsed = 0.0
        self.pending_pins = 0
        self.roll_progress = 0.0
        self.last_message = ""
        self.rack = build_rack((LANE_LEFT + LANE_RIGHT) / 2, RACK_Y)
        self._rack_pending_reset = False  # set once a frame ends; a fresh
        # rack is swapped in only after the fall animation finishes, so a
        # strike still gets to visibly topple instead of vanishing instantly

        self.bar_flash_color = None
        self.bar_flash_timer = 0.0

        self._font = None
        self._small_font = None

    # -- input ------------------------------------------------------------

    def handle_event(self, event, manager):
        if event.type != pygame.KEYDOWN or event.key != pygame.K_SPACE:
            return

        if self.state == "aiming":
            self.state = "charging"
            self.charge_elapsed = 0.0
        elif self.state == "charging":
            power = power_meter_value(self.charge_elapsed)
            self.pending_pins = resolve_roll(self.aim_offset, power, self.match.bumpers)
            self.state = "rolling"
            self.roll_progress = 0.0

            hit_window = STRIKE_WINDOW[0] <= power <= STRIKE_WINDOW[1]
            self.bar_flash_color = BAR_FLASH_HIT_COLOR if hit_window else BAR_FLASH_MISS_COLOR
            self.bar_flash_timer = BAR_FLASH_DURATION
        elif self.state == "result" and self.on_finish is not None:
            self.on_finish(manager, self.match)

    def update(self, dt, keys, manager):
        for pin in self.rack:
            pin.update(dt)

        if self.bar_flash_timer > 0.0:
            self.bar_flash_timer = max(0.0, self.bar_flash_timer - dt)
            if self.bar_flash_timer == 0.0:
                self.bar_flash_color = None

        if self._rack_pending_reset and all(p.standing or p.fall_t >= 1.0 for p in self.rack):
            self.rack = build_rack((LANE_LEFT + LANE_RIGHT) / 2, RACK_Y)
            self._rack_pending_reset = False

        if self.state == "aiming":
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                self.aim_offset -= AIM_SPEED * dt
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                self.aim_offset += AIM_SPEED * dt
            self.aim_offset = max(-1.0, min(1.0, self.aim_offset))
        elif self.state == "charging":
            self.charge_elapsed += dt
        elif self.state == "rolling":
            self.roll_progress += dt / ROLL_DURATION
            if self.roll_progress >= 1.0:
                player = self.match.current_player
                frame_rolls_before = list(player.frames[player.current_frame])
                standing_before = sum(1 for p in self.rack if p.standing)
                knocked_this_roll = min(self.pending_pins, standing_before)

                impact_x = self._lane_x(self.aim_offset)
                apply_hit(self.rack, impact_x, self.pending_pins)
                self.match.record_roll(self.pending_pins)
                self.last_message = _describe_roll(frame_rolls_before, knocked_this_roll)
                self.aim_offset = 0.0

                if self.match.is_game_over:
                    self.state = "result"
                else:
                    self.state = "aiming"
                    if self.match.pins_standing() == 10:
                        self._rack_pending_reset = True

    # -- drawing ------------------------------------------------------------

    def draw(self, surface):
        if self._font is None:
            self._font = pygame.font.SysFont(None, 26)
            self._small_font = pygame.font.SysFont(None, 18)

        surface.fill(BG_COLOR)
        self._draw_lane(surface)
        self._draw_pins(surface)
        self._draw_player_and_ball(surface)
        self._draw_power_bar(surface)
        self._draw_scoreboard(surface)
        self._draw_message(surface)

        if self.state == "result":
            self._draw_result(surface)

    def _lane_x(self, offset):
        center = (LANE_LEFT + LANE_RIGHT) / 2
        half_width = (LANE_RIGHT - LANE_LEFT) / 2
        return center + offset * half_width

    def _draw_lane(self, surface):
        pygame.draw.rect(surface, GUTTER_COLOR, (0, LANE_TOP, SCREEN_WIDTH, LANE_BOTTOM - LANE_TOP))
        pygame.draw.rect(surface, LANE_COLOR, (LANE_LEFT, LANE_TOP, LANE_RIGHT - LANE_LEFT, LANE_BOTTOM - LANE_TOP))

    def _draw_pins(self, surface):
        if self.state == "result":
            return
        for pin in self.rack:
            pos, scale = pin.draw_pos_and_scale()
            if scale <= 0.05:
                continue
            draw_pin_icon(surface, pos, PIN_HEIGHT * scale)

    def _draw_player_and_ball(self, surface):
        px = self._lane_x(self.aim_offset)
        draw_stick_figure(surface, px, LANE_BOTTOM, 70, PLAYER_COLOR)

        if self.state == "rolling":
            # ease-in: slow to start, gathering speed toward the pins, plus a
            # perspective shrink as it recedes — a cheap sense of the ball's
            # weight and momentum without any real physics simulation
            eased = self.roll_progress ** BALL_EASE_POWER
            bx = self._lane_x(self.aim_offset)
            by = LANE_BOTTOM + (LANE_TOP - LANE_BOTTOM) * eased
            radius = BALL_RADIUS_NEAR + (BALL_RADIUS_FAR - BALL_RADIUS_NEAR) * eased

            shadow_rect = pygame.Rect(0, 0, radius * 2.2, radius * 1.1)
            shadow_rect.center = (bx, by + radius * 0.7)
            pygame.draw.ellipse(surface, BALL_SHADOW_COLOR, shadow_rect)
            pygame.draw.circle(surface, BALL_COLOR, (int(bx), int(by)), int(radius))

    def _draw_power_bar(self, surface):
        bar_rect = pygame.Rect(BAR_X, BAR_Y, BAR_W, BAR_H)
        bar_fill = self.bar_flash_color if self.bar_flash_timer > 0.0 else BAR_BG_COLOR
        pygame.draw.rect(surface, bar_fill, bar_rect)

        window_x = BAR_X + STRIKE_WINDOW[0] * BAR_W
        window_w = (STRIKE_WINDOW[1] - STRIKE_WINDOW[0]) * BAR_W
        pygame.draw.rect(surface, BAR_WINDOW_COLOR, (window_x, BAR_Y, window_w, BAR_H))
        pygame.draw.rect(surface, TEXT_COLOR, bar_rect, 2)

        if self.state == "charging":
            power = power_meter_value(self.charge_elapsed)
            marker_x = BAR_X + power * BAR_W
            pygame.draw.line(surface, BAR_MARKER_COLOR, (marker_x, BAR_Y - 4), (marker_x, BAR_Y + BAR_H + 4), 3)

        hint = "SPACE: aim -> throw" if self.state == "aiming" else "SPACE: release!"
        if self.state in ("aiming", "charging"):
            label = self._small_font.render(hint, True, TEXT_COLOR)
            surface.blit(label, label.get_rect(midtop=(SCREEN_WIDTH // 2, BAR_Y + BAR_H + 6)))

    def _draw_scoreboard(self, surface):
        y = 8
        for i, player in enumerate(self.match.players):
            color = CURRENT_TURN_COLOR if i == self.match.current_index and not self.match.is_game_over else TEXT_COLOR
            rolls = [pins for frame in player.frames for pins in frame]
            frames = frame_breakdown(rolls)
            frame_text = " ".join(f"F{j + 1}:{_format_frame(f['rolls'])}" for j, f in enumerate(frames))
            line = f"{player.name}  {frame_text}   Total: {player.score}"
            label = self._small_font.render(line, True, color)
            surface.blit(label, (8, y))
            y += self._small_font.get_height() + 4

    def _draw_message(self, surface):
        if self.last_message and self.state != "result":
            label = self._font.render(self.last_message, True, TEXT_COLOR)
            surface.blit(label, label.get_rect(midtop=(SCREEN_WIDTH // 2, LANE_TOP - 30)))

    def _draw_result(self, surface):
        box = pygame.Rect(0, 0, 360, 40 + 26 * len(self.match.players))
        box.center = (SCREEN_WIDTH // 2, 300)
        pygame.draw.rect(surface, (20, 20, 20), box)
        pygame.draw.rect(surface, TEXT_COLOR, box, 2)

        title = self._font.render("Final Score", True, TEXT_COLOR)
        surface.blit(title, title.get_rect(midtop=(box.centerx, box.top + 8)))

        y = box.top + 40
        for player in self.match.players:
            label = self._small_font.render(f"{player.name}: {player.score}", True, TEXT_COLOR)
            surface.blit(label, label.get_rect(midtop=(box.centerx, y)))
            y += 22

        hint = self._small_font.render("SPACE to continue", True, TEXT_COLOR)
        surface.blit(hint, hint.get_rect(midbottom=(box.centerx, box.bottom - 6)))


def _format_frame(rolls):
    return "-".join("X" if r == 10 else str(r) for r in rolls)


def _describe_roll(frame_rolls_before, knocked_this_roll):
    """The on-screen message for a just-finished roll: "Strike!"/"Spare!"
    when earned, otherwise how many pins *this* throw knocked down (not the
    frame's running total)."""
    if knocked_this_roll == 10:
        return "Strike!"
    previous_roll = frame_rolls_before[-1] if frame_rolls_before else None
    if previous_roll is not None and previous_roll != 10 and previous_roll + knocked_this_roll == 10:
        return "Spare!"
    return f"{knocked_this_roll} pin(s)!" if knocked_this_roll else "Gutter!"
