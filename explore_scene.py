"""explore_scene.py — the overworld: walking around a tile, picking up
items, opening the inventory, and interacting with buildings. This is what
used to be game.py's entire main loop, factored out into a Scene so
dialogue and mini-game scenes can be pushed on top of it and popped back to
cleanly.
"""

import pygame

from bank_scene import BankScene
from bowling.scene import BowlingScene
from constants import BLACK, SCREEN_HEIGHT, SCREEN_WIDTH
from dialogue import DialogueScene
from fishing.scene import FishingScene
from inventory import Inventory, Item
from item_db import get_item
from lake_shape import draw_lake
from map import World
from motocross.scene import MotocrossScene
from player import Player
import save_system
from scene import Scene
from space_wars.scene import SpaceWarsScene
from spaceport_icon import draw_launchpad
from track_icon import draw_track_decoration

BUMP_COOLDOWN = 2.0  # seconds; keeps a wedged player from spamming the sound
NOTICE_DURATION = 4.0  # seconds a post-minigame result banner stays up
BOWLING_WIN_SCORE = 155  # score needed to win Machine Part #25
MOTORCYCLE_WIN_KG = 50   # total catch weight needed to win the motorcycle
HELMET_WIN_KG = 100      # total catch weight needed to win the helmet
MOTOCROSS_WIN_TIME = 35.5  # seconds; beat this to win the Hammer

EQUIP_TOGGLE_MESSAGES = {
    "vehicle": ("You hop on the motorcycle. Vroom!", "You put the motorcycle away."),
    "head": ("You put on the helmet.", "You take off the helmet."),
}

# nothing in the world can satisfy a "use" yet (e.g. no PS1 to insert a
# disc into), so trying to use any non-equip item always gets this line
FOREST_RANGER_CANT_USE_LINE = "Not here, not now. Thank you for not littering."

