"""explore_scene.py — the overworld: walking around a tile, picking up
items, opening the inventory, and interacting with buildings. This is what
used to be game.py's entire main loop, factored out into a Scene so
dialogue and mini-game scenes can be pushed on top of it and popped back to
cleanly.
"""

import pygame

from bowling.scene import BowlingScene
from constants import BLACK, SCREEN_HEIGHT, SCREEN_WIDTH
from dialogue import DialogueScene
from fishing.scene import FishingScene
from inventory import Inventory, Item
from item_db import get_item
from lake_shape import draw_lake
from map import World
from player import Player
from scene import Scene

BUMP_COOLDOWN = 2.0  # seconds; keeps a wedged player from spamming the sound
NOTICE_DURATION = 4.0  # seconds a post-minigame result banner stays up
BOWLING_WIN_SCORE = 185  # score needed to win Machine Part #25
MOTORCYCLE_WIN_KG = 50   # total catch weight needed to win the motorcycle
HELMET_WIN_KG = 100      # total catch weight needed to win the helmet

EQUIP_TOGGLE_MESSAGES = {
    "vehicle": ("You hop on the motorcycle. Vroom!", "You put the motorcycle away."),
    "head": ("You put on the helmet.", "You take off the helmet."),
}


def use_item(item):
    """Return the flavor text for using `item` right now, or None if the slot is empty."""
    if item is None:
        return None
    record = get_item(item.name)
    if record is None:
        return None
    # nothing in the world can satisfy a "use" yet (e.g. no PS1 to insert a
    # disc into), so this always resolves to the can't-use line for now
    return record.cant_use_description


