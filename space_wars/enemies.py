"""space_wars/enemies.py — enemy state machines for SPACE WARS. Pure logic,
no pygame — mirrors fishing/fish.py and motocross/obstacles.py's split from
their scene's rendering.

SwarmEnemy: enter from off-screen, loop three times in a row (firing four
shots at each loop's quarter-points), then dive in a straight line toward a
one-time-captured point (not a homing chase), accelerating constantly for
the whole dive.

Launcher: enter from off-screen down to a patrol row, then drift
horizontally, taking a random action (change direction, fire a 3-shot
spread, or request a Swarm ship be spawned) every LAUNCHER_ACTION_INTERVAL
seconds.

Seeker: enter from the side, then wander randomly, pulled toward the
player's position for a few seconds every time the scene tells it
(notify_shot) the player has fired. Fires a single shot straight down
every few seconds; the scene calls explode() once it reaches the bottom
of the play area for a radial burst.

Boss: enter from off-screen down to a patrol row, then float slowly back
and forth across the screen (the scene supplies the bounds it bounces
between), firing a burst (a laser fan + straight-down bombs) at a
randomly re-rolled interval. Never reaches DONE — there is no code path
that destroys it.
"""

import math

ENTERING = "entering"
LOOPING = "looping"
DIVING = "diving"
DONE = "done"

ENTER_SPEED = 220        # px/s, straight down from off-screen to formation row
LOOP_DURATION = 1.2      # seconds for one loop pass
LOOP_REPEATS = 3         # loop passes before diving
LOOP_RADIUS = 30
DIVE_SPEED = 260         # px/s once diving starts
DIVE_ACCEL = 200         # px/s^2, constant speed-up for the whole dive — tune freely
SHOT_FRACTIONS = [0.5]  # points of each loop pass that fire (currently: halfway)


class SwarmEnemy:
    def __init__(self, formation_x, formation_y, stagger_delay, instant=False):
        self.formation_x = formation_x
        self.formation_y = formation_y
        self.x = formation_x
        self.y = formation_y if instant else -40.0  # instant: appear in place, skip the off-screen entry
        self.state = LOOPING if instant else ENTERING
        self.stagger_delay = stagger_delay  # extra wait once formation is reached, before looping
        self.loop_t = 0.0
        self.loops_completed = 0
        self._next_shot_index = 0
        self.dive_dx = 0.0
        self.dive_dy = 0.0
        self.dive_speed = DIVE_SPEED

    def update(self, dt, player_x, player_y):
        """Advances one frame; returns a list of (x, y) points where this
        enemy fired a shot this frame (usually empty) — the scene turns
        these into real projectiles, keeping this module free of pygame."""
        if self.state == ENTERING:
            self.y += ENTER_SPEED * dt
            if self.y >= self.formation_y:
                self.y = self.formation_y
                self.state = LOOPING
            return []

        if self.state == LOOPING:
            if self.stagger_delay > 0:
                self.stagger_delay -= dt
                return []

            self.loop_t += dt / LOOP_DURATION
            fraction = min(1.0, self.loop_t)
            angle = fraction * 2 * math.pi
            self.x = self.formation_x + LOOP_RADIUS * math.sin(angle)
            self.y = self.formation_y + LOOP_RADIUS * (1 - math.cos(angle))

            shots = []
            while (self._next_shot_index < len(SHOT_FRACTIONS)
                   and fraction >= SHOT_FRACTIONS[self._next_shot_index]):
                shots.append((self.x, self.y))
                self._next_shot_index += 1

            if self.loop_t >= 1.0:
                self.loops_completed += 1
                if self.loops_completed < LOOP_REPEATS:
                    self.loop_t = 0.0
                    self._next_shot_index = 0
                else:
                    self.x = self.formation_x
                    self.y = self.formation_y
                    dx, dy = player_x - self.x, player_y - self.y
                    dist = math.hypot(dx, dy) or 1.0
                    self.dive_dx, self.dive_dy = dx / dist, dy / dist
                    self.state = DIVING
            return shots

        if self.state == DIVING:
            self.dive_speed += DIVE_ACCEL * dt
            self.x += self.dive_dx * self.dive_speed * dt
            self.y += self.dive_dy * self.dive_speed * dt
            return []

        return []  # DONE


DRIFTING = "drifting"

LAUNCHER_ENTER_SPEED = 150       # px/s, straight down to its patrol row
LAUNCHER_DRIFT_SPEED = 100        # px/s, horizontal patrol speed — tune freely
LAUNCHER_ACTION_INTERVAL = 2.5   # seconds between random actions — tune freely
LAUNCHER_SPREAD_ANGLE = 25       # degrees, each side of straight down, for the 3-shot spread


