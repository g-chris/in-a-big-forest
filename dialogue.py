"""dialogue.py — a simple black-background conversation scene: the player's
figure in the foreground, an NPC across from them, and a textbox (offset
toward the right side of the screen) with selectable options.

The game's whole art style is a stick figure with no face, so there's no
literal "back" sprite to draw — the player figure is just drawn larger, in
the foreground, standing in for "you, from behind."
"""

import pygame

from constants import SCREEN_WIDTH
from player import draw_helmet
from scene import Scene
from stick_figure import draw_stick_figure

BOX_BG_COLOR = (20, 20, 20)
BOX_BORDER_COLOR = (200, 200, 200)
TEXT_COLOR = (230, 230, 230)
SELECTED_COLOR = (255, 220, 0)

PLAYER_COLOR = (255, 220, 0)
NPC_COLOR = (220, 220, 220)


class DialogueScene(Scene):
    def __init__(self, speaker, line, choices, on_choice, wearing_helmet=False):
        """
        speaker: NPC label shown before the line, e.g. "Shopkeep"
        line: the dialogue text
        choices: list of option strings, e.g. ["Yes", "No"]
        on_choice: callable(manager, choice_text) — decides what happens next
        wearing_helmet: whether the player currently has the Motorcycle
            Helmet equipped, so this scene's separately-drawn player figure
            reflects it too
        """
        self.speaker = speaker
        self.line = line
        self.choices = choices
        self.on_choice = on_choice
        self.wearing_helmet = wearing_helmet
        self.selected = 0
        self._line_font = None
        self._choice_font = None

    def handle_event(self, event, manager):
        if event.type != pygame.KEYDOWN:
            return
        if event.key in (pygame.K_UP, pygame.K_LEFT):
            self.selected = (self.selected - 1) % len(self.choices)
        elif event.key in (pygame.K_DOWN, pygame.K_RIGHT):
            self.selected = (self.selected + 1) % len(self.choices)
        elif event.key == pygame.K_SPACE:
            self.on_choice(manager, self.choices[self.selected])

    def draw(self, surface):
        if self._line_font is None:
            self._line_font = pygame.font.SysFont(None, 26)
            self._choice_font = pygame.font.SysFont(None, 24)

        surface.fill((0, 0, 0))

        # player, large, foreground bottom-left — stands in for "your back"
        player_height = 160
        head_center = draw_stick_figure(surface, x=180, y=520, height=player_height, color=PLAYER_COLOR)
        if self.wearing_helmet:
            draw_helmet(surface, head_center, player_height)
        # NPC, right-of-center
        draw_stick_figure(surface, x=620, y=430, height=110, color=NPC_COLOR)

        # textbox offset toward the right side of the screen
        box_w, box_h = 380, 160
        box_rect = pygame.Rect(SCREEN_WIDTH - box_w - 40, 50, box_w, box_h)
        pygame.draw.rect(surface, BOX_BG_COLOR, box_rect)
        pygame.draw.rect(surface, BOX_BORDER_COLOR, box_rect, 2)

        text = f"{self.speaker}: {self.line}"
        y = box_rect.top + 14
        for wrapped_line in _wrap_text(text, self._line_font, box_w - 24):
            label = self._line_font.render(wrapped_line, True, TEXT_COLOR)
            surface.blit(label, (box_rect.left + 12, y))
            y += self._line_font.get_height() + 2

        y += 10
        for i, choice in enumerate(self.choices):
            color = SELECTED_COLOR if i == self.selected else TEXT_COLOR
            label = self._choice_font.render(choice, True, color)
            surface.blit(label, (box_rect.left + 28, y))
            y += self._choice_font.get_height() + 4


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
