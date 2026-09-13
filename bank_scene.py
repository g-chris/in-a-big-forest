"""bank_scene.py — the Bank's account screen once an account is open: the
player's inventory grid and a same-shaped bank storage grid, side by side.
A single moving selector square travels across both grids (crossing the
shared inner edge continues into the other one); selecting an occupied slot
moves that item to the first open slot on the opposite side — deposit and
withdraw are the same action, just read in whichever direction.
"""

import pygame

from constants import SCREEN_HEIGHT, SCREEN_WIDTH
from inventory import SLOT_PADDING, SLOT_SIZE, draw_grid
from scene import Scene

GRID_GAP = 140  # "a decent bit of space" between the two panels
HINT_COLOR = (200, 200, 200)


class BankScene(Scene):
    def __init__(self, player_inventory, bank_inventory):
        self.player_inventory = player_inventory
        self.bank_inventory = bank_inventory
        self.side = "player"  # which grid the moving selector is currently on
        self.hint_font = pygame.font.SysFont(None, 22)

    def _active(self):
        return self.player_inventory if self.side == "player" else self.bank_inventory

    def handle_event(self, event, manager):
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_LEFT:
            self._move(-1)
        elif event.key == pygame.K_RIGHT:
            self._move(1)
        elif event.key == pygame.K_UP:
            self._active().move_selector(0, -1)
        elif event.key == pygame.K_DOWN:
            self._active().move_selector(0, 1)
        elif event.key == pygame.K_SPACE:
            self._transfer_selected()
        elif event.key == pygame.K_i:
            manager.pop()

    def _move(self, dx):
        active = self._active()
        col = active.selected % active.cols
        row = active.selected // active.cols
        crossing_right = self.side == "player" and dx > 0 and col == active.cols - 1
        crossing_left = self.side == "bank" and dx < 0 and col == 0
        if not (crossing_right or crossing_left):
            active.move_selector(dx, 0)
            return
        self.side = "bank" if crossing_right else "player"
        other = self._active()
        other.selected = row * other.cols + (0 if crossing_right else other.cols - 1)

    def _transfer_selected(self):
        source = self._active()
        dest = self.bank_inventory if self.side == "player" else self.player_inventory
        item = source.slots[source.selected]
        if item is None:
            return
        for i, slot in enumerate(dest.slots):
            if slot is None:
                dest.slots[i] = item
                source.slots[source.selected] = None
                return

    def draw(self, surface):
        surface.fill((0, 0, 0))
        grid_w = self.player_inventory.cols * SLOT_SIZE + (self.player_inventory.cols + 1) * SLOT_PADDING
        left_center_x = SCREEN_WIDTH // 2 - GRID_GAP // 2 - grid_w // 2
        right_center_x = SCREEN_WIDTH // 2 + GRID_GAP // 2 + grid_w // 2
        center_y = SCREEN_HEIGHT // 2

        draw_grid(surface, self.player_inventory, left_center_x, center_y,
                  title="You", show_selector=self.side == "player")
        draw_grid(surface, self.bank_inventory, right_center_x, center_y,
                  title="Bank", show_selector=self.side == "bank")

        hint = self.hint_font.render("SPACE: move item     I: leave", True, HINT_COLOR)
        surface.blit(hint, hint.get_rect(midtop=(SCREEN_WIDTH // 2, 20)))
