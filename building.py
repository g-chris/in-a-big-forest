"""building.py — a static, solid structure the player can walk up to and
interact with via its door (e.g. the bowling shack). Buildings are collision
obstacles just like trees, but rectangular, and carry a `kind` tag so a
scene can decide what happens when the player interacts with their door.
"""

import pygame

from pin_icon import draw_pin_icon

DOOR_OUTLINE_COLOR = (0, 0, 0)
SIGN_BG_COLOR = (20, 20, 20)
SIGN_BORDER_COLOR = (200, 200, 200)
SIGN_TEXT_COLOR = (255, 255, 255)


class Building:
    def __init__(self, x, y, width, height, color, sign_text, kind, sign_icon=draw_pin_icon):
        self.x = x
        self.y = y  # ground/base y (bottom edge of the building)
        self.width = width
        self.height = height
        self.color = color
        self.sign_text = sign_text
        self.kind = kind  # e.g. "bowling" — what a scene does on interact
        self.sign_icon = sign_icon  # callable(surface, center, height)
        self.rect = pygame.Rect(x - width / 2, y - height, width, height)
        self._font = None

    def blocks(self, px, py, radius):
        """Rectangle collision, inflated by the tester's radius — same
        polymorphic interface as Tree.blocks() so Player can treat trees and
        buildings as interchangeable obstacles."""
        return self.rect.inflate(radius * 2, radius * 2).collidepoint(px, py)

    def door_in_range(self, px, py, radius=30):
        """The door sits at the building's base center — same interaction
        radius as a WorldItem pickup, for a consistent feel."""
        return (px - self.x) ** 2 + (py - self.y) ** 2 < radius ** 2

    def draw(self, surface):
        if self._font is None:
            self._font = pygame.font.SysFont(None, max(12, int(self.height * 0.4 * 0.5)))

        pygame.draw.rect(surface, self.color, self.rect)

        # door: same color as the building — the outline is what reads it as
        # a door despite matching the walls
        door_w, door_h = self.width * 0.16, self.height * 0.55
        door_rect = pygame.Rect(self.x - door_w / 2, self.y - door_h, door_w, door_h)
        pygame.draw.rect(surface, self.color, door_rect)
        pygame.draw.rect(surface, DOOR_OUTLINE_COLOR, door_rect, 2)

        # roof sign: a small board above the roofline with the sign text and
        # an icon (draw_pin_icon by default, or whatever `sign_icon` is)
        sign_w, sign_h = self.width * 0.6, self.height * 0.4
        sign_rect = pygame.Rect(self.x - sign_w / 2, self.rect.top - sign_h, sign_w, sign_h)
        pygame.draw.rect(surface, SIGN_BG_COLOR, sign_rect)
        pygame.draw.rect(surface, SIGN_BORDER_COLOR, sign_rect, 1)

        label = self._font.render(self.sign_text, True, SIGN_TEXT_COLOR)
        label_rect = label.get_rect(midleft=(sign_rect.left + 6, sign_rect.centery))
        surface.blit(label, label_rect)

        self.sign_icon(surface, (sign_rect.right - 12, sign_rect.centery), sign_h * 0.8)
