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