class Launcher:
    def __init__(self, entry_x, target_y, rng):
        self.x = entry_x
        self.y = -40.0  # starts off-screen above
        self.target_y = target_y  # the patrol row, chosen by the scene
        self.state = ENTERING
        self.rng = rng  # a random.Random the scene seeds from its own rng
        self.direction = rng.choice([-1, 1])
        self.action_timer = LAUNCHER_ACTION_INTERVAL
        self.shield_active = True  # absorbs one player-laser hit before the ship itself is vulnerable

    def update(self, dt):
        """Advances one frame; returns (shots, spawn_requested). `shots` is
        a list of (x, y, dx, dy) points with (dx, dy) a unit direction —
        the scene scales this by its own laser speed, keeping this module
        screen/speed agnostic, same as SwarmEnemy's plain (x, y) points.
        `spawn_requested` is True the one frame this Launcher wants a new
        Swarm ship spawned at its current position."""
        if self.state == ENTERING:
            self.y += LAUNCHER_ENTER_SPEED * dt
            if self.y >= self.target_y:
                self.y = self.target_y
                self.state = DRIFTING
            return [], False

        if self.state == DRIFTING:
            self.x += self.direction * LAUNCHER_DRIFT_SPEED * dt

            self.action_timer -= dt
            if self.action_timer <= 0:
                self.action_timer = LAUNCHER_ACTION_INTERVAL
                roll = self.rng.random()
                if roll < 0.5:
                    self.direction *= -1
                elif roll < 0.75:
                    return self._spread_shots(), False
                else:
                    return [], True  # spawn a Swarm ship
            return [], False

        return [], False  # DONE

    def _spread_shots(self):
        shots = []
        for angle_deg in (-LAUNCHER_SPREAD_ANGLE, 0, LAUNCHER_SPREAD_ANGLE):
            angle = math.radians(angle_deg)
            shots.append((self.x, self.y, math.sin(angle), math.cos(angle)))
        return shots


ACTIVE = "active"

SEEKER_ENTER_SPEED = 200        # px/s while entering from the side
SEEKER_ENTER_DISTANCE = 80       # px moved inward before switching to ACTIVE
SEEKER_SPEED = 130               # px/s, both wandering and seeking — tune freely
SEEKER_WANDER_CHANGE_INTERVAL = 1.5   # seconds between random new wander directions
SEEKER_SEEK_DURATION = 2.0        # seconds spent heading toward the last player shot
SEEKER_SHOT_INTERVAL = 3.0        # seconds between its own downward laser shots
SEEKER_EXPLOSION_SHOT_COUNT = 8   # radial burst size when it reaches the bottom


class Seeker:
    def __init__(self, entry_x, entry_y, direction, rng):
        self.x, self.y = entry_x, entry_y
        self.entry_x = entry_x
        self.direction = direction  # +1 entering from the left, -1 from the right
        self.state = ENTERING
        self.rng = rng  # a random.Random the scene seeds from its own rng
        self.wander_dx = 0.0
        self.wander_dy = 0.0
        self.wander_timer = 0.0  # <=0 forces an immediate direction roll on the first ACTIVE frame
        self.seek_timer = 0.0
        self.seek_target_x = 0.0
        self.seek_target_y = 0.0
        self.shot_timer = SEEKER_SHOT_INTERVAL

    def update(self, dt):
        """Advances one frame; returns a list of (x, y, dx, dy) shot
        tuples for its own periodic downward laser (usually empty). The
        scene separately checks the screen-relative "reached the bottom"
        condition and calls explode() when that happens — this class has
        no notion of screen bounds."""
        if self.state == ENTERING:
            self.x += self.direction * SEEKER_ENTER_SPEED * dt
            if abs(self.x - self.entry_x) >= SEEKER_ENTER_DISTANCE:
                self.state = ACTIVE
            return []

        if self.state == ACTIVE:
            if self.seek_timer > 0:
                self.seek_timer -= dt
                dx, dy = self.seek_target_x - self.x, self.seek_target_y - self.y
                dist = math.hypot(dx, dy) or 1.0
                self.x += dx / dist * SEEKER_SPEED * dt
                self.y += dy / dist * SEEKER_SPEED * dt
            else:
                self.wander_timer -= dt
                if self.wander_timer <= 0:
                    angle = self.rng.uniform(0, 2 * math.pi)
                    self.wander_dx, self.wander_dy = math.cos(angle), math.sin(angle)
                    self.wander_timer = SEEKER_WANDER_CHANGE_INTERVAL
                self.x += self.wander_dx * SEEKER_SPEED * dt
                self.y += self.wander_dy * SEEKER_SPEED * dt

            shots = []
            self.shot_timer -= dt
            if self.shot_timer <= 0:
                self.shot_timer = SEEKER_SHOT_INTERVAL
                shots.append((self.x, self.y, 0.0, 1.0))  # straight down
            return shots

        return []  # DONE

    def notify_shot(self, x, y):
        """Called by the scene once per player shot fired — retargets and
        refreshes the seek window, even mid-seek (rapid fire keeps it
        homing continuously on the player's live position)."""
        self.seek_target_x, self.seek_target_y = x, y
        self.seek_timer = SEEKER_SEEK_DURATION

    def explode(self):
        """Call when the scene detects this Seeker reached the bottom of
        the play area: destroys it and returns the 8-shot radial burst."""
        self.state = DONE
        return [(self.x, self.y, math.cos(a), math.sin(a))
                for a in (2 * math.pi * i / SEEKER_EXPLOSION_SHOT_COUNT
                          for i in range(SEEKER_EXPLOSION_SHOT_COUNT))]


