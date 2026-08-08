"""fishing/fish.py — a single fish's state machine: swim, get hooked (or
flee), fight, and end up either caught or gone for good.

    SWIMMING -> NIBBLING -> HOOKED_WRIGGLE <-> HOOKED_STILL -> CAUGHT
                    \\-> ESCAPING -> GONE <-------------------/ (escape)

Nothing here talks to pygame — `fishing/scene.py` owns rendering and input;
this module is pure state so it can be unit-tested with scripted input.
"""

import math

# bigger fish: more (harder to read) pokes, a shorter hookset window, sink
# faster if fought while wriggling, and gain more slowly when reeled calm
FISH_CLASSES = [
    {"name": "Small Fry", "min_kg": 6, "max_kg": 12, "count": 4,
     "pokes": (1, 2), "hang_time": 1.0, "pull_fast": 40, "pull_slow": 15, "reel_speed": 70},
    {"name": "Reg Fish", "min_kg": 13, "max_kg": 20, "count": 3,
     "pokes": (2, 3), "hang_time": 0.8, "pull_fast": 55, "pull_slow": 20, "reel_speed": 60},
    {"name": "Lunker", "min_kg": 21, "max_kg": 30, "count": 2,
     "pokes": (3, 4), "hang_time": 0.6, "pull_fast": 70, "pull_slow": 25, "reel_speed": 50},
    {"name": "Legend", "min_kg": 50, "max_kg": 100, "count": 1,
     "pokes": (4, 6), "hang_time": 0.45, "pull_fast": 90, "pull_slow": 35, "reel_speed": 40},
]

MAX_DEPTH = 320  # depth units == screen pixels below the boat (see fishing/scene.py)
CATCH_DEPTH = 20  # a fish is landed once reeled to within this much of the boat
PROXIMITY_X = 40
PROXIMITY_DEPTH = 35

WRIGGLE_TIME_RANGE = (0.2, 0.8)
STILL_TIME_RANGE = (0.5, 3.0)
NIBBLE_POKE_INTERVAL = 0.5
ESCAPE_DURATION = 0.8
PATROL_SPEED = 0.6  # radians/sec of the patrol sine wave

SWIMMING = "swimming"
NIBBLING = "nibbling"
HOOKED_WRIGGLE = "hooked_wriggle"
HOOKED_STILL = "hooked_still"
ESCAPING = "escaping"
CAUGHT = "caught"
GONE = "gone"

ACTIVE_STATES = (SWIMMING, NIBBLING, HOOKED_WRIGGLE, HOOKED_STILL, ESCAPING)
ENGAGED_STATES = (NIBBLING, HOOKED_WRIGGLE, HOOKED_STILL, ESCAPING)


