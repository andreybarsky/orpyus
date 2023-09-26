### unimplemented module, TBD

### but will eventually handle melodies, time signatures, swing ratios and so on

from .audio import LogEnv, white_noise, smooth, fs, play_wave
from . import conversion as conv
from . import notes
import numpy as np

# audio samples for major and minor drumbeats:
major_beat_audio = smooth(LogEnv(white_noise(0.06)),ratio=1000)
medium_beat_audio = smooth(LogEnv(white_noise(0.05)),ratio=1000) * 0.6
minor_beat_audio = smooth(LogEnv(white_noise(0.04)),ratio=1000) * 0.6
reference_tempo = 120.

class TimeSignature:
    """a time signature representing the beats of a bar at a specific tempo"""
    def __init__(self, beats_per_bar, beat_value, tempo=reference_tempo):
        assert beats_per_bar == int(beats_per_bar), "upper numeral must be a whole number"
        self.beats_per_bar = int(beats_per_bar) # upper numeral

        assert beat_value == int(beat_value), "lower numeral must be a whole number"
        self.beat_value = int(beat_value)       # lower numeral

        self.bar_length_in_beats = self.beats_per_bar / self.beat_value
        self.quarter_notes_per_beat = 4 / self.beat_value

        self.beats_per_minute = self.tempo = self.bpm = tempo
        self.bars_per_minute = self.tempo / self.beats_per_bar
        self.bar_duration = 60. / self.bars_per_minute # in seconds
        self.beat_duration = self.bar_duration / self.beats_per_bar # in seconds

        self.quarter_note_duration = self.beat_duration / self.quarter_notes_per_beat

    def at_tempo(self, tempo):
        """returns a new TimeSignature with the same upper and lower numerals,
        but a different tempo"""
        return TimeSignature(self.beats_per_bar, self.beat_value, tempo)

    def doubled(self):
        """returns a new TimeSignature with doubled values compared to this one,
        i.e. 4/4 becomes 8/8, 3/4 becomes 6/8 etc."""
        return TimeSignature(self.beats_per_bar*2, self.beat_value*2, self.tempo)

    def halved(self):
        """as doubled, but halved"""
        return TimeSignature(self.beats_per_bar/2, self.beat_value/2, self.tempo)

    def __repr__(self):
        u, l = self.beats_per_bar, self.beat_value
        rows = [f'TimeSignature: |{u}/{l}|',
                f'Beats per minute: {self.beats_per_minute}',
                f'Beat duration: {round(self.beat_duration,3)}',
                f'Bars per minute: {round(self.bars_per_minute,1)}',
                f'Bar duration: {round(self.bar_duration,2)}']
        return '\n'.join(rows)

    def metronome(self, bars=1):
        """synthesises a sound wave of some desired number of bars,
        with major and minor beats of the desired time signature
        indicated with drum beats"""
        wave = np.zeros(int(self.bar_duration*fs))

        beat_idxs = [int(fs * self.beat_duration * b) for b in range(0,self.beats_per_bar)]

        # major beat idx is 0 by definition
        minor_beat_idxs = beat_idxs[1:]
        major_beat_size, minor_beat_size = len(major_beat_audio), len(minor_beat_audio)

        # allocate beats to sound wave:
        wave[0: major_beat_size] = major_beat_audio

        for b_start in minor_beat_idxs:
            b_end = b_start + minor_beat_size
            wave[b_start : b_end] = minor_beat_audio

        if self.beats_per_bar > 4 and self.beats_per_bar <= self.beat_value:
            # for 6/8, 8/8 time etc. we will use a medium beat sound
            # (in between major and minor beat sounds)
            # to accentuate the half bar
            half_bar_idx = self.beats_per_bar // 2
            # overwrite existing minor beat with medium beat:
            b_start = beat_idxs[half_bar_idx]
            wave[b_start : b_start + minor_beat_size] = 0

            wave[b_start: b_start + len(medium_beat_audio)] = medium_beat_audio

        metronome_waves = [wave]*bars
        return np.concatenate(metronome_waves)



    def get_pitches(self):
        """finds the pitches associated with this time signature's tempo,
        within the range of the 88-note piano keyboard"""
        return bpm_to_pitches(self.beats_per_minute)
    @property
    def pitches(self):
        return self.get_pitches()

    def get_note(self, return_cents=False, temperament=None):
        """finds the note chroma associated with this time signature's tempo,
        when upscaled to a pitch large enough to correspond to a note"""
        return bpm_to_note(self.beats_per_minute, return_cents=return_cents, temperament=temperament)
    @property
    def note(self):
        return self.get_note()


    def play(self, bars=2):
        """plays a metronome at this time signature for the specified number of bars"""
        if bars not in (0, None):
            # play as many bars as requested
            play_wave(self.metronome(bars=bars), block=True)
        else:
            # play forever
            wave = self.metronome(bars=100)  # synthesise 100 bars of metronome audio
            while True: # repeat them until keyboard interrupt
                play_wave(wave, block=True)


def bpm_to_pitches(bpm):
    """finds the pitches associated with this tempo within the range of the
    piano keyboard"""
    lowest_piano_pitch = notes.OctaveNote(1).pitch
    highest_piano_pitch = notes.OctaveNote(88).pitch
    tempo_hz = bpm / 60.
    tempo_pitches = []
    while tempo_hz < highest_piano_pitch:
        if tempo_hz > lowest_piano_pitch:
            tempo_pitches.append(tempo_hz)
        tempo_hz *= 2 # double the frequency until it's in the range we want
    return tempo_pitches

def bpm_to_note(bpm, return_cents=False, temperament=None):
    """finds the note chroma associated with this tempo when upscaled to a pitch"""
    tempo_pitches = bpm_to_pitches(bpm)
    nearest_notes = []
    offsets = []
    # compare to the first pitch; we'd get the same answer no matter which we compared to
    pitch = tempo_pitches[0]
    nearest_note_exact_value = conv.pitch_to_value(pitch, nearest=False, temperament=temperament)
    nearest_note_value = int(round(nearest_note_exact_value))
    nearest_octavenote = notes.OctaveNote(nearest_note_value)
    cents_offset = conv.cents(nearest_octavenote.pitch, pitch)
    nearest_note = nearest_octavenote.note # strip the octave as it's arbitrary
    if not return_cents:
        return nearest_note
    else:
        return nearest_note, round(cents_offset, 1)


CommonTime = FourFour   = TimeSignature(4,4)
FastTime =   EightEight = TimeSignature(8,8)
CutTime =    TwoTwo     = TimeSignature(2,2)
WaltzTime =  ThreeFour  = TimeSignature(3,4)
PolkaTime =  SixEight   = TimeSignature(6,8)
