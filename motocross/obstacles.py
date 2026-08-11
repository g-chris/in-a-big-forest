"""motocross/obstacles.py — track hazards: a stationary Cactus and a moving
Racer, each placed at a fixed distance-along-track + lane. Pure logic, no
pygame — mirrors fishing/fish.py's split from its scene's rendering.
"""

CACTUS = "cactus"
RACER = "racer"
RACER_RED = (220, 30, 30)
RACER_GREEN = (30, 200, 60)

LANE_COUNT = 5
MIN_SPACING = 250
MAX_SPACING = 750
FIRST_OBSTACLE_DISTANCE = 1200  # gives the player a moment before the first hazard
RACER_CHANCE = 0.7              # vs. cactus, per spawn point


class Cactus:
    kind = CACTUS

    def __init__(self, distance, lane, arms):
        self.distance = distance  # fixed position along the track
        self.lane = lane
        self.arms = arms          # from _random_arms(rng), stable per instance
        self.destroyed = False


class Racer:
    kind = RACER

    def __init__(self, distance, lane, helmet_color, speed):
        self.distance = distance  # advances every frame, unlike Cactus
        self.lane = lane
        self.helmet_color = helmet_color
        self.speed = speed

    def update(self, dt):
        self.distance += self.speed * dt


def _random_arms(rng):
    """0-3 arms, each a (side, height_frac) pair — a stable, randomized
    shape generated once per cactus so it doesn't reshuffle every frame."""
    count = rng.randint(0, 3)
    return [(rng.choice((-1, 1)), rng.uniform(0.35, 0.75)) for _ in range(count)]


def spawn_obstacles(rng, track_distance, base_speed, racer_speed_multiplier):
    """A list of Cactus/Racer hazards spanning the race, randomized lane and
    type, spaced so a lane change always has time to land before the next one."""
    obstacles = []
    distance = FIRST_OBSTACLE_DISTANCE
    while distance < track_distance - MIN_SPACING:
        lane = rng.randrange(LANE_COUNT)
        if rng.random() < RACER_CHANCE:
            helmet_color = rng.choice((RACER_RED, RACER_GREEN))
            obstacles.append(Racer(distance, lane, helmet_color, base_speed * racer_speed_multiplier))
        else:
            obstacles.append(Cactus(distance, lane, _random_arms(rng)))
        distance += rng.uniform(MIN_SPACING, MAX_SPACING)
    return obstacles
