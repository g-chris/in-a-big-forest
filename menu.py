"""menu.py — a small reusable full-screen list menu: a title, a list of
selectable option lines (Up/Down or W/S to move the selector, Space to
choose), and an optional transient notice banner. This is the same
interaction dialogue.py's choice list already uses, generalized to a full
screen and reused for the main menu, the minigames test menu, and small
in-menu sub-choices (like bowling's player count) so every menu screen in
the game looks and behaves the same way.
"""

import pygame

from constants import BLACK, SCREEN_HEIGHT, SCREEN_WIDTH
from scene import Scene

TEXT_COLOR = (230, 230, 230)
SELECTED_COLOR = (255, 220, 0)  # matches dialogue.py's SELECTED_COLOR / the player sprite
TITLE_COLOR = (255, 255, 255)
NOTICE_DURATION = 3.0

OPTION_SPACING = 44
OPTIONS_TOP = 260


class ListMenu(Scene):
    def __init__(self, title, options, on_select, subtitle=""):
        """
        title: heading shown at the top of the screen
        options: list[str] of selectable lines
        on_select: callable(manager, index, label) — called when Space
            confirms the current selection
        subtitle: optional smaller line shown under the title
        """
        self.title = title
        self.subtitle = subtitle
        self.options = options
        self.on_select = on_select
        self.selected = 0

        self.notice_text = ""
        self.notice_timer = 0.0

        self._title_font = None
        self._subtitle_font = None
        self._option_font = None

    def show_notice(self, text, duration=NOTICE_DURATION):
        """Pop up a short banner — used for "Coming soon!" and minigame
        result summaries when launched from the test menu."""
        self.notice_text = text
        self.notice_timer = duration

    # -- input --------------------------------------------------------------

    def handle_event(self, event, manager):
        if event.type != pygame.KEYDOWN:
            return
        if event.key in (pygame.K_UP, pygame.K_w):
            self.selected = (self.selected - 1) % len(self.options)
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self.selected = (self.selected + 1) % len(self.options)
        elif event.key == pygame.K_SPACE:
            self.on_select(manager, self.selected, self.options[self.selected])

    def update(self, dt, keys, manager):
        if self.notice_timer > 0:
            self.notice_timer -= dt
            if self.notice_timer <= 0:
                self.notice_text = ""

    # -- drawing --------------------------------------------------------------

    def draw(self, surface):
        if self._title_font is None:
            self._title_font = pygame.font.SysFont(None, 48)
            self._subtitle_font = pygame.font.SysFont(None, 22)
            self._option_font = pygame.font.SysFont(None, 32)

        surface.fill(BLACK)

        title_label = self._title_font.render(self.title, True, TITLE_COLOR)
        surface.blit(title_label, title_label.get_rect(center=(SCREEN_WIDTH // 2, 120)))

        if self.subtitle:
            subtitle_label = self._subtitle_font.render(self.subtitle, True, TEXT_COLOR)
            surface.blit(subtitle_label, subtitle_label.get_rect(center=(SCREEN_WIDTH // 2, 160)))

        for i, option in enumerate(self.options):
            color = SELECTED_COLOR if i == self.selected else TEXT_COLOR
            label = self._option_font.render(option, True, color)
            y = OPTIONS_TOP + i * OPTION_SPACING
            surface.blit(label, label.get_rect(center=(SCREEN_WIDTH // 2, y)))

        self._draw_notice(surface)

    def _draw_notice(self, surface):
        if not self.notice_text:
            return
        label = self._option_font.render(self.notice_text, True, TEXT_COLOR)
        box_rect = label.get_rect(midbottom=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 30)).inflate(24, 16)
        pygame.draw.rect(surface, (20, 20, 20), box_rect)
        pygame.draw.rect(surface, (200, 200, 200), box_rect, 2)
        surface.blit(label, label.get_rect(center=box_rect.center))
