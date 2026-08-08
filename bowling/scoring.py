"""bowling/scoring.py — standard 10-frame bowling scoring over a flat list
of pinfalls, in the order they were thrown.

The 10th frame's bonus rolls (for a strike or spare) just land at the tail
of the same flat list, so this one loop handles them without a special case.
"""

FRAMES_PER_GAME = 10
STRIKE = 10


def _at(rolls, idx):
    return rolls[idx] if idx < len(rolls) else 0


def score_game(rolls):
    """Total score for a completed (or in-progress) game given a flat list
    of pinfalls. Bonus rolls not yet thrown count as 0, so this also works
    as a live/partial scoreboard total."""
    total = 0
    i = 0
    for _ in range(FRAMES_PER_GAME):
        if _at(rolls, i) == STRIKE:
            total += STRIKE + _at(rolls, i + 1) + _at(rolls, i + 2)
            i += 1
        elif _at(rolls, i) + _at(rolls, i + 1) == STRIKE:
            total += STRIKE + _at(rolls, i + 2)
            i += 2
        else:
            total += _at(rolls, i) + _at(rolls, i + 1)
            i += 2
    return total


def frame_breakdown(rolls):
    """Per-frame detail for a scoreboard display: a list of up to 10 dicts,
    each `{"rolls": [...], "total": cumulative score after this frame}`,
    covering only the frames that have at least started."""
    breakdown = []
    i = 0
    for frame in range(FRAMES_PER_GAME):
        if i >= len(rolls):
            break
        if frame == FRAMES_PER_GAME - 1:
            # 10th frame keeps every roll thrown there (2 or 3)
            frame_rolls = rolls[i:]
            i = len(rolls)
        elif rolls[i] == STRIKE:
            frame_rolls = [rolls[i]]
            i += 1
        else:
            frame_rolls = rolls[i:i + 2]
            i += len(frame_rolls)
        breakdown.append({"rolls": frame_rolls, "total": score_game(rolls[:i])})
    return breakdown