class Fish:
    def __init__(self, cls, home_x, patrol_range, depth, rng):
        self.cls = cls
        self.name = cls["name"]
        self.weight_kg = rng.randint(cls["min_kg"], cls["max_kg"])
        self.home_x = home_x
        self.patrol_range = patrol_range
        self.depth = depth
        self.x = home_x
        self.rng = rng

        self.state = SWIMMING
        self.patrol_phase = rng.uniform(0, 6.28)
        self.wiggle_phase = 0.0

        self.poke_count = 0
        self.real_poke_index = 0
        self.poke_index = 0
        self.poke_timer = 0.0
        self.hang_timer = 0.0
        self.hang_time_total = 0.0
        self.in_hang_window = False

        self.fight_timer = 0.0
        self.escape_timer = 0.0
        self.just_hooked = False  # true for one frame: hookset succeeded
        self.just_lost = False    # true for one frame: fish faded away for good

    def update(self, dt, hook_x, hook_depth, hook_available, space_pressed, space_held):
        """One frame of simulation.

        `hook_x`/`hook_depth`: the freely-controlled hook's current position
        (only meaningful — and only checked — while `hook_available`).
        `hook_available`: True if no other fish currently has the hook's
        attention, so this fish is allowed to start nibbling.
        `space_pressed`: Space was pressed *this frame* (edge, not held) —
        used for the hookset.
        `space_held`: Space is currently held — used for reeling/fighting.
        """
        self.just_hooked = False
        self.just_lost = False

        fast_wiggle = self.state in (NIBBLING, HOOKED_WRIGGLE)
        self.wiggle_phase += dt * (9 if fast_wiggle else 3)

        # once a fish is on the line, it's attached to it — follow the
        # hook horizontally so it doesn't appear to hang in open water
        # while the boat moves. Purely cosmetic: nothing below reads .x
        # again for these states, so this can't affect the fight/hookset
        # logic.
        if self.state in (NIBBLING, HOOKED_WRIGGLE, HOOKED_STILL):
            self.x = hook_x

        if self.state == SWIMMING:
            self._update_swimming(dt, hook_x, hook_depth, hook_available)
        elif self.state == NIBBLING:
            self._update_nibbling(dt, space_pressed)
        elif self.state in (HOOKED_WRIGGLE, HOOKED_STILL):
            self._update_fight(dt, space_held)
        elif self.state == ESCAPING:
            self.escape_timer += dt
            if self.escape_timer >= ESCAPE_DURATION:
                self.state = GONE
                self.just_lost = True

    def _update_swimming(self, dt, hook_x, hook_depth, hook_available):
        self.patrol_phase += dt * PATROL_SPEED
        self.x = self.home_x + (self.patrol_range / 2) * math.sin(self.patrol_phase)
        if hook_available and self._hook_in_range(hook_x, hook_depth):
            self._start_nibble()

    def _hook_in_range(self, hook_x, hook_depth):
        return abs(self.x - hook_x) < PROXIMITY_X and abs(self.depth - hook_depth) < PROXIMITY_DEPTH

    def _start_nibble(self):
        self.state = NIBBLING
        self.poke_count = self.rng.randint(*self.cls["pokes"])
        self.real_poke_index = self.rng.randrange(self.poke_count)
        self.poke_index = 0
        self.poke_timer = 0.0
        self.in_hang_window = False

    def _update_nibbling(self, dt, space_pressed):
        if self.in_hang_window:
            self.hang_timer -= dt
            if space_pressed:
                self._start_fight()
                self.just_hooked = True
            elif self.hang_timer <= 0:
                self.state = ESCAPING
                self.escape_timer = 0.0
            return

        self.poke_timer += dt
        if self.poke_timer >= NIBBLE_POKE_INTERVAL:
            self.poke_timer -= NIBBLE_POKE_INTERVAL
            if self.poke_index == self.real_poke_index:
                self.in_hang_window = True
                self.hang_timer = self.cls["hang_time"]
                self.hang_time_total = self.cls["hang_time"]
            self.poke_index += 1

    def _start_fight(self):
        self.state = HOOKED_WRIGGLE
        self.fight_timer = self.rng.uniform(*WRIGGLE_TIME_RANGE)

    def _update_fight(self, dt, space_held):
        self.fight_timer -= dt
        if self.fight_timer <= 0:
            if self.state == HOOKED_WRIGGLE:
                self.state = HOOKED_STILL
                self.fight_timer = self.rng.uniform(*STILL_TIME_RANGE)
            else:
                self.state = HOOKED_WRIGGLE
                self.fight_timer = self.rng.uniform(*WRIGGLE_TIME_RANGE)

        if self.state == HOOKED_WRIGGLE:
            self.depth += (self.cls["pull_fast"] if space_held else self.cls["pull_slow"]) * dt
        elif space_held:  # HOOKED_STILL: only progress while actively reeling
            self.depth -= self.cls["reel_speed"] * dt

        self.depth = max(0.0, min(MAX_DEPTH, self.depth))
        if self.depth <= CATCH_DEPTH:
            self.state = CAUGHT
        elif self.depth >= MAX_DEPTH:
            self.state = ESCAPING
            self.escape_timer = 0.0


def spawn_fish(rng, min_x, max_x, min_depth=40):
    """A fresh pool of fish per FISH_CLASSES' counts, positioned randomly
    across [min_x, max_x] at random depths."""
    fish_list = []
    for cls in FISH_CLASSES:
        for _ in range(cls["count"]):
            home_x = rng.uniform(min_x, max_x)
            depth = rng.uniform(min_depth, MAX_DEPTH - min_depth)
            patrol_range = rng.uniform(30, 60)
            fish_list.append(Fish(cls, home_x, patrol_range, depth, rng))
    rng.shuffle(fish_list)
    return fish_list
