from muse.notes import OctaveNote

###
# import sys, pdb
import numpy as np
import sounddevice as sd
import matplotlib.pyplot as plt
from matplotlib import ticker as mticker
import threading
from scipy.fft import fft, ifft
from muse.util import log, test

# from scipy.io.wavfile import write


sampling_freq = 44100
fs = sampling_freq


def show(*arrs, subplots=False):
    if not subplots:
        fig, ax = plt.subplots()
        for arr in arrs:
            ax.plot(arr)
        ax.legend(range(len(arrs)))
        plt.show()
    elif subplots:
        fig, axes = plt.subplots(len(arrs), 1)
        for arr, ax in zip(arrs, axes):
            ax.plot(arr)
        plt.show()


def show_fft(arr, xlim=(25,5000), note_names=True, which_notes=['C', 'E', 'G'], log_x=True, figsize=(14,8)):
    N = len(arr)
    xf = np.linspace(0.0, 1.0/(2.0*(1/fs)), N//2)
    f = fft(arr)
    yf = 2./N * np.abs(f[:N//2])

    fig, ax = plt.subplots(figsize=figsize)
    ax.plot(xf, yf)

    if log_x:
        ax.set_xscale('log')

    ax.set_ylabel('Amplitude')
    ax.set_xlim(xlim) # default 25,5000 covers the piano key range from C1-C8
    # ymin, ymax = ax.get_ylim() # we'll use this to place annotations if we need them
    # anno_y = ymax * -0.04

    # initialise OctaveNotes and add their pitches to the x-axis
    tick_notes = []
    for octave in range(1,8):
        for chroma in which_notes:
            note_name = f'{chroma}{octave}'
            note = OctaveNote(note_name)
            # ax.annotate(note_name, (note.pitch, anno_y))
            tick_notes.append(note)

    if note_names:
        ax.set_xticks([n.pitch for n in tick_notes])
        ax.set_xticklabels([n.name for n in tick_notes])
        ax.set_xlabel('Note')
    else:
        # octave_notes = [tick_notes[i] for i in range(0, len(tick_notes), len(which_notes))]
        # approx. octave marks:
        pitch_marks = [2**b for b in range(3,12)]
        ax.set_xticks(pitch_marks)
        ax.set_xticklabels(pitch_marks)
        # ax.xaxis.set_major_locator(mticker.LogLocator(base=2, numticks))
        # ax.xaxis.set_major_formatter(mticker.ScalarFormatter())
        # ax.xaxis.set_minor_locator(mticker.MultipleLocator(100))
        ax.set_xlabel('Frequency (Hz)')

    # add minor tick marks for every note, but don't label them:
    ax.set_xticks([OctaveNote(value=v).pitch for v in range(1,89)], minor=True)
    ax.set_xticklabels([], minor=True)

    plt.show()

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

# pure exponential falloff function: (timbre sounds harp-like, or like an electric piano)
def exp_falloff(wave, sharpness=5, peak_at=0.05):
    """peak_at is float, in seconds"""
    start_samples = int(sampling_freq * peak_at)
    start = np.copy(wave[:start_samples])
    end = np.copy(wave[start_samples:])
    end_samples = len(end)
    # climbup at the very beginning:
    up_profile = np.linspace(0,sharpness, start_samples)
    exp_up = normalise(np.exp(up_profile))
    start *= exp_up

    # falloff at the end
    down_profile = np.linspace(sharpness, 0, end_samples)
    exp_down = normalise(np.exp(down_profile))
    end *= exp_down
    return np.concatenate([start, end], axis=0)

def lin_falloff(wave, start_at=0.0):
    start_samples = int(sampling_freq * start_at)
    end = np.copy(wave[start_samples:])
    end_samples = len(end)

    # falloff at the end
    down_profile = np.linspace(1, 0, end_samples)
    end *= down_profile
    return np.concatenate([wave[:start_samples], end], axis=0)

def amp_correct(wave, pitch=None):
    ### correct amplitude of a wave wrt its pitch.
    # if pitch is not given, try to detect it automatically
    if pitch is None:
        pitch = detect_freq(wave)

    # correct amplitude wrt freq, with reference to c4 as ideal volume:
    amp_factor = 261.32 / pitch # 261.63 is c4 pitch
    wave *= amp_factor
    return wave

def arrange_chord(waves, *args, norm=False, falloff=True, **kwargs):
    start_max = np.max([np.max(w) for w in waves])
    wave = np.sum(waves, axis=0)
    wave = lin_falloff(wave, *args, **kwargs) if falloff else wave
    if norm:
        wave = wave / start_max
    return wave

def arrange_melody(waves, *args, delay=0.5, norm=False, falloff=True, **kwargs):
    start_max = np.max([np.max(w) for w in waves])

    delay_frames = int(delay * sampling_freq)
    melody_wave = lin_falloff(waves[0]) if falloff else np.copy(waves[0])
    for i, wave in enumerate(waves[1:]):

        start = delay_frames * (i+1)
        end = start + len(wave)
        if end > len(melody_wave):
            padding = np.zeros(end - len(melody_wave))
            melody_wave = np.concatenate([melody_wave, padding])
        melody_wave[start : end] += lin_falloff(wave) if falloff else wave
        # if norm:
        #     melody_wave[start : end] = normalise(melody_wave[start : end])
    if norm:
        melody_wave = melody_wave / start_max
    return melody_wave

def play_note(wave, *args, falloff=True, **kwargs):
    wave = lin_falloff(wave, *args, **kwargs) if falloff else wave
    play_wave(wave)

def play_chord(waves, *args, falloff=True, **kwargs):
    wave = arrange_chord(waves, *args, falloff=falloff, **kwargs)
    play_wave(wave)

def play_melody(waves, *args, delay=0.5, falloff=True, **kwargs):
    """interval given in seconds"""
    wave = arrange_melody(waves, *args, delay=delay, falloff=falloff, **kwargs)
    play_wave(wave)

### sd solution
def play_wave(wave, amplitude=1, block=False):
    sd.play(wave*amplitude, sampling_freq, blocking=block)

### longer form solution
def play_wave2(wave, amplitude=1):
    event = threading.Event()
    current_frame = 0
    # try:
    data = np.reshape(wave * amplitude, (-1,1))

    duration_secs = int(len(wave) // 44.1)

    def callback(outdata, frames, time, status):
        # import pdb; pdb.set_trace()
        nonlocal current_frame
        if status:
            print(status)
        chunksize = min(len(data) - current_frame, frames)
        outdata[:chunksize] = data[current_frame:current_frame + chunksize]
        if chunksize < frames:
            outdata[chunksize:] = 0
            raise sd.CallbackStop()
        current_frame += chunksize

    stream = sd.OutputStream(samplerate = sampling_freq,
                             device = sd.default.device[1],
                             channels = data.shape[1],
                             callback = callback,
                             finished_callback = event.set)
    with stream:
        # sd.sleep(duration_secs)
        event.wait()  # wait until playback is finished
    # except:
    #     print('Try failed')



def karplus_strong(freq, duration, wave_table_reso=44100):
    """synthesises sound sample of a desired frequency and duration
    according to Karplus-Strong algorithm for guitar-pluck timbre"""

    freq = int(freq)
    log(f'Desired freq is: {freq:.1f}')

    num_samples = duration * wave_table_reso
    table_len = int(wave_table_reso // freq) # i don't know why it's *4 but it gets the correct frequency
    log(f'Desired note duration of {num_samples} ({duration}*{wave_table_reso}) divides by {freq}*4 to get table length of: {table_len}')
    wave_table = (np.random.randint(0, 2, table_len)*2 -1).astype(float)

    samples = np.zeros(num_samples)
    pointer = 0
    # step = 0
    # num_loops = 0
    prev_val = samples[-1]
    for i in range(num_samples):
                # print(f'{step} Averaging {wave_table[pointer]} and {prev_val} to get {(wave_table[pointer] + prev_val) * 0.5}')
        wave_table[pointer] = (wave_table[pointer] + samples[i-1]) * 0.5
        samples[i] = (wave_table[pointer])
        # if pointer+1 >= table_len:
        #     num_loops += 1
        pointer = (pointer + 1) % table_len
        # step += 1
    log(f'Actual frequency of output is: {detect_freq(samples):.1f}')
    return samples

def play_karplus(note, duration=2, falloff = False):
    if isinstance(note, str):
        freq = OctaveNote(note).pitch
    elif isinstance(note, OctaveNote):
        freq = note.pitch
    elif isinstance(note, (int, float)):
        freq = float(note)

    samples = karplus_strong(freq, duration=duration)
    if falloff:
        samples = lin_falloff(samples)
    play_wave(samples)


def find_peaks(arr, ret=False):
    num_peaks = 0
    peak_idxs = []
    for i in range(1, len(arr)-1):
        if arr[i-1] < arr[i] > arr[i+1]:
            num_peaks += 1
            peak_idxs.append(i)
    if ret:
        return num_peaks, peak_idxs
    else:
        print(f'{num_peaks} peaks, located at:', ', '.join([str(p) for p in peak_idxs]))

def detect_pure_freq(arr):
    """detects the frequency of a pure sinusoid signal.
    not sure what it does for non-pure signals."""
    num_peaks, peak_idxs = find_peaks(arr, ret=True)
    sample_duration = len(arr) / fs # in seconds
    freq = num_peaks / sample_duration
    return freq

def detect_freq(arr, note=False):
    """uses fft to detect highest frequency in a composite signal.
    if note=True, returns the note name instead"""
    N = len(arr)
    xf = np.linspace(0.0, 1.0/(2.0*(1/fs)), N//2)
    f = fft(arr)
    yf = 2./N * np.abs(f[:N//2])

    # skip zero-index to avoid DC signals
    max_power = np.argmax(yf[1:]+1)
    freq = xf[max_power]
    if not note:
        return round(freq,2)
    else:
        return OctaveNote(pitch=freq).name


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

        self.dynamics = dynamics # for falloff?

    def play(self, tempo=60):
        duration_secs = self.duration * tempo
        raise Exception('TBI')

class Tune:
    """an ordered list of played Tones, or NoteLists of Tones (chords), with a tempo (in beats/min)"""
    def __init__(self, tones, tempo=60):
        self.tones = []
        self.tempo = tempo # bpm
        for tone in tones:
            assert isinstance(tone, Tone)
            self.tones.append(tone)

    def play(self):
        for tone in self.tones:
            tone.play(tempo=self.tempo)




if __name__ == '__main__':
    # c4 = sine_wave(261.63, 2)
    # e4 = sine_wave(329.63, 2)
    # g4 = sine_wave(392.0, 2)
    # a4 = sine_wave(440.0, 2)
    # cmaj = [c4, e4, g4]
    # am_c = [c4, e4, a4]
    from muse.chords import Chord
    cmaj = Chord('C')
    am_c = Chord('Am/C')
    am_c.arpeggio(octave=3)
    ###
    #
    pass
