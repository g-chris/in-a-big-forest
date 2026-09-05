"""art_tools.py — a tiny in-game pixel art editor for making static sprite
assets (starting with the Spaceport's spaceship). Like audio/sound_tools.py
and audio/midi_tools.py, this is custom tooling the project builds for
itself — but interactive, so it's a Scene rather than a one-shot generator.

Fully D-Pad + one action button, matching the rest of the game: arrows
navigate, Space confirms whatever is focused — no other key does anything,
including naming and saving the file (a true on-screen keyboard, no typing).
"""

import os

import pygame

from constants import SCREEN_HEIGHT, SCREEN_WIDTH
from scene import Scene

ASSET_DIR = os.path.join(os.path.dirname(__file__), "assets")

CANVAS_SIZE = 12
CELL_PX = 28
CANVAS_LEFT = (SCREEN_WIDTH - CANVAS_SIZE * CELL_PX) // 2
CANVAS_TOP = 96

TOOLS = ["Pencil", "Eraser"]
TOOLS_Y = 66

PALETTE = [
    (0, 0, 0),        # black
    (255, 255, 255),  # white
    (140, 140, 140),  # grey
    (220, 40, 40),    # red
    (40, 180, 80),    # green
    (60, 120, 220),   # blue
    (255, 220, 0),    # yellow
    (120, 80, 40),    # brown
]
PALETTE_Y = CANVAS_TOP + CANVAS_SIZE * CELL_PX + 14
SWATCH_SIZE = 34
SWATCH_GAP = 8

ACTIONS = ["Save", "Exit"]
ACTIONS_Y = PALETTE_Y + SWATCH_SIZE + 24

BTN_W, BTN_H = 100, 34
BTN_GAP = 14

MAX_NAME_LEN = 12
KEYBOARD_ROWS = [
    "ABCDEFGHI",
    "JKLMNOPQR",
    "STUVWXYZ0",
    "123456789",
]
NAMING_ACTIONS = ["Del", "Save", "Cancel"]
KEY_PX = 40
KEYBOARD_LEFT = (SCREEN_WIDTH - len(KEYBOARD_ROWS[0]) * KEY_PX) // 2
KEYBOARD_TOP = 100
NAME_SLOT_W = 26
NAME_BUFFER_Y = 56
NAMING_ACTIONS_Y = KEYBOARD_TOP + len(KEYBOARD_ROWS) * KEY_PX + 24

TITLE_Y = 16
STATUS_Y = 40
STATUS_DURATION = 2.5

BG_COLOR = (10, 40, 15)
TEXT_COLOR = (255, 255, 255)
BUTTON_BG = (40, 40, 40)
FOCUS_COLOR = (255, 220, 0)
GRID_LINE_COLOR = (20, 20, 20)
CHECKER_LIGHT = (90, 90, 90)
CHECKER_DARK = (70, 70, 70)


