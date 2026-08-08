"""motorcycle_icon.py — a simple black 2-wheel motorcycle silhouette with a
small rider head, drawn at the same ground-point convention as
stick_figure.draw_stick_figure (feet/wheels touch down at (x, y)).
"""

import pygame

BODY_COLOR = (137, 141, 137)


def draw_motorcycle(surface, x, y, height, rider_color, body_color=BODY_COLOR):
    """Returns the rider's head center, so a helmet overlay can be
    positioned the same way whether the player is walking or riding."""
    wheel_r = height * 0.2
    wheel_y = y - wheel_r
    rear_x = x - height * 0.32
    front_x = x + height * 0.32
    line_w = max(2, int(height * 0.06))

    pygame.draw.circle(surface, body_color, (int(rear_x), int(wheel_y)), int(wheel_r), line_w)
    pygame.draw.circle(surface, body_color, (int(front_x), int(wheel_y)), int(wheel_r), line_w)

    seat = (x - height * 0.05, wheel_y - height * 0.35)
    handlebar = (front_x, wheel_y - height * 0.5)
    pygame.draw.line(surface, body_color, (rear_x, wheel_y), seat, line_w)
    pygame.draw.line(surface, body_color, seat, (front_x, wheel_y), line_w)
    pygame.draw.line(surface, body_color, seat, handlebar, line_w)

    head_r = height * 0.14
    head_center = (seat[0], seat[1] - head_r * 2)
    pygame.draw.circle(surface, rider_color, (int(head_center[0]), int(head_center[1])), int(head_r))
    return head_center
