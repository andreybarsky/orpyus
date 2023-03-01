from muse.notes import OctaveNote

###
import numpy as np
import sounddevice as sd
import matplotlib.pyplot as plt
# import playsound
# from scipy.io.wavfile import write


def show(*arrs):
    for arr in arrs:
        plt.plot(arr)
    plt.legend(range(len(arrs)))
    plt.show()

sampling_freq = 44100

def normalise(x):
    return x / np.max(x)

### create wave:
def sine_wave(freq, duration, amplitude=1):
    # freq and sampling_Freq are in hz
    # duration is in seconds
    sampling_freq = 44100 # hz
    samples = np.linspace(0, duration, int(sampling_freq*duration))
    wave = np.sin(2 * np.pi * freq * samples) * amplitude
    return wave

def exp_falloff(wave, sharpness=5, peak_at=0.05):
    """peak_at is float, in seconds"""
    start_samples = int(sampling_freq * peak_at)
    start = wave[:start_samples]
    end = wave[start_samples:]
    end_samples = len(end)
    # climbup at the very beginning:
    up_profile = np.linspace(0,sharpness, start_samples)
    exp_up = normalise(np.exp(up_profile))
    start = start * exp_up

    # falloff at the end
    down_profile = np.linspace(sharpness, 0, end_samples)
    exp_down = normalise(np.exp(down_profile))
    end = end * exp_down
    return np.concatenate([start, end], axis=0)



def chordsum(waves, *args, norm=True, fadeout=True, **kwargs):
    wave = np.sum(waves, axis=0)
    wave = exp_falloff(wave, *args, **kwargs) if fadeout else wave
    wave = normalise(wave) if norm else wave
    return wave

def arrange_melody(waves, *args, interval=0.5, fadeout=True, **kwargs):
    interval_frames = int(interval * sampling_freq)
    melody_wave = exp_falloff(waves[0], *args, **kwargs) if fadeout else np.copy(waves[0])
    for i, wave in enumerate(waves[1:]):

        start = interval_frames * (i+1)
        end = start + len(wave)
        if end > len(melody_wave):
            padding = np.zeros(end - len(melody_wave))
            melody_wave = np.concatenate([melody_wave, padding])
        melody_wave[start : end] += exp_falloff(wave, *args, **kwargs) if fadeout else wave
        melody_wave[start : end] = normalise(melody_wave[start : end])

    return melody_wave

def play_note(wave, *args, fadeout=True, **kwargs):
    wave = exp_falloff(wave, *args, **kwargs) if fadeout else wave
    play_wave(wave)

def play_chord(waves, *args, fadeout=True, **kwargs):
    wave = chordsum(waves, *args, fadeout=fadeout, **kwargs)
    play_wave(wave)

def play_melody(waves, *args, interval=0.5, fadeout=True, **kwargs):
    """interval given in seconds"""
    wave = arrange_melody(waves, *args, interval=interval, fadeout=fadeout, **kwargs)
    play_wave(wave)

# sd solution
def play_wave(wave, amplitude=1):
    sd.play(wave*amplitude, sampling_freq)

# file writing soluton:
def play_wave(wave, amplitude=0.9):
    write('output.wav', sampling_freq, wave*amplitude)
    playsound('output.wav')


c4 = sine_wave(261.63, 2)
e4 = sine_wave(329.63, 2)
g4 = sine_wave(392.0, 2)
a4 = sine_wave(440.0, 2)
cmaj = [c4, e4, g4]
am_c = [c4, e4, a4]
play_melody(am_c)
###




#
# ### jupyter solution:
# from IPython.display import Audio
# wave_audio = numpy.sin(numpy.linspace(0, 3000, 20000))
# Audio(wave_audio, rate=20000)
# ###
#


class Tone(OctaveNote):
    """a played note, with a pitch, duration (in beats), and amplitude (relative to baseline of 100)"""
    def __init__(self, note, duration=1, amplitude=100, dynamics=False):

        if isinstance(note, Note):
            # if note is an instance of Note class, assign to attribute:
            self.note = note
        elif note is None:
            # this is a rest:
            self.note = None
        else:
            # otherwise instantiate it:
            self.note = Note(note)

        self.note = note
        self.pitch = note.pitch
        self.duration = duration # in beats?
        self.amplitude = amplitude

        self.dynamics = dynamics # for fadeout?

    def play(self, tempo=60):
        duration_secs = self.duration * tempo
        raise Exception('TBI')

class Tune:
    """an ordered list of played Tones, with a tempo (in beats/min)"""
    def __init__(self, tones, tempo=60):
        self.tones = []
        self.tempo = tempo # bpm
        for tone in tones:
            assert isinstance(tone, Tone)
            self.tones.append(tone)

    def play(self):
        for tone in self.tones:
            tone.play(tempo=self.tempo)
