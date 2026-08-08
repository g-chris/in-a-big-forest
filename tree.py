"""tree.py — the Tree obstacle/scenery entity and its procedural placement."""

import random

import pygame

from constants import BROWN, GREEN, SCREEN_HEIGHT, SCREEN_WIDTH


class Tree:
    def __init__(self, x, y, scale=1.0):
        self.x = x
        self.y = y  # base of trunk (ground point)
        self.trunk_w = int(14 * scale)
        self.trunk_h = int(40 * scale)
        self.top_r = int(34 * scale)
        self.collision_radius = self.trunk_w / 2 + 4
        self.canopy_y = self.y - self.trunk_h - self.top_r * 0.6

    def covers(self, px, py):
        return (px - self.x) ** 2 + (py - self.canopy_y) ** 2 < self.top_r ** 2

    def blocks(self, px, py, radius):
        min_dist = radius + self.collision_radius
        return (px - self.x) ** 2 + (py - self.y) ** 2 < min_dist ** 2

    def draw(self, surface):
        trunk_rect = pygame.Rect(
            self.x - self.trunk_w // 2,
            self.y - self.trunk_h,
            self.trunk_w,
            self.trunk_h,
        )
        pygame.draw.rect(surface, BROWN, trunk_rect)

        pygame.draw.circle(surface, GREEN, (int(self.x), int(self.canopy_y)), self.top_r)


def generate_trees(seed, count):
    """Deterministically scatter `count` trees for a given seed, so the same
    seed always reproduces the same layout — tiles are regenerated on every
    visit rather than kept in memory, so this needs to be reproducible.
    """
    rng = random.Random(seed)
    trees = []
    for _ in range(count):
        x = rng.randint(30, SCREEN_WIDTH - 30)
        y = rng.randint(120, SCREEN_HEIGHT - 20)
        scale = rng.uniform(0.8, 1.4)
        trees.append(Tree(x, y, scale))
    trees.sort(key=lambda t: t.y)
    return trees
