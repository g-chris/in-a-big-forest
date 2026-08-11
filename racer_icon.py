"""racer_icon.py — the MotoCross racer as seen from above and slightly
behind, with forward (the direction of travel) pointing "up" the screen.
This is a different camera angle than motorcycle_icon.py's side-view bike
(used on the overworld and the hut's sign), so it gets its own module
rather than a variant of that one.
"""

import pygame

BODY_COLOR = (137, 141, 137)  # matches motorcycle_icon.BODY_COLOR
WHEEL_COLOR = (30, 30, 30)
HELMET_COLOR = (110, 110, 115)  # matches player.HELMET_COLOR


def draw_racer(surface, x, y, height, rider_color, body_color=BODY_COLOR, helmet_color=HELMET_COLOR):
    """x, y: the racer's center point. height: overall length from front
    wheel to rear wheel. Always drawn facing up the screen — MotoCross has
    no turning, only lane changes, so there's no rotation to handle.
    helmet_color defaults to the player's grey; opponent racers pass their
    own red/green so they're distinguishable at a glance."""
    body_w = height * 0.24
    body_h = height * 0.85

    # bike body: a long rounded rect pointing straight up the screen
    body_rect = pygame.Rect(0, 0, body_w, body_h)
    body_rect.center = (x, y)
    pygame.draw.rect(surface, body_color, body_rect, border_radius=int(body_w * 0.4))

    # wheels: small dark ovals at the front and rear
    wheel_w, wheel_h = body_w * 1.4, height * 0.14
    front_wheel = pygame.Rect(0, 0, wheel_w, wheel_h)
    front_wheel.center = (x, y - body_h * 0.45)
    rear_wheel = pygame.Rect(0, 0, wheel_w, wheel_h)
    rear_wheel.center = (x, y + body_h * 0.45)
    pygame.draw.ellipse(surface, WHEEL_COLOR, front_wheel)
    pygame.draw.ellipse(surface, WHEEL_COLOR, rear_wheel)

    # handlebar: a short bar near the front
    handlebar_y = y - body_h * 0.32
    handlebar_w = body_w * 2.4
    line_w = max(2, int(height * 0.05))
    pygame.draw.line(surface, body_color, (x - handlebar_w / 2, handlebar_y), (x + handlebar_w / 2, handlebar_y), line_w)

    # rider, seen from behind: shoulders sitting on the bike, helmet toward
    # the front where they lean over the handlebars
    shoulder_rect = pygame.Rect(0, 0, body_w * 1.7, height * 0.22)
    shoulder_rect.center = (x, y + body_h * 0.08)
    pygame.draw.ellipse(surface, rider_color, shoulder_rect)

    helmet_r = height * 0.13
    helmet_center = (x, y - body_h * 0.12)
    pygame.draw.circle(surface, helmet_color, helmet_center, int(helmet_r))

    return helmet_center
