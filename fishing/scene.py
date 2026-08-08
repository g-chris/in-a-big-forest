"""fishing/scene.py — the fishing mini-game screen. Boat + hook/line input,
lake rendering (via lake_shape.draw_lake), and wiring the fish pool
(fishing.fish) into a 3-slot catch UI, mirroring bowling/scene.py's shape.
"""

import math
import random

import pygame

from constants import SCREEN_WIDTH
from fish_icon import draw_fish
from lake_shape import draw_lake
from scene import Scene
from stick_figure import draw_stick_figure

from .fish import (CAUGHT, ESCAPING, GONE, HOOKED_STILL, HOOKED_WRIGGLE,
                    MAX_DEPTH, NIBBLING, SWIMMING, spawn_fish)

LAKE_RECT = pygame.Rect(150, 90, 600, 380)
BOAT_Y = LAKE_RECT.top
BOAT_MARGIN = 50
BOAT_MIN_X = LAKE_RECT.left + BOAT_MARGIN
BOAT_MAX_X = LAKE_RECT.right - BOAT_MARGIN
BOAT_SPEED = 200      # px/s
DROP_SPEED = 90        # px/s, hook sinking when not reeling (unhooked)
REEL_SPEED = 130       # px/s, hook rising when reeling (unhooked)
SLOT_COUNT = 3
POPUP_DURATION = 1.0  # seconds the "Fish On!" / "It Got Away!" text stays up

BG_COLOR = (10, 40, 15)
BOAT_COLOR = (110, 70, 35)
LINE_COLOR = (230, 230, 230)
HOOK_COLOR = (200, 200, 200)
FISH_COLOR = (215, 210, 225)
TEXT_COLOR = (255, 255, 255)
HUD_BG = (20, 20, 20)
FLASH_COLOR = (255, 255, 255)


