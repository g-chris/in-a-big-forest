"""scene.py — the Scene interface and a stack-based SceneManager.

The game is a stack of screens: exploring the world, a dialogue box, a
mini-game. Only the top of the stack gets input/updates/draws each frame;
pushing a scene (e.g. opening a dialogue) suspends what's under it, and
popping returns to it exactly where it left off.
"""


class Scene:
    """Base interface every scene implements. Subclasses override whichever
    of these they need; the no-ops here let a scene skip what doesn't apply
    to it (e.g. a static dialogue has nothing to do in update())."""

    def handle_event(self, event, manager):
        pass

    def update(self, dt, keys, manager):
        pass

    def draw(self, surface):
        pass


class SceneManager:
    def __init__(self, initial_scene):
        self.stack = [initial_scene]

    @property
    def current(self):
        return self.stack[-1]

    def push(self, scene):
        self.stack.append(scene)

    def pop(self):
        self.stack.pop()

    def replace(self, scene):
        self.stack[-1] = scene
