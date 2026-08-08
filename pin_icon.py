"""pin_icon.py — the small white/red-trim bowling pin shape, shared by the
bowling shack's roof sign and the bowling lane's pin rack.
"""

import pygame

PIN_BODY_COLOR = (255, 255, 255)
PIN_TRIM_COLOR = (200, 30, 30)
PIN_OUTLINE_COLOR = (0, 0, 0)


def draw_pin_icon(surface, center, height):
    """Draw a simple bowling pin centered at `center`, `height` pixels tall."""
    cx, cy = center
    body_w = height * 0.5
    body_rect = pygame.Rect(0, 0, body_w, height)
    body_rect.center = (cx, cy)

    pygame.draw.ellipse(surface, PIN_BODY_COLOR, body_rect)
    pygame.draw.ellipse(surface, PIN_OUTLINE_COLOR, body_rect, 1)

    stripe_rect = pygame.Rect(body_rect.left, body_rect.top + height * 0.28, body_w, height * 0.14)
    pygame.draw.rect(surface, PIN_TRIM_COLOR, stripe_rect)