class FishingScene(Scene):
    def __init__(self, on_finish=None, rng_seed=None):
        self.rng = random.Random(rng_seed)
        self.fish_list = spawn_fish(self.rng, BOAT_MIN_X, BOAT_MAX_X)
        self.on_finish = on_finish

        self.boat_x = (BOAT_MIN_X + BOAT_MAX_X) / 2
        self.hook_depth = 0.0
        self.slots = [None] * SLOT_COUNT
        self.game_over = False
        self._space_pressed_this_frame = False
        self._popup_text = ""
        self._popup_pos = (0, 0)
        self._popup_timer = 0.0

        self._font = None
        self._small_font = None

    # -- input --------------------------------------------------------------

    def handle_event(self, event, manager):
        if event.type != pygame.KEYDOWN or event.key != pygame.K_SPACE:
            return
        if self.game_over:
            if self.on_finish is not None:
                self.on_finish(manager, self)
        else:
            self._space_pressed_this_frame = True

    def update(self, dt, keys, manager):
        if self.game_over:
            return

        space_held = keys[pygame.K_SPACE]
        space_pressed = self._space_pressed_this_frame
        self._space_pressed_this_frame = False

        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.boat_x -= BOAT_SPEED * dt
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.boat_x += BOAT_SPEED * dt
        self.boat_x = max(BOAT_MIN_X, min(BOAT_MAX_X, self.boat_x))

        engaged = self._engaged_fish()
        if engaged is None:
            if space_held:
                self.hook_depth = max(0.0, self.hook_depth - REEL_SPEED * dt)
            else:
                self.hook_depth = min(MAX_DEPTH, self.hook_depth + DROP_SPEED * dt)

        for fish in self.fish_list:
            if fish.state in (GONE, CAUGHT):
                continue
            available = engaged is None or fish is engaged
            was_swimming = fish.state == SWIMMING
            fish.update(dt, self.boat_x, self.hook_depth, available, space_pressed, space_held)
            if engaged is None and was_swimming and fish.state != SWIMMING:
                engaged = fish  # claimed the hook's attention just now — lock out others this frame
            fish_y = BOAT_Y + fish.depth
            if fish.just_hooked:
                self._show_popup("Fish On!", fish.x, fish_y)
            if fish.just_lost:
                self._show_popup("It Got Away!", fish.x, fish_y)
            if fish.state == CAUGHT:
                self._catch(fish)

        if self._popup_timer > 0:
            self._popup_timer -= dt

        self._check_game_over()

    def _show_popup(self, text, x, y):
        self._popup_text = text
        self._popup_pos = (x, y)
        self._popup_timer = POPUP_DURATION

    def _engaged_fish(self):
        return next((f for f in self.fish_list if f.state in (NIBBLING, HOOKED_WRIGGLE, HOOKED_STILL, ESCAPING)), None)

    def _catch(self, fish):
        for i, slot in enumerate(self.slots):
            if slot is None:
                self.slots[i] = fish
                return

    def _check_game_over(self):
        if sum(1 for s in self.slots if s is not None) >= SLOT_COUNT:
            self.game_over = True
            return
        if not any(f.state not in (GONE, CAUGHT) for f in self.fish_list):
            self.game_over = True

    def total_kg(self):
        return sum(f.weight_kg for f in self.slots if f is not None)

    # -- drawing --------------------------------------------------------------

    def draw(self, surface):
        if self._font is None:
            self._font = pygame.font.SysFont(None, 26)
            self._small_font = pygame.font.SysFont(None, 20)

        surface.fill(BG_COLOR)
        draw_lake(surface, LAKE_RECT)
        self._draw_fish(surface)
        self._draw_boat_and_line(surface)
        self._draw_hud(surface)
        self._draw_popup(surface)

        if self.game_over:
            self._draw_result(surface)

    def _draw_fish(self, surface):
        for fish in self.fish_list:
            if fish.state in (GONE, CAUGHT):
                continue
            y = BOAT_Y + fish.depth
            length = 16 + fish.weight_kg * 0.5
            scale = 1.0
            if fish.state == ESCAPING:
                scale = max(0.0, 1.0 - fish.escape_timer / 0.8)
            if scale <= 0.05:
                continue
            draw_fish(surface, fish.x, y, length * scale, FISH_COLOR, wiggle=fish.wiggle_phase)

            # only the real bite gets a tell: the ring swells out and back
            # in over the hookset window, rather than flashing on every poke
            if fish.state == NIBBLING and fish.in_hang_window and fish.hang_time_total > 0:
                frac = 1.0 - fish.hang_timer / fish.hang_time_total
                frac = max(0.0, min(1.0, frac))
                pulse = math.sin(math.pi * frac)
                if pulse > 0.02:
                    radius = int(length * (0.4 + 0.5 * pulse))
                    pygame.draw.circle(surface, FLASH_COLOR, (int(fish.x), int(y)), radius, 1)

            # agitation marks only while actively fighting/wriggling — the
            # visual cue for "don't reel right now"
            if fish.state == HOOKED_WRIGGLE:
                self._draw_agitation_lines(surface, fish.x, y, length, fish.wiggle_phase)

    def _draw_agitation_lines(self, surface, x, y, radius, phase):
        count = 6
        for i in range(count):
            angle = (i / count) * 2 * math.pi + phase
            inner = radius * 0.9
            outer = radius * 1.25
            start = (x + math.cos(angle) * inner, y + math.sin(angle) * inner)
            end = (x + math.cos(angle) * outer, y + math.sin(angle) * outer)
            pygame.draw.line(surface, FLASH_COLOR, start, end, 1)

    def _draw_popup(self, surface):
        if not self._popup_text or self._popup_timer <= 0:
            return
        label = self._font.render(self._popup_text, True, TEXT_COLOR)
        x, y = self._popup_pos
        surface.blit(label, label.get_rect(center=(x, y - 24)))

    def _draw_boat_and_line(self, surface):
        engaged = self._engaged_fish()
        display_depth = engaged.depth if engaged else self.hook_depth
        line_bottom = BOAT_Y + display_depth

        pygame.draw.line(surface, LINE_COLOR, (self.boat_x, BOAT_Y), (self.boat_x, line_bottom), 1)
        pygame.draw.circle(surface, HOOK_COLOR, (int(self.boat_x), int(line_bottom)), 4)

        hull = [
            (self.boat_x - 30, BOAT_Y), (self.boat_x + 30, BOAT_Y),
            (self.boat_x + 22, BOAT_Y + 14), (self.boat_x - 22, BOAT_Y + 14),
        ]
        pygame.draw.polygon(surface, BOAT_COLOR, hull)
        draw_stick_figure(surface, self.boat_x, BOAT_Y - 4, 36, (255, 220, 0))

    def _draw_hud(self, surface):
        hud_rect = pygame.Rect(0, 0, SCREEN_WIDTH, 30)
        pygame.draw.rect(surface, HUD_BG, hud_rect)

        parts = []
        for i, slot in enumerate(self.slots):
            parts.append(f"Slot {i + 1}: {slot.name} {slot.weight_kg}kg" if slot else f"Slot {i + 1}: --")
        parts.append(f"Total: {self.total_kg()}kg")
        label = self._small_font.render("   |   ".join(parts), True, TEXT_COLOR)
        surface.blit(label, (8, 6))

    def _draw_result(self, surface):
        box = pygame.Rect(0, 0, 340, 40 + 24 * (SLOT_COUNT + 1))
        box.center = (SCREEN_WIDTH // 2, 300)
        pygame.draw.rect(surface, (20, 20, 20), box)
        pygame.draw.rect(surface, TEXT_COLOR, box, 2)

        title = self._font.render("Catch Report", True, TEXT_COLOR)
        surface.blit(title, title.get_rect(midtop=(box.centerx, box.top + 8)))

        y = box.top + 40
        for i, slot in enumerate(self.slots):
            text = f"{slot.name}: {slot.weight_kg}kg" if slot else "(empty)"
            label = self._small_font.render(text, True, TEXT_COLOR)
            surface.blit(label, label.get_rect(midtop=(box.centerx, y)))
            y += 22

        total = self._small_font.render(f"Total: {self.total_kg()}kg", True, TEXT_COLOR)
        surface.blit(total, total.get_rect(midtop=(box.centerx, y + 4)))

        hint = self._small_font.render("SPACE to continue", True, TEXT_COLOR)
        surface.blit(hint, hint.get_rect(midbottom=(box.centerx, box.bottom - 6)))