BANK_CASH_ITEM_NAME = "$10,000 US Cash"


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
        self.won_hammer = False      # Hammer, also one-time
        self.motocross_best_time = None  # best race time across visits (lower is better)
        self.player_name = None      # earned by winning Space Wars — never cleared once set
        self.bowling_alley_closed = False  # the Bowling Alley Guy gave everything away and left for good
        self.won_bank_account = False  # the promo account has been opened, also one-time
        self.bank_storage = Inventory()  # same shape as self.inventory — items parked at the Bank

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
            self._handle_inventory_key(event, manager)
        elif event.key == pygame.K_SPACE:
            self._handle_interact(manager)

    def _handle_inventory_key(self, event, manager):
        if event.key == pygame.K_LEFT:
            self.inventory.move_selector(-1, 0)
        elif event.key == pygame.K_RIGHT:
            self.inventory.move_selector(1, 0)
        elif event.key == pygame.K_UP:
            self.inventory.move_selector(0, -1)
        elif event.key == pygame.K_DOWN:
            self.inventory.move_selector(0, 1)
        elif event.key == pygame.K_SPACE:
            self._use_selected_item(manager)
        elif event.key == pygame.K_s:
            self._open_save_menu(manager)

    def _use_selected_item(self, manager):
        item = self.inventory.selected_item()
        if item is None:
            return
        record = get_item(item.name)
        if record is None:
            return
        if record.equip_slot is not None:
            equip_on_message, equip_off_message = EQUIP_TOGGLE_MESSAGES[record.equip_slot]
            if record.equip_slot == "vehicle":
                self.player.toggle_riding()
                self.use_message = equip_on_message if self.player.riding else equip_off_message
            elif record.equip_slot == "head":
                self.player.toggle_helmet()
                self.use_message = equip_on_message if self.player.wearing_helmet else equip_off_message
            return

        manager.push(DialogueScene(
            speaker="Forest Ranger",
            line=FOREST_RANGER_CANT_USE_LINE,
            choices=["OK"],
            on_choice=lambda m, choice: m.pop(),
            wearing_helmet=self.player.wearing_helmet,
        ))

    def _open_save_menu(self, manager):
        manager.push(DialogueScene(
            speaker="Save Master",
            line="Choose a slot to save to.",
            choices=[save_system.SLOT_LABELS[slot_id] for slot_id in save_system.SLOT_IDS] + ["Cancel"],
            on_choice=self._on_save_slot_choice,
            wearing_helmet=self.player.wearing_helmet,
        ))

    def _on_save_slot_choice(self, manager, choice):
        manager.pop()  # back to the still-open inventory
        if choice == "Cancel":
            return
        slot_id = save_system.LABEL_TO_SLOT_ID[choice]
        save_system.write_slot(slot_id, self.to_save_data())
        self.use_message = f"Saved to {choice}."

    def to_save_data(self):
        return {
            "tx": self.world.tx, "ty": self.world.ty,
            "player_x": self.player.x, "player_y": self.player.y,
            "riding": self.player.riding, "wearing_helmet": self.player.wearing_helmet,
            "collected_items": [list(t) for t in sorted(self.world.collected_items)],
            "inventory": [item.name if item else None for item in self.inventory.slots],
            "won_machine_part": self.won_machine_part,
            "bowling_high_score": self.bowling_high_score,
            "won_motorcycle": self.won_motorcycle,
            "won_helmet": self.won_helmet,
            "fishing_high_score": self.fishing_high_score,
            "won_hammer": self.won_hammer,
            "motocross_best_time": self.motocross_best_time,
            "player_name": self.player_name,
            "bowling_alley_closed": self.bowling_alley_closed,
            "won_bank_account": self.won_bank_account,
            "bank_storage": [item.name if item else None for item in self.bank_storage.slots],
        }

    @classmethod
    def from_save_data(cls, data, footstep_sound=None, bump_sound=None, engine_sound=None):
        scene = cls(footstep_sound, bump_sound, engine_sound)
        collected_items = {tuple(entry) for entry in data["collected_items"]}
        scene.world = World(tx=data["tx"], ty=data["ty"], collected_items=collected_items)
        scene.player.x = data["player_x"]
        scene.player.y = data["player_y"]
        scene.player.riding = data["riding"]
        scene.player.wearing_helmet = data["wearing_helmet"]
        scene.inventory.slots = [
            Item(get_item(name).name, get_item(name).color) if name is not None else None
            for name in data["inventory"]
        ]
        scene.won_machine_part = data["won_machine_part"]
        scene.bowling_high_score = data["bowling_high_score"]
        scene.won_motorcycle = data["won_motorcycle"]
        scene.won_helmet = data["won_helmet"]
        scene.fishing_high_score = data["fishing_high_score"]
        scene.won_hammer = data["won_hammer"]
        scene.motocross_best_time = data["motocross_best_time"]
        scene.player_name = data["player_name"]
        scene.bowling_alley_closed = data["bowling_alley_closed"]
        scene.won_bank_account = data["won_bank_account"]
        scene.bank_storage.slots = [
            Item(get_item(name).name, get_item(name).color) if name is not None else None
            for name in data["bank_storage"]
        ]
        return scene

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
                elif building.kind == "motocross":
                    self._open_motocross_dialogue(manager)
                elif building.kind == "spaceport":
                    self._open_spaceport_dialogue(manager)
                elif building.kind == "bank":
                    self._open_bank_dialogue(manager)
                return

    # -- bowling shack flow ---------------------------------------------------

    def _open_shack_dialogue(self, manager):
        if self.bowling_alley_closed:
            manager.push(DialogueScene(
                speaker="Shopkeep",
                line="The door's locked . . .",
                choices=["OK"],
                on_choice=lambda m, choice: m.pop(),
                wearing_helmet=self.player.wearing_helmet,
            ))
            return

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
            manager.push(BowlingScene(["Player 1"], on_finish=self._on_bowling_finish))

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

    # -- motocross flow ---------------------------------------------------------

    def _open_motocross_dialogue(self, manager):
        if not (self.player.riding and self.player.wearing_helmet):
            manager.push(DialogueScene(
                speaker="Race Official",
                line="You here to race? You'll need a bike and a helmet equipped first.",
                choices=["OK"],
                on_choice=lambda m, choice: m.pop(),
                wearing_helmet=self.player.wearing_helmet,
            ))
            return

        if self.won_hammer:
            line = f"Back to beat your best time of {self.motocross_best_time:.1f}s?"
        else:
            line = ("You here to race? You need a bike and a helmet. Beat the course "
                    f"record of {MOTOCROSS_WIN_TIME}s and win a hammer.")
        manager.push(DialogueScene(
            speaker="Race Official",
            line=line,
            choices=["Yes", "No"],
            on_choice=self._on_motocross_choice,
            wearing_helmet=self.player.wearing_helmet,
        ))

    def _on_motocross_choice(self, manager, choice):
        manager.pop()  # back to exploring either way
        if choice == "Yes":
            manager.push(MotocrossScene(on_finish=self._on_motocross_finish))

    def _on_motocross_finish(self, manager, race):
        manager.pop()  # back to exploring
        race_time = race.race_time
        is_new_best = self.motocross_best_time is None or race_time < self.motocross_best_time
        if is_new_best:
            self.motocross_best_time = race_time

        if not self.won_hammer and race_time <= MOTOCROSS_WIN_TIME:
            record = get_item("Hammer")
            self.inventory.add_item(Item(record.name, record.color))
            self.won_hammer = True
            self.show_notice(f"Time: {race_time:.1f}s - you win! Got the Hammer.")
        elif self.won_hammer and is_new_best:
            self.show_notice(f"Time: {race_time:.1f}s - new best!")
        elif self.won_hammer:
            self.show_notice(f"Time: {race_time:.1f}s. Best: {self.motocross_best_time:.1f}s.")
        else:
            self.show_notice(f"Time: {race_time:.1f}s. Try again sometime.")

    # -- spaceport flow ---------------------------------------------------------

    def _open_spaceport_dialogue(self, manager):
        # gated on Machine Part #25, per spec
        if not self.won_machine_part:
            manager.push(DialogueScene(
                speaker="Space Command",
                line="Make a name for yourself, join the Space War. We're one part away from the next launch.",
                choices=["Leave"],
                on_choice=lambda m, choice: m.pop(),
                wearing_helmet=self.player.wearing_helmet,
            ))
            return

        manager.push(DialogueScene(
            speaker="Space Command",
            line="That's the last part. Ready to fly, recruit?",
            choices=["Yes", "No"],
            on_choice=self._on_spaceport_choice,
            wearing_helmet=self.player.wearing_helmet,
        ))

    def _on_spaceport_choice(self, manager, choice):
        manager.pop()  # back to exploring either way
        if choice == "Yes":
            manager.push(SpaceWarsScene(on_finish=self._on_space_wars_finish))

    def _on_space_wars_finish(self, manager, scene):
        manager.pop()  # back to exploring
        if scene.stage == "3-2":
            self.bowling_alley_closed = True  # the Bowling Alley Guy already gave everything away and left
        if scene.player_name is not None:
            self.player_name = scene.player_name

        if scene.state == "won":
            self.show_notice(f"Stage {scene.stage} clear! The skies are safe... for now.")
        else:
            self.show_notice("Game Over. The Spaceport awaits your return.")

    # -- bank flow ----------------------------------------------------------

    def _push_dialogue_chain(self, manager, speaker, lines, on_finish):
        """Push `lines` one at a time as press-space-to-continue DialogueScenes
        (an invisible single choice, so space just advances), then call
        on_finish(manager) once the last line is dismissed."""
        def _show(m, index):
            if index >= len(lines):
                on_finish(m)
                return

            def _advance(mgr, choice):
                mgr.pop()
                _show(mgr, index + 1)

            m.push(DialogueScene(
                speaker=speaker, line=lines[index], choices=[""],
                on_choice=_advance, wearing_helmet=self.player.wearing_helmet,
            ))

        _show(manager, 0)

    def _open_bank_dialogue(self, manager):
        if self.won_bank_account:
            manager.push(DialogueScene(
                speaker="Bank Teller",
                line="Access your account?",
                choices=["Yes", "No"],
                on_choice=self._on_bank_teller_choice,
                wearing_helmet=self.player.wearing_helmet,
            ))
            return

        self._push_dialogue_chain(manager, "Bank President", [
            "Ah, a new client! Great news!",
            "We're having a special promotion for opening a new account!",
        ], on_finish=self._open_bank_promo_offer)

    def _open_bank_promo_offer(self, manager):
        manager.push(DialogueScene(
            speaker="Bank President",
            line="$10,000 US, cash, to our first new account! Do you want to open an Account?",
            choices=["Yes", "No"],
            on_choice=self._on_bank_promo_choice,
            wearing_helmet=self.player.wearing_helmet,
        ))

    def _on_bank_promo_choice(self, manager, choice):
        manager.pop()  # back to exploring either way
        if choice != "Yes":
            return

        if self.player_name is None:
            self._push_dialogue_chain(manager, "Bank President", [
                "Perfect! We just need your name!",
                " . . . ",
                "So . . . what's your name?",
                " . . .",
                "Ok so we can't open an account without a name.",
                "Why don't you come back when you, uh. . .",
                " . . . have a name . . .",
            ], on_finish=lambda m: None)
        else:
            self._push_dialogue_chain(manager, "Bank President", [
                "Excellent! Just sign right here . . . ",
                f"Ok {self.player_name}. your account is all set!",
                "We hope to serve all your banking needs. And here's the 10 piece to hold as promised.",
            ], on_finish=self._on_bank_account_opened)

    def _on_bank_account_opened(self, manager):
        record = get_item(BANK_CASH_ITEM_NAME)
        self.inventory.add_item(Item(record.name, record.color))
        self.won_bank_account = True
        self.show_notice(f"Account opened - you receive {BANK_CASH_ITEM_NAME}!")

    def _on_bank_teller_choice(self, manager, choice):
        manager.pop()  # back to exploring either way
        if choice == "Yes":
            manager.push(BankScene(self.inventory, self.bank_storage))

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
        if self.world.tile.track is not None:
            obstacles = obstacles + [self.world.tile.track]
        if self.world.tile.launchpad is not None:
            obstacles = obstacles + [self.world.tile.launchpad]
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
        if self.world.tile.track is not None:
            draw_track_decoration(surface, self.world.tile.track.rect, pygame.time.get_ticks() / 1000.0)
        if self.world.tile.launchpad is not None:
            draw_launchpad(surface, self.world.tile.launchpad.rect)
        for tree in self.world.tile.trees:
            tree.draw(surface)
        for building in self.world.tile.buildings:
            building.draw(surface)
        for world_item in self.world.tile.items:
            world_item.draw(surface)
        self.player.draw(surface, self.world.tile.trees)

        self._draw_interact_hint(surface)
        self.inventory.draw(surface, title=self.player_name)
        self._draw_inventory_hint(surface)
        self._draw_use_message(surface)
        self._draw_notice(surface)

        coord_label = self.debug_font.render(f"Tile ({self.world.tx}, {self.world.ty})", True, (200, 200, 200))
        surface.blit(coord_label, (8, 8))

    def _draw_inventory_hint(self, surface):
        if not self.inventory.is_open:
            return
        hint = self.hint_font.render("I: Close   S: Save", True, (200, 200, 200))
        surface.blit(hint, hint.get_rect(midtop=(SCREEN_WIDTH // 2, 16)))

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
