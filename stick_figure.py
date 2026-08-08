"""stick_figure.py — the shared stick-figure rendering used by the player
and by any NPC, so the limb/walk-cycle math isn't duplicated between them.
"""

import math

import pygame


def draw_stick_figure(surface, x, y, height, color, swing=0.0):
    """Draw a stick figure standing with its feet at (x, y).

    `swing` is the walk-cycle phase in radians; 0 means standing still.
    Returns the head center, so a helmet overlay can be positioned
    consistently whether the player is walking or riding (see
    motorcycle_icon.draw_motorcycle, which returns the same thing).
    """
    h = height
    head_r = h * 0.14
    cx, cy = x, y

    # ground = cy, head top = cy - h
    neck_y = cy - h + head_r * 2
    hip_y = cy - h * 0.42
    foot_y = cy

    head_center = (cx, cy - h + head_r)

    # legs — opposite legs swing opposite ways
    leg_spread = h * 0.22
    left_leg_end = (cx + math.sin(swing) * leg_spread, foot_y)
    right_leg_end = (cx - math.sin(swing) * leg_spread, foot_y)

    # arms swing opposite to legs
    arm_spread = h * 0.22
    shoulder_y = neck_y + h * 0.06
    left_arm_end = (cx - math.sin(swing) * arm_spread, shoulder_y + h * 0.24)
    right_arm_end = (cx + math.sin(swing) * arm_spread, shoulder_y + h * 0.24)

    line_w = max(2, int(h * 0.06))

    # head
    pygame.draw.circle(surface, color, (int(head_center[0]), int(head_center[1])), int(head_r))
    # body
    pygame.draw.line(surface, color, (cx, neck_y), (cx, hip_y), line_w)
    # arms
    pygame.draw.line(surface, color, (cx, shoulder_y), left_arm_end, line_w)
    pygame.draw.line(surface, color, (cx, shoulder_y), right_arm_end, line_w)
    # legs
    pygame.draw.line(surface, color, (cx, hip_y), left_leg_end, line_w)
    pygame.draw.line(surface, color, (cx, hip_y), right_leg_end, line_w)

    return head_center
