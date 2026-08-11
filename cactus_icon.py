"""cactus_icon.py — a simple green saguaro cactus. Arm count/placement is
randomized per-instance by motocross/obstacles.py's _random_arms() and
passed in as plain data, so the shape stays stable across frames — only
the color argument changes, for the hit-flash effect.
"""

import pygame

BODY_COLOR = (60, 140, 60)


def draw_cactus(surface, x, y, height, arms, color=BODY_COLOR):
    """x, y: the cactus's base (ground point). height: trunk height.
    arms: [(side, height_frac), ...] from obstacles._random_arms() — side
    is -1 (left) or 1 (right), height_frac is how far up the trunk it sits."""
    trunk_w = height * 0.22
    trunk_rect = pygame.Rect(0, 0, trunk_w, height)
    trunk_rect.midbottom = (x, y)
    pygame.draw.rect(surface, color, trunk_rect, border_radius=int(trunk_w * 0.5))

    arm_w = trunk_w * 0.8
    stub_len = trunk_w * 1.1
    arm_h = height * 0.3
    for side, height_frac in arms:
        elbow_y = y - height * height_frac

        stub_rect = pygame.Rect(0, 0, stub_len, arm_w)
        if side < 0:
            stub_rect.midright = (x - trunk_w / 2, elbow_y)
        else:
            stub_rect.midleft = (x + trunk_w / 2, elbow_y)
        pygame.draw.rect(surface, color, stub_rect, border_radius=int(arm_w * 0.4))

        outer_x = stub_rect.left if side < 0 else stub_rect.right
        arm_rect = pygame.Rect(0, 0, arm_w, arm_h)
        arm_rect.midbottom = (outer_x, elbow_y + arm_w / 2)
        pygame.draw.rect(surface, color, arm_rect, border_radius=int(arm_w * 0.4))