class ExploreScene(Scene):
    def __init__(self, footstep_sound=None, bump_sound=None, engine_sound=None):
        self.world = World()
        self.player = Player(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
        self.inventory = Inventory()
        self.footstep_sound = footstep_sound
        self.bump_sound = bump_sound
        self.engine_sound = engine_sound
        self.bump_cooldown = 0.0
        self.use_message = ""
        self.notice_text = ""
        self.notice_timer = 0.0
        self.won_machine_part = False  # Machine Part #25 can only be won once
        self.bowling_high_score = None
        self.won_motorcycle = False  # 1957 Vincent Black Shadow, also one-time
        self.won_helmet = False      # Motorcycle Helmet, also one-time
        self.fishing_high_score = None  # best total kg across visits

        self.hint_font = pygame.font.SysFont(None, 22)
        self.message_font = pygame.font.SysFont(None, 24)
        self.debug_font = pygame.font.SysFont(None, 18)

    def show_notice(self, text, duration=NOTICE_DURATION):
        """Pop up a short banner — used for mini-game results."""
        self.notice_text = text
        self.notice_timer = duration

    # -- input --------------------------------------------------------------

    def handle_event(self, event, manager):
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_i:
            self.inventory.toggle()
            self.use_message = ""
        elif self.inventory.is_open:
            self._handle_inventory_key(event)
        elif event.key == pygame.K_SPACE:
            self._handle_interact(manager)

    def _handle_inventory_key(self, event):
        if event.key == pygame.K_LEFT:
            self.inventory.move_selector(-1, 0)
        elif event.key == pygame.K_RIGHT:
            self.inventory.move_selector(1, 0)
        elif event.key == pygame.K_UP:
            self.inventory.move_selector(0, -1)
        elif event.key == pygame.K_DOWN:
            self.inventory.move_selector(0, 1)
        elif event.key == pygame.K_SPACE:
            self._use_selected_item()

    def _use_selected_item(self):
        item = self.inventory.selected_item()
        if item is None:
            return
        record = get_item(item.name)
        if record is not None and record.equip_slot is not None:
            equip_on_message, equip_off_message = EQUIP_TOGGLE_MESSAGES[record.equip_slot]
            if record.equip_slot == "vehicle":
                self.player.toggle_riding()
                self.use_message = equip_on_message if self.player.riding else equip_off_message
            elif record.equip_slot == "head":
                self.player.toggle_helmet()
                self.use_message = equip_on_message if self.player.wearing_helmet else equip_off_message
            return

        message = use_item(item)
        if message is not None:
            self.use_message = message

    def _handle_interact(self, manager):
        for world_item in self.world.tile.items:
            if world_item.in_range(self.player.x, self.player.y):
                if self.inventory.add_item(world_item.item):
                    world_item.collected = True
                    self.world.collect(world_item.item.name)
                return

        for building in self.world.tile.buildings:
            if building.door_in_range(self.player.x, self.player.y):
                if building.kind == "bowling":
                    self._open_shack_dialogue(manager)
                elif building.kind == "fishing":
                    self._open_fishing_dialogue(manager)
                return

    # -- bowling shack flow ---------------------------------------------------

    def _open_shack_dialogue(self, manager):
        if self.won_machine_part:
            line = f"Come back to beat your high score of {self.bowling_high_score}?"
        else:
            line = f"Try some bowling? Score {BOWLING_WIN_SCORE}+ to win Machine Part #25"
        manager.push(DialogueScene(
            speaker="Shopkeep",
            line=line,
            choices=["Yes", "No"],
            on_choice=self._on_shack_choice,
            wearing_helmet=self.player.wearing_helmet,
        ))

    def _on_shack_choice(self, manager, choice):
        manager.pop()  # back to exploring either way
        if choice == "Yes":
            manager.push(BowlingScene(["Player 1"], bumpers=True, on_finish=self._on_bowling_finish))

    def _on_bowling_finish(self, manager, match):
        manager.pop()  # back to exploring
        score = match.players[0].score
        is_new_high_score = self.bowling_high_score is None or score > self.bowling_high_score
        if is_new_high_score:
            self.bowling_high_score = score

        if not self.won_machine_part and score >= BOWLING_WIN_SCORE:
            record = get_item("Machine Part #25")
            self.inventory.add_item(Item(record.name, record.color))
            self.won_machine_part = True
            self.show_notice(f"Score: {score} - you win! Got Machine Part #25.")
        elif self.won_machine_part and is_new_high_score:
            self.show_notice(f"Score: {score} - new high score!")
        elif self.won_machine_part:
            self.show_notice(f"Score: {score}. High score: {self.bowling_high_score}.")
        else:
            self.show_notice(f"Score: {score}. Try again sometime.")

    # -- fishing hut flow -------------------------------------------------------

    def _open_fishing_dialogue(self, manager):
        if self.won_motorcycle and self.won_helmet:
            line = f"Come back to beat your best haul of {self.fishing_high_score}kg?"
        elif self.won_motorcycle:
            line = f"Catch {HELMET_WIN_KG}kg total to win a Motorcycle Helmet! Best haul: {self.fishing_high_score}kg."
        else:
            line = "Try some fishing? Catch 50 kgs to win a 1957 Vincent Black Shadow"
        manager.push(DialogueScene(
            speaker="Fishing Guru",
            line=line,
            choices=["Yes", "No"],
            on_choice=self._on_fishing_choice,
            wearing_helmet=self.player.wearing_helmet,
        ))

    def _on_fishing_choice(self, manager, choice):
        manager.pop()  # back to exploring either way
        if choice == "Yes":
            manager.push(FishingScene(on_finish=self._on_fishing_finish))

    def _on_fishing_finish(self, manager, result):
        manager.pop()  # back to exploring
        total_kg = result.total_kg()
        is_new_high_score = self.fishing_high_score is None or total_kg > self.fishing_high_score
        if is_new_high_score:
            self.fishing_high_score = total_kg

        just_won_motorcycle = not self.won_motorcycle and total_kg >= MOTORCYCLE_WIN_KG
        if just_won_motorcycle:
            record = get_item("1957 Vincent Black Shadow")
            self.inventory.add_item(Item(record.name, record.color))
            self.won_motorcycle = True

        just_won_helmet = not self.won_helmet and total_kg >= HELMET_WIN_KG
        if just_won_helmet:
            record = get_item("Motorcycle Helmet")
            self.inventory.add_item(Item(record.name, record.color))
            self.won_helmet = True

        if just_won_motorcycle and just_won_helmet:
            self.show_notice(f"Caught {total_kg}kg - you win a 1957 Vincent Black Shadow AND a Motorcycle Helmet!")
        elif just_won_motorcycle:
            self.show_notice(f"Caught {total_kg}kg - you win a 1957 Vincent Black Shadow!")
        elif just_won_helmet:
            self.show_notice(f"Caught {total_kg}kg - you win a Motorcycle Helmet!")
        elif is_new_high_score:
            self.show_notice(f"Caught {total_kg}kg - new high score!")
        else:
            self.show_notice(f"Caught {total_kg}kg. High score: {self.fishing_high_score}kg.")

    # -- update/draw ----------------------------------------------------------

    def update(self, dt, keys, manager):
        self.bump_cooldown = max(0.0, self.bump_cooldown - dt)
        if self.notice_timer > 0:
            self.notice_timer -= dt
            if self.notice_timer <= 0:
                self.notice_text = ""

        if self.inventory.is_open:
            return

        obstacles = self.world.tile.trees + self.world.tile.buildings
        if self.world.tile.lake is not None:
            obstacles = obstacles + [self.world.tile.lake]
        self.player.update(dt, keys, obstacles)
        self.world.handle_transition(self.player)

        if self.player.stepped:
            step_sound = self.engine_sound if self.player.riding else self.footstep_sound
            if step_sound is not None:
                step_sound.play()
        if self.player.bumped and self.bump_cooldown <= 0.0 and self.bump_sound is not None:
            self.bump_sound.play()
            self.bump_cooldown = BUMP_COOLDOWN

    def draw(self, surface):
        surface.fill(BLACK)

        if self.world.tile.lake is not None:
            draw_lake(surface, self.world.tile.lake.rect)
        for tree in self.world.tile.trees:
            tree.draw(surface)
        for building in self.world.tile.buildings:
            building.draw(surface)
        for world_item in self.world.tile.items:
            world_item.draw(surface)
        self.player.draw(surface, self.world.tile.trees)

        self._draw_interact_hint(surface)
        self.inventory.draw(surface)
        self._draw_use_message(surface)
        self._draw_notice(surface)

        coord_label = self.debug_font.render(f"Tile ({self.world.tx}, {self.world.ty})", True, (200, 200, 200))
        surface.blit(coord_label, (8, 8))

    def _draw_interact_hint(self, surface):
        nearby_item = next((wi for wi in self.world.tile.items if wi.in_range(self.player.x, self.player.y)), None)
        if nearby_item is not None:
            hint = self.hint_font.render(f"SPACE to pick up {nearby_item.item.name}", True, (255, 255, 255))
            surface.blit(hint, hint.get_rect(midtop=(self.player.x, self.player.y + 12)))
            return

        for building in self.world.tile.buildings:
            if building.door_in_range(self.player.x, self.player.y):
                hint = self.hint_font.render("SPACE to enter", True, (255, 255, 255))
                surface.blit(hint, hint.get_rect(midtop=(self.player.x, self.player.y + 12)))
                return

    def _draw_use_message(self, surface):
        if self.inventory.is_open and self.use_message:
            text = self.message_font.render(self.use_message, True, (255, 255, 255))
            box_rect = text.get_rect(midbottom=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 20)).inflate(24, 16)
            pygame.draw.rect(surface, (20, 20, 20), box_rect)
            pygame.draw.rect(surface, (200, 200, 200), box_rect, 2)
            surface.blit(text, text.get_rect(center=box_rect.center))

    def _draw_notice(self, surface):
        if not self.notice_text:
            return
        text = self.message_font.render(self.notice_text, True, (255, 255, 255))
        box_rect = text.get_rect(midtop=(SCREEN_WIDTH // 2, 20)).inflate(24, 16)
        pygame.draw.rect(surface, (20, 20, 20), box_rect)
        pygame.draw.rect(surface, (200, 200, 200), box_rect, 2)
        surface.blit(text, text.get_rect(center=box_rect.center))
