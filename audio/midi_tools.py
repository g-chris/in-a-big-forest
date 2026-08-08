"""midi_tools.py — a tiny, dependency-free MIDI file writer.

Build simple background music by writing notes, chords, and rests as plain
Python, then export a Standard MIDI File (.mid) that any DAW, softsynth, or
media player can play. No external libraries required.

Example:
    from midi_tools import Track, MidiFile

    melody = Track(name="Melody", instrument=INSTRUMENTS["flute"])
    melody.note("E4", 0.5)
    melody.note("G4", 0.5)
    melody.note("B4", 1.0)
    melody.rest(0.5)
    melody.chord(["C4", "E4", "G4"], 1.0)

    MidiFile(tempo=100).add_track(melody).save("soundtrack.mid")

Run this file directly to generate a short example track (soundtrack.mid).
"""

import re
import struct

# A handful of General MIDI program numbers (0-127) worth naming for a
# forest-themed soundtrack. Any GM program number can be used directly too.
INSTRUMENTS = {
    "acoustic_grand_piano": 0,
    "music_box": 10,
    "acoustic_guitar_nylon": 24,
    "pizzicato_strings": 45,
    "string_ensemble": 48,
    "flute": 73,
    "pan_flute": 75,
    "ocarina": 79,
    "pad_warm": 89,
}

_PITCH_CLASS = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
_NOTE_RE = re.compile(r"^([A-Ga-g])([#b]?)(-?\d+)$")


def note_name_to_number(name):
    """Convert a note name like 'C4', 'F#3', 'Bb5' into a MIDI note number (0-127).

    Octave numbering follows the common convention where C4 is middle C (60).
    """
    match = _NOTE_RE.match(name.strip())
    if not match:
        raise ValueError(f"Invalid note name: {name!r}")
    letter, accidental, octave = match.groups()
    number = _PITCH_CLASS[letter.upper()]
    if accidental == "#":
        number += 1
    elif accidental == "b":
        number -= 1
    number += (int(octave) + 1) * 12
    if not 0 <= number <= 127:
        raise ValueError(f"Note {name!r} is out of MIDI range (0-127)")
    return number


def _vlq(value):
    """Encode a non-negative integer as a MIDI variable-length quantity."""
    chunks = [value & 0x7F]
    value >>= 7
    while value:
        chunks.append((value & 0x7F) | 0x80)
        value >>= 7
    return bytes(reversed(chunks))


class Track:
    """A single instrument line: a sequence of notes, chords, and rests."""

    def __init__(self, name="Track", instrument=0, channel=0, volume=100):
        self.name = name
        self.instrument = instrument  # General MIDI program number, 0-127
        self.channel = channel        # 0-15 (channel 9 is the GM drum kit)
        self.volume = volume          # 0-127
        self._events = []  # (pitches-or-None, duration_in_beats, velocity)

    def note(self, pitch, duration, velocity=100):
        """Queue a single note for `duration` beats (1.0 = a quarter note).

        `pitch` may be a note name ('A4') or a raw MIDI number (0-127).
        """
        self._events.append(([pitch], duration, velocity))
        return self

    def chord(self, pitches, duration, velocity=100):
        """Queue several notes to be played together for the same duration."""
        self._events.append((list(pitches), duration, velocity))
        return self

    def rest(self, duration):
        """Queue `duration` beats of silence."""
        self._events.append((None, duration, 0))
        return self

    def repeat(self, times):
        """Duplicate everything queued so far so it plays `times` times in total."""
        self._events = self._events * times
        return self

    def _resolve(self, pitch):
        return pitch if isinstance(pitch, int) else note_name_to_number(pitch)

    def _to_chunk(self, ticks_per_beat):
        events = []  # (tick, is_note_on, pitch, velocity)
        cursor = 0
        for pitches, duration, velocity in self._events:
            ticks = round(duration * ticks_per_beat)
            if pitches is not None:
                for pitch in pitches:
                    number = self._resolve(pitch)
                    events.append((cursor, True, number, velocity))
                    events.append((cursor + ticks, False, number, velocity))
            cursor += ticks
        # note-offs before note-ons at the same tick, so back-to-back
        # repeats of the same pitch don't get swallowed
        events.sort(key=lambda e: (e[0], e[1]))

        data = bytearray()

        def meta(delta, meta_type, payload):
            data.extend(_vlq(delta))
            data.extend(bytes([0xFF, meta_type, len(payload)]))
            data.extend(payload)

        def channel_event(delta, status, byte1, byte2=None):
            data.extend(_vlq(delta))
            data.append(status | self.channel)
            data.append(byte1)
            if byte2 is not None:
                data.append(byte2)

        meta(0, 0x03, self.name.encode("ascii", errors="replace"))  # track name
        channel_event(0, 0xC0, self.instrument)                      # program change
        channel_event(0, 0xB0, 7, self.volume)                       # channel volume

        prev_tick = 0
        for tick, is_on, pitch, velocity in events:
            status = 0x90 if is_on else 0x80
            channel_event(tick - prev_tick, status, pitch, velocity if is_on else 0)
            prev_tick = tick

        meta(0, 0x2F, b"")  # end of track

        return b"MTrk" + struct.pack(">I", len(data)) + bytes(data)


