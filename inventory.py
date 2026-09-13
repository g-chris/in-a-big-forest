"""inventory.py — a dead-simple 4x4 grid inventory and world-item pickups."""

import pygame

GRID_COLS = 4
GRID_ROWS = 4
SLOT_SIZE = 56
SLOT_PADDING = 8

PANEL_BG = (20, 20, 20)
PANEL_BORDER = (200, 200, 200)
SLOT_BG = (50, 50, 50)
SLOT_BORDER = (90, 90, 90)
TEXT_COLOR = (230, 230, 230)
SELECTOR_COLOR = (255, 220, 0)


def _truncate(text, font, max_width):
    """Shorten `text` with an ellipsis so it renders within `max_width` pixels."""
    if font.size(text)[0] <= max_width:
        return text
    ellipsis = "…"
    while text and font.size(text + ellipsis)[0] > max_width:
        text = text[:-1]
    return (text + ellipsis) if text else ellipsis


class Item:
    def __init__(self, name, color):
        self.name = name
        self.color = color


class WorldItem:
    """An item sitting in the world that the player can walk up to and pick up."""

    def __init__(self, x, y, item, pickup_radius=30):
        self.x = x
        self.y = y
        self.item = item
        self.pickup_radius = pickup_radius
        self.collected = False

    def in_range(self, px, py):
        if self.collected:
            return False
        return (px - self.x) ** 2 + (py - self.y) ** 2 < self.pickup_radius ** 2

    def draw(self, surface):
        if self.collected:
            return
        pygame.draw.circle(surface, self.item.color, (int(self.x), int(self.y)), 8)
        pygame.draw.circle(surface, (0, 0, 0), (int(self.x), int(self.y)), 8, 1)


class Inventory:
    def __init__(self, cols=GRID_COLS, rows=GRID_ROWS):
        self.cols = cols
        self.rows = rows
        self.slots = [None] * (cols * rows)
        self.is_open = False
        self.selected = 0
        self._font = None
        self._title_font = None
        self._name_font = None

    def toggle(self):
        self.is_open = not self.is_open

    def add_item(self, item):
        """Place `item` in the first empty slot. Returns False if full."""
        for i, slot in enumerate(self.slots):
            if slot is None:
                self.slots[i] = item
                return True
        return False

    def move_selector(self, dx, dy):
        col = self.selected % self.cols
        row = self.selected // self.cols
        col = max(0, min(self.cols - 1, col + dx))
        row = max(0, min(self.rows - 1, row + dy))
        self.selected = row * self.cols + col

    def selected_item(self):
        return self.slots[self.selected]

    def draw(self, surface, title=None):
        if not self.is_open:
            return
        draw_grid(surface, self, surface.get_width() // 2, surface.get_height() // 2, title=title)


def draw_grid(surface, inv, center_x, center_y, title=None, show_selector=True):
    """The actual grid-drawing logic behind Inventory.draw(), factored out
    so bank_scene.py can render two of these side by side (each at its own
    center point, only one showing the moving selector) without going
    through Inventory's own is_open/single-centered assumptions."""
    if inv._font is None:
        inv._font = pygame.font.SysFont(None, 18)
    if inv._title_font is None:
        inv._title_font = pygame.font.SysFont(None, 32)
    if inv._name_font is None:
        inv._name_font = pygame.font.SysFont(None, 24)

    grid_w = inv.cols * SLOT_SIZE + (inv.cols + 1) * SLOT_PADDING
    grid_h = inv.rows * SLOT_SIZE + (inv.rows + 1) * SLOT_PADDING
    panel_x = center_x - grid_w // 2
    panel_y = center_y - grid_h // 2

    panel_rect = pygame.Rect(panel_x, panel_y, grid_w, grid_h)
    pygame.draw.rect(surface, PANEL_BG, panel_rect)
    pygame.draw.rect(surface, PANEL_BORDER, panel_rect, 2)

    if title:
        label = inv._title_font.render(title, True, TEXT_COLOR)
        surface.blit(label, label.get_rect(midbottom=(panel_rect.centerx, panel_rect.top - 12)))

    for index, item in enumerate(inv.slots):
        col = index % inv.cols
        row = index // inv.cols
        slot_x = panel_x + SLOT_PADDING + col * (SLOT_SIZE + SLOT_PADDING)
        slot_y = panel_y + SLOT_PADDING + row * (SLOT_SIZE + SLOT_PADDING)
        slot_rect = pygame.Rect(slot_x, slot_y, SLOT_SIZE, SLOT_SIZE)
        pygame.draw.rect(surface, SLOT_BG, slot_rect)
        pygame.draw.rect(surface, SLOT_BORDER, slot_rect, 1)

        if item is not None:
            center = slot_rect.center
            pygame.draw.circle(surface, item.color, center, SLOT_SIZE // 2 - 10)
            text = _truncate(item.name, inv._font, SLOT_SIZE - 4)
            label = inv._font.render(text, True, TEXT_COLOR)
            label_rect = label.get_rect(midtop=(center[0], slot_rect.bottom - 16))
            surface.blit(label, label_rect)

        if show_selector and index == inv.selected:
            pygame.draw.rect(surface, SELECTOR_COLOR, slot_rect, 3)

    if show_selector:
        selected_item = inv.slots[inv.selected]
        if selected_item is not None:
            name_label = inv._name_font.render(selected_item.name, True, (255, 255, 255))
            surface.blit(name_label, name_label.get_rect(midtop=(panel_rect.centerx, panel_rect.bottom + 10)))

    return panel_rect
