"""bowling/match.py — turn order and per-player frame state for a 1-4
player, 10-frame bowling match.

Built multiplayer-capable from the start so the same engine can later be
launched from a main-menu "MiniGames" flow with more than one player; the
in-world bowling shack always starts a 1-player match today, which just
exercises this same logic with a single player (see BowlingMatch below —
there's no separate single-player code path).
"""

from .scoring import score_game

MAX_PLAYERS = 4
FRAMES_PER_GAME = 10
PINS = 10
LAST_FRAME = FRAMES_PER_GAME - 1


class PlayerState:
    def __init__(self, name):
        self.name = name
        self.frames = [[] for _ in range(FRAMES_PER_GAME)]
        self.current_frame = 0  # 0-indexed; 10 once the game is finished

    @property
    def is_done(self):
        return self.current_frame >= FRAMES_PER_GAME

    @property
    def score(self):
        rolls = [pins for frame in self.frames for pins in frame]
        return score_game(rolls)

    def pins_standing(self):
        """How many pins are up for the next roll in the current frame."""
        frame = self.frames[self.current_frame]
        if not frame:
            return PINS

        if self.current_frame < LAST_FRAME:
            # frames 1-9: a frame with a roll already in it (and not yet
            # complete) means that roll wasn't a strike, so exactly 1 roll
            return PINS - frame[0]

        # 10th frame: the rack resets after a strike or a spare, since those
        # earn bonus ball(s); otherwise the remaining pins carry over
        if len(frame) == 1:
            return PINS if frame[0] == PINS else PINS - frame[0]
        # len(frame) == 2 here (3 would mean the frame is already complete)
        if frame[0] == PINS:
            return PINS if frame[1] == PINS else PINS - frame[1]
        if frame[0] + frame[1] == PINS:
            return PINS  # spare earned, bonus ball gets a fresh rack
        return PINS  # unreachable: an open 10th frame is complete at 2 rolls

    def record_roll(self, pins):
        self.frames[self.current_frame].append(pins)
        if self._frame_complete():
            self.current_frame += 1

    def _frame_complete(self):
        frame = self.frames[self.current_frame]
        if self.current_frame < LAST_FRAME:
            return len(frame) == 2 or frame[0] == PINS
        if len(frame) < 2:
            return False
        if len(frame) == 2:
            return not (frame[0] == PINS or frame[0] + frame[1] == PINS)
        return True  # 3 rolls thrown in the 10th — always done


class BowlingMatch:
    def __init__(self, player_names, bumpers=True):
        assert 1 <= len(player_names) <= MAX_PLAYERS
        self.players = [PlayerState(name) for name in player_names]
        self.bumpers = bumpers
        self.current_index = 0

    @property
    def current_player(self):
        return self.players[self.current_index]

    @property
    def is_game_over(self):
        return all(p.is_done for p in self.players)

    def pins_standing(self):
        return self.current_player.pins_standing()

    def record_roll(self, pins_knocked):
        """Record a throw for the current player, then advance turn order —
        only to the *next* player if that roll just finished this player's
        frame; otherwise they throw again (their 2nd/3rd ball)."""
        player = self.current_player
        pins_knocked = min(pins_knocked, self.pins_standing())
        frame_before = player.current_frame
        player.record_roll(pins_knocked)
        if player.current_frame != frame_before:
            self._advance_to_next_active_player()

    def _advance_to_next_active_player(self):
        if self.is_game_over:
            return
        for _ in range(len(self.players)):
            self.current_index = (self.current_index + 1) % len(self.players)
            if not self.current_player.is_done:
                return