BOSS_ENTER_SPEED = 80          # px/s while descending to its patrol row
BOSS_MOVE_SPEED = 40            # very slow "floating" patrol speed — tune freely
BOSS_SHOT_MIN_INTERVAL = 2.0
BOSS_SHOT_MAX_INTERVAL = 6.0     # re-rolled after every burst
BOSS_LASER_COUNT = 4
BOSS_LASER_SPREAD_ANGLE = 35     # degrees each side of straight down, for the laser fan
BOSS_BOMB_COUNT = 3
BOSS_BOMB_OFFSET = 60            # px between each dropped bomb's x position
BOSS_SHIELD_FLASH_DURATION = 3.0  # seconds the shield flashes before disappearing, after the 2nd charge hit


class Boss:
    def __init__(self, entry_x, target_y, rng, max_hp=None):
        self.x, self.y = entry_x, -60.0
        self.target_y = target_y  # the patrol row, chosen by the scene
        self.state = ENTERING
        self.rng = rng  # a random.Random the scene seeds from its own rng
        self.direction = rng.choice([-1, 1])
        self.shot_timer = rng.uniform(BOSS_SHOT_MIN_INTERVAL, BOSS_SHOT_MAX_INTERVAL)

        self.shield_hits = 0
        self.shield_flash_timer = 0.0
        self.shield_removed = False
        self.max_hp = max_hp  # None = impenetrable (e.g. stage 1's decorative Boss)
        self.hp = max_hp
        self.defeated = False

    def update(self, dt, min_x, max_x):
        """Advances one frame; returns a list of (x, y, dx, dy, kind)
        shots (usually empty), `kind` being "laser" or "bomb" so the scene
        can draw/tag them differently. `min_x`/`max_x` are the
        screen-relative bounds it bounces between, supplied by the scene
        each call — this class has no notion of screen size."""
        if self.shield_flash_timer > 0:
            self.shield_flash_timer -= dt
            if self.shield_flash_timer <= 0:
                self.shield_removed = True

        if self.state == ENTERING:
            self.y += BOSS_ENTER_SPEED * dt
            if self.y >= self.target_y:
                self.y = self.target_y
                self.state = ACTIVE
            return []

        # ACTIVE: float back and forth, firing a full burst at a freshly
        # re-rolled random interval
        self.x += self.direction * BOSS_MOVE_SPEED * dt
        if self.x <= min_x:
            self.x, self.direction = min_x, 1
        elif self.x >= max_x:
            self.x, self.direction = max_x, -1

        self.shot_timer -= dt
        if self.shot_timer <= 0:
            self.shot_timer = self.rng.uniform(BOSS_SHOT_MIN_INTERVAL, BOSS_SHOT_MAX_INTERVAL)
            return self._fire_burst()
        return []

    def _fire_burst(self):
        shots = []
        for i in range(BOSS_LASER_COUNT):
            t = i / (BOSS_LASER_COUNT - 1)
            angle = math.radians(-BOSS_LASER_SPREAD_ANGLE + t * 2 * BOSS_LASER_SPREAD_ANGLE)
            shots.append((self.x, self.y, math.sin(angle), math.cos(angle), "laser"))
        for i in range(BOSS_BOMB_COUNT):
            offset = (i - (BOSS_BOMB_COUNT - 1) / 2) * BOSS_BOMB_OFFSET
            shots.append((self.x + offset, self.y, 0.0, 1.0, "bomb"))
        return shots

    def hit_shield(self):
        """Call when a charge shot connects with the still-present shield.
        A no-op once it's already flashing or fully removed, so a single
        piercing shot lingering nearby can't rack up extra hits."""
        if self.shield_removed or self.shield_flash_timer > 0:
            return
        self.shield_hits += 1
        if self.shield_hits >= 2:
            self.shield_flash_timer = BOSS_SHIELD_FLASH_DURATION

    def damage(self, amount):
        """A no-op until the shield is fully gone (or if this Boss has no
        HP system at all, i.e. max_hp is None — the impenetrable case)."""
        if self.max_hp is None or not self.shield_removed or self.defeated:
            return
        self.hp = max(0, self.hp - amount)
        if self.hp <= 0:
            self.defeated = True