class PixelArtScene(Scene):
    def __init__(self):
        self.mode = "editing"  # "editing" | "naming"

        self.grid = [[None] * CANVAS_SIZE for _ in range(CANVAS_SIZE)]
        self.cursor_x = 0
        self.cursor_y = 0

        self.focus = "canvas"  # "tools" | "canvas" | "palette" | "actions"
        self.tool_index = 0
        self.active_tool = TOOLS[0].lower()
        self.color_index = 0
        self.active_color = PALETTE[0]
        self.action_index = 0

        self.naming_focus = "keyboard"  # "keyboard" | "actions"
        self.key_x = 0
        self.key_y = 0
        self.naming_action_index = 0
        self.name_buffer = ""

        self.status_text = ""
        self.status_timer = 0.0

        self._font = None
        self._small_font = None

    # -- input --------------------------------------------------------------

    def handle_event(self, event, manager):
        if event.type != pygame.KEYDOWN:
            return
        if self.mode == "editing":
            self._handle_editing_key(event, manager)
        else:
            self._handle_naming_key(event, manager)

    def _handle_editing_key(self, event, manager):
        if event.key in (pygame.K_LEFT, pygame.K_a):
            self._move_editing(-1, 0)
        elif event.key in (pygame.K_RIGHT, pygame.K_d):
            self._move_editing(1, 0)
        elif event.key in (pygame.K_UP, pygame.K_w):
            self._move_editing(0, -1)
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self._move_editing(0, 1)
        elif event.key == pygame.K_SPACE:
            self._confirm_editing(manager)

    def _move_editing(self, dx, dy):
        if self.focus == "canvas":
            if dx != 0:
                self.cursor_x = max(0, min(CANVAS_SIZE - 1, self.cursor_x + dx))
            if dy != 0:
                new_y = self.cursor_y + dy
                if 0 <= new_y < CANVAS_SIZE:
                    self.cursor_y = new_y
                else:
                    self.focus = "tools" if dy < 0 else "palette"
            return

        if dx != 0:
            if self.focus == "tools":
                self.tool_index = (self.tool_index + dx) % len(TOOLS)
            elif self.focus == "palette":
                self.color_index = (self.color_index + dx) % len(PALETTE)
            elif self.focus == "actions":
                self.action_index = (self.action_index + dx) % len(ACTIONS)
        if dy != 0:
            order = ["tools", "canvas", "palette", "actions"]
            i = (order.index(self.focus) + (1 if dy > 0 else -1)) % len(order)
            self.focus = order[i]

    def _confirm_editing(self, manager):
        if self.focus == "tools":
            self.active_tool = TOOLS[self.tool_index].lower()
        elif self.focus == "palette":
            self.active_color = PALETTE[self.color_index]
        elif self.focus == "canvas":
            if self.active_tool == "pencil":
                self.grid[self.cursor_y][self.cursor_x] = self.active_color
            else:
                self.grid[self.cursor_y][self.cursor_x] = None
        elif self.focus == "actions":
            action = ACTIONS[self.action_index]
            if action == "Save":
                self.mode = "naming"
            elif action == "Exit":
                manager.pop()

    def _handle_naming_key(self, event, manager):
        if event.key in (pygame.K_LEFT, pygame.K_a):
            self._move_naming(-1, 0)
        elif event.key in (pygame.K_RIGHT, pygame.K_d):
            self._move_naming(1, 0)
        elif event.key in (pygame.K_UP, pygame.K_w):
            self._move_naming(0, -1)
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self._move_naming(0, 1)
        elif event.key == pygame.K_SPACE:
            self._confirm_naming(manager)

    def _move_naming(self, dx, dy):
        if self.naming_focus == "keyboard":
            if dx != 0:
                self.key_x = max(0, min(len(KEYBOARD_ROWS[0]) - 1, self.key_x + dx))
            if dy != 0:
                new_y = self.key_y + dy
                if 0 <= new_y < len(KEYBOARD_ROWS):
                    self.key_y = new_y
                else:
                    self.naming_focus = "actions"
            return

        # naming_focus == "actions" -- only one other region, so any
        # vertical move just returns focus to the keyboard's bottom row
        if dx != 0:
            self.naming_action_index = (self.naming_action_index + dx) % len(NAMING_ACTIONS)
        if dy != 0:
            self.naming_focus = "keyboard"

    def _confirm_naming(self, manager):
        if self.naming_focus == "keyboard":
            char = KEYBOARD_ROWS[self.key_y][self.key_x]
            if len(self.name_buffer) < MAX_NAME_LEN:
                self.name_buffer += char
            return

        action = NAMING_ACTIONS[self.naming_action_index]
        if action == "Del":
            self.name_buffer = self.name_buffer[:-1]
        elif action == "Save":
            if self.name_buffer:
                self._save_canvas(self.name_buffer)
                self.name_buffer = ""
                self.mode = "editing"
        elif action == "Cancel":
            self.name_buffer = ""
            self.mode = "editing"

    def _save_canvas(self, name):
        surf = pygame.Surface((CANVAS_SIZE, CANVAS_SIZE), pygame.SRCALPHA)
        for y in range(CANVAS_SIZE):
            for x in range(CANVAS_SIZE):
                color = self.grid[y][x]
                surf.set_at((x, y), (*color, 255) if color is not None else (0, 0, 0, 0))
        os.makedirs(ASSET_DIR, exist_ok=True)
        pygame.image.save(surf, os.path.join(ASSET_DIR, f"{name}.png"))
        self.status_text = f"Saved as {name}.png!"
        self.status_timer = STATUS_DURATION

    # -- update ---------------------------------------------------------------

    def update(self, dt, keys, manager):
        if self.status_timer > 0:
            self.status_timer = max(0.0, self.status_timer - dt)
            if self.status_timer == 0.0:
                self.status_text = ""

    # -- drawing ----------------------------------------------------------------

    def draw(self, surface):
        if self._font is None:
            self._font = pygame.font.SysFont(None, 30)
            self._small_font = pygame.font.SysFont(None, 20)

        if self.mode == "editing":
            self._draw_editing(surface)
        else:
            self._draw_naming(surface)

    def _draw_editing(self, surface):
        surface.fill(BG_COLOR)

        title = self._font.render("Pixel Art Editor", True, TEXT_COLOR)
        surface.blit(title, title.get_rect(midtop=(SCREEN_WIDTH // 2, TITLE_Y)))

        if self.status_text:
            label = self._small_font.render(self.status_text, True, FOCUS_COLOR)
            surface.blit(label, label.get_rect(midtop=(SCREEN_WIDTH // 2, STATUS_Y)))

        self._draw_button_row(surface, TOOLS, self.tool_index, self.focus == "tools",
                               TOOLS_Y, active_label=self.active_tool.capitalize())
        self._draw_canvas(surface)
        self._draw_palette_row(surface)
        self._draw_button_row(surface, ACTIONS, self.action_index, self.focus == "actions", ACTIONS_Y)

        hint = self._small_font.render("ARROWS: move   SPACE: select", True, TEXT_COLOR)
        surface.blit(hint, hint.get_rect(midbottom=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 12)))

    def _draw_canvas(self, surface):
        for y in range(CANVAS_SIZE):
            for x in range(CANVAS_SIZE):
                rect = pygame.Rect(CANVAS_LEFT + x * CELL_PX, CANVAS_TOP + y * CELL_PX, CELL_PX, CELL_PX)
                color = self.grid[y][x]
                if color is None:
                    checker = CHECKER_LIGHT if (x + y) % 2 == 0 else CHECKER_DARK
                    pygame.draw.rect(surface, checker, rect)
                else:
                    pygame.draw.rect(surface, color, rect)
                pygame.draw.rect(surface, GRID_LINE_COLOR, rect, 1)

        if self.focus == "canvas":
            cursor_rect = pygame.Rect(CANVAS_LEFT + self.cursor_x * CELL_PX,
                                       CANVAS_TOP + self.cursor_y * CELL_PX, CELL_PX, CELL_PX)
            pygame.draw.rect(surface, FOCUS_COLOR, cursor_rect, 3)

    def _draw_palette_row(self, surface):
        total_w = len(PALETTE) * SWATCH_SIZE + (len(PALETTE) - 1) * SWATCH_GAP
        left = (SCREEN_WIDTH - total_w) // 2
        for i, color in enumerate(PALETTE):
            rect = pygame.Rect(left + i * (SWATCH_SIZE + SWATCH_GAP), PALETTE_Y, SWATCH_SIZE, SWATCH_SIZE)
            pygame.draw.rect(surface, color, rect)
            focused = self.focus == "palette" and self.color_index == i
            border_color = FOCUS_COLOR if focused else TEXT_COLOR
            pygame.draw.rect(surface, border_color, rect, 3 if focused else 1)
            if color == self.active_color:
                pygame.draw.circle(surface, (255, 255, 255), rect.center, 5)
                pygame.draw.circle(surface, (0, 0, 0), rect.center, 5, 1)

    def _draw_button_row(self, surface, options, index, region_focused, y, active_label=None):
        total_w = len(options) * BTN_W + (len(options) - 1) * BTN_GAP
        left = (SCREEN_WIDTH - total_w) // 2
        for i, label in enumerate(options):
            rect = pygame.Rect(left + i * (BTN_W + BTN_GAP), y, BTN_W, BTN_H)
            focused = region_focused and index == i
            active = active_label is not None and label == active_label
            self._draw_button(surface, rect, label, focused, active)

    def _draw_button(self, surface, rect, label, focused, active=False):
        pygame.draw.rect(surface, BUTTON_BG, rect)
        border_color = FOCUS_COLOR if focused else TEXT_COLOR
        pygame.draw.rect(surface, border_color, rect, 3 if focused else 1)
        label_surf = self._small_font.render(label, True, TEXT_COLOR)
        surface.blit(label_surf, label_surf.get_rect(center=rect.center))
        if active:
            pygame.draw.circle(surface, (255, 255, 255), (rect.right - 8, rect.top + 8), 4)
            pygame.draw.circle(surface, (0, 0, 0), (rect.right - 8, rect.top + 8), 4, 1)

    def _draw_naming(self, surface):
        surface.fill(BG_COLOR)

        title = self._font.render("Save As", True, TEXT_COLOR)
        surface.blit(title, title.get_rect(midtop=(SCREEN_WIDTH // 2, TITLE_Y)))

        total_w = MAX_NAME_LEN * NAME_SLOT_W
        left = (SCREEN_WIDTH - total_w) // 2
        for i in range(MAX_NAME_LEN):
            rect = pygame.Rect(left + i * NAME_SLOT_W, NAME_BUFFER_Y, NAME_SLOT_W - 4, 30)
            pygame.draw.rect(surface, BUTTON_BG, rect)
            pygame.draw.rect(surface, TEXT_COLOR, rect, 1)
            if i < len(self.name_buffer):
                ch = self._small_font.render(self.name_buffer[i], True, TEXT_COLOR)
                surface.blit(ch, ch.get_rect(center=rect.center))

        self._draw_keyboard(surface)
        self._draw_button_row(surface, NAMING_ACTIONS, self.naming_action_index,
                               self.naming_focus == "actions", NAMING_ACTIONS_Y)

        hint = self._small_font.render("ARROWS: move   SPACE: select", True, TEXT_COLOR)
        surface.blit(hint, hint.get_rect(midbottom=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 12)))

    def _draw_keyboard(self, surface):
        for row_i, row in enumerate(KEYBOARD_ROWS):
            for col_i, ch in enumerate(row):
                rect = pygame.Rect(KEYBOARD_LEFT + col_i * KEY_PX, KEYBOARD_TOP + row_i * KEY_PX,
                                   KEY_PX - 4, KEY_PX - 4)
                pygame.draw.rect(surface, BUTTON_BG, rect)
                focused = self.naming_focus == "keyboard" and self.key_x == col_i and self.key_y == row_i
                border_color = FOCUS_COLOR if focused else TEXT_COLOR
                pygame.draw.rect(surface, border_color, rect, 3 if focused else 1)
                label = self._small_font.render(ch, True, TEXT_COLOR)
                surface.blit(label, label.get_rect(center=rect.center))