class MidiFile:
    """A set of Tracks that play together, written out as a format-1 .mid file."""

    def __init__(self, tempo=120, ticks_per_beat=480, time_signature=(4, 4)):
        self.tempo = tempo  # beats per minute
        self.ticks_per_beat = ticks_per_beat
        self.time_signature = time_signature
        self.tracks = []

    def add_track(self, track):
        self.tracks.append(track)
        return self

    def _tempo_chunk(self):
        data = bytearray()
        numerator, denominator = self.time_signature
        data.extend(_vlq(0))
        data.extend(bytes([0xFF, 0x58, 0x04, numerator, denominator.bit_length() - 1, 24, 8]))
        micros_per_beat = round(60_000_000 / self.tempo)
        data.extend(_vlq(0))
        data.extend(bytes([0xFF, 0x51, 0x03]) + struct.pack(">I", micros_per_beat)[1:])
        data.extend(_vlq(0))
        data.extend(bytes([0xFF, 0x2F, 0x00]))  # end of track
        return b"MTrk" + struct.pack(">I", len(data)) + bytes(data)

    def save(self, path):
        if not self.tracks:
            raise ValueError("Add at least one Track before saving")
        chunks = [self._tempo_chunk()] + [t._to_chunk(self.ticks_per_beat) for t in self.tracks]
        header = struct.pack(">4sIHHH", b"MThd", 6, 1, len(chunks), self.ticks_per_beat)
        with open(path, "wb") as f:
            f.write(header)
            for chunk in chunks:
                f.write(chunk)
        return path


def build_forest_theme(path="soundtrack.mid"):
    """Compose the demo forest theme (pan-flute melody over a warm pad) and save it."""
    melody = Track(name="Melody", instrument=INSTRUMENTS["pan_flute"])
    phrase = [
        ("E4", 0.5), ("G4", 0.5), ("A4", 1.0),
        ("G4", 0.5), ("E4", 0.5), ("D4", 1.0),
        ("C4", 0.5), ("D4", 0.5), ("E4", 1.0),
        ("D4", 0.5), ("C4", 0.5), ("B3", 1.0),
    ]
    for pitch, duration in phrase:
        melody.note(pitch, duration, velocity=95)
    melody.repeat(2)

    pad = Track(name="Pad", instrument=INSTRUMENTS["pad_warm"], channel=1, volume=70)
    for chord in [["C3", "E3", "G3"], ["A2", "C3", "E3"], ["F2", "A2", "C3"], ["G2", "B2", "D3"]]:
        pad.chord(chord, 4.0, velocity=55)
    pad.repeat(2)

    return MidiFile(tempo=96).add_track(melody).add_track(pad).save(path)


if __name__ == "__main__":
    print(f"Wrote {build_forest_theme()}")
