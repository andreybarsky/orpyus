#### experimental/unfinished module
#### please do not judge the quality of my code by this file in particular

from .notes import OctaveNote
from .util import log

import threading

import math
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.pyplot import plot, show
# from matplotlib import ticker as mticker
from scipy.fft import fft, ifft
from scipy.ndimage import gaussian_filter
import sounddevice as sd

# global sampling frequency:
fs = 44100


class AmplitudeEnvelope:
    """class that can be called on sound waves to apply attack/onset/decay parameters"""
    def __init__(self, spec):
        """accepts argument 'spec', a list of of (fraction, amp) pairs,
        where 'fraction' is a float between 0 and 1, representing
            fractions of the original signature as 'keypoints',
        and 'amp' is a positive float (but usually between 0 and 1), representing
            the desired amplitude at the corresponding keypoint, relative to
            a reference value of 1 (the original signal)"""

        # if amplitudes for onset and offset are not provided in spec,
        # set them to 1 and 0 by default:
        if (len(spec) == 0) or spec[0][0] != 0:
            start_profile = (0,1) # start at reference volume
            spec = [start_profile] + spec
        if spec[-1][0] != 1:
            end_profile = (1,0) # decay to 0 by end
            spec.append(end_profile)

        self.keypoints = [pair[0] for pair in spec]
        self.amplitudes = [np.max([pair[1],0]) for pair in spec] # floor at 0
        assert self.keypoints == sorted(self.keypoints), "keypoints must be in increasing order"

    def __call__(self, wave):
        """applies this envelope to a desired 1d wave"""
        size = len(wave)
        keypoint_idxs = [int(size * frac) for frac in self.keypoints]
        amp_profile = np.ones(size)
        output_segments = []
        # loop over segments of the envelope, i.e. the edges between keypoints:
        for s in range(1, len(self.keypoints)):
            start_idx, end_idx = keypoint_idxs[s-1], keypoint_idxs[s]
            segment_size = end_idx - start_idx
            amp_start, amp_end = self.amplitudes[s-1], self.amplitudes[s]

            amp_values = np.linspace(amp_start, amp_end, segment_size)

            segment = wave[start_idx : end_idx]
            output_segments.append(segment * amp_values)
        return np.concatenate(output_segments)

LinearEnv = AmplitudeEnvelope([])
TriangleEnv = AmplitudeEnvelope([(0,0), (.5, 1), (1,0)])
HexEnv = AmplitudeEnvelope([(0, 0), (0.21, 1), (0.78,1), (1,0)])
LogEnv = AmplitudeEnvelope([(i/20, -math.log(i/20,10)/2) for i in range(1,20)])
ExpEnv = AmplitudeEnvelope([(i/20, -1.6*math.exp(((i/20)-1.1)*2)+1.18) for i in range(1,20)])


def smooth(wave, ratio=500):
    sd = len(wave) / ratio
    return gaussian_filter(wave, sd)

### pyaudio for mic input?

def show(*arrs, fix_ylim=True, fix_xlim=True, overlay=False):
    if isinstance(arrs[0], tuple):
        log(f' show detected arrs[0] as being of type: {type(arrs[0])}')
        log(f' so calling recursively on unpacked iterable of len {len(arrs[0])}, whose first type is: {type(arrs[0][0])}')
        show(*arrs[0], fix_ylim=fix_ylim, fix_xlim=fix_xlim, overlay=overlay)
    else:
        if not overlay:
            fig, axes = plt.subplots(len(arrs), 1, sharex=fix_xlim, sharey=fix_ylim)
            # xlims, ylims = [], []
            if isinstance(axes, np.ndarray):
                for arr, ax in zip(arrs, axes):
                    ax.plot(arr)

            else:
                axes.plot(arrs[0])
            fig.tight_layout()
            plt.show()

        elif overlay:
            fig, ax = plt.subplots()
            for arr in arrs:
                ax.plot(arr)
            ax.legend(range(len(arrs)))
            plt.show()

def show_fft(arr, xlim=(25,5000), note_names=True, which_notes=['C', 'E', 'G'], log_x=True, figsize=(14,8), type='pure', show=True):
    if isinstance(arr, (int, float)):
        # if input arg is a scalar, interpret a pure wave of that frequency instead
        freq = arr
        arr = synth_wave(freq, 1, type=type)

    N = len(arr)
    xf = np.linspace(0.0, 1.0/(2.0*(1/fs)), N//2)
    f = fft(arr)
    yf = 2./N * np.abs(f[:N//2])

    fig, ax = plt.subplots(figsize=figsize)
    xleft, xright = xlim
    ax.plot(xf[xleft:xright], yf[xleft:xright])

    ax.set_ylabel('Amplitude')
    # ax.set_xlim(xlim) # default 25 -> 5000 covers the piano key range from C1-C8
    # set log scale on x-axis:
    if log_x:
        ax.set_xscale('log')

    # initialise OctaveNotes so we can add their pitches to the x-axis
    tick_notes = []
    for octave in range(1,9):
        for chroma in which_notes:
            note_name = f'{chroma}{octave}'
            note = OctaveNote(note_name)
            tick_notes.append(note)

    if note_names:
        # add major tick marks at the notes specified in which_notes, at every octave
        ax.set_xticks([n.pitch for n in tick_notes])
        ax.set_xticklabels([n.name for n in tick_notes])
        ax.set_xlabel('Note')
    else:
        # approx. octave marks:
        pitch_marks = [2**b for b in range(3,12)]
        ax.set_xticks(pitch_marks)
        ax.set_xticklabels(pitch_marks)
        # ax.xaxis.set_major_locator(mticker.LogLocator(base=2, numticks))
        ax.set_xlabel('Frequency (Hz)')

    # add minor tick marks for every note, but don't label them:
    ax.set_xticks([OctaveNote(value=v).pitch for v in range(1,89)], minor=True)
    ax.set_xticklabels([], minor=True)

    if show:
        plt.show()

def normalise(x, ceil=None):
    if ceil is None:
        ceil = np.max(x)
    return x / ceil

### create pure wave:
def sine_wave(freq, duration, correct=True, amplitude=1):
    # duration is in seconds
    samples = np.linspace(0, duration, int(fs*duration))
    wave = np.sin(2 * np.pi * freq * samples) * amplitude
    # pure tones at low freqs sound quieter, so we raise the amplitude to correct:
    if correct:
        wave = amp_correct(wave, freq)
    return wave

# def harmonic_wave(freq, duration, num_harmonics=8, norm_each=True, correct=False, amplitude=1):
#     """create a pure sine wave with overtones according to harmonic series"""
#     ratios = range(1, num_harmonics+1)
#     overtone_freqs = [freq*r for r in ratios]
#     waves = [sine_wave(freq, duration, amplitude=amplitude) for freq in overtone_freqs]
#     if norm_each:
#         waves = [w/r for w,r in zip(waves, ratios)]
#     wave_sum = normalise(np.sum(waves, axis=0))
#     if correct:
#         # avg_freq = np.mean(overtone_freqs)
#         wave_sum = amp_correct(wave_sum, freq)
#     return wave_sum

### create white noise:
def white_noise(duration, amplitude=1):
    wave = np.random.uniform(-amplitude, amplitude, int(fs*duration))
    return wave

# pure exponential falloff function: (timbre over pure sine wave sounds harp-like, or like an electric piano)
def exp_falloff(wave, sharpness=5, peak_at=0.05):
    """peak_at is float, in seconds"""
    start_samples = int(fs * peak_at)
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
    start_samples = int(fs * start_at)
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

    delay_frames = int(delay * fs)
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
    sd.play(wave*amplitude, fs, blocking=block)

### longer form solution
def play_wave2(wave, amplitude=1):
    event = threading.Event()
    current_frame = 0
    # try:
    data = np.reshape(wave * amplitude, (-1,1))

    duration_secs = int(len(wave) // 44.1)

    def callback(outdata, frames, time, status):
        # from pdb import set_trace; set_trace(context=30)
        nonlocal current_frame
        if status:
            print(status)
        chunksize = min(len(data) - current_frame, frames)
        outdata[:chunksize] = data[current_frame:current_frame + chunksize]
        if chunksize < frames:
            outdata[chunksize:] = 0
            raise sd.CallbackStop()
        current_frame += chunksize

    stream = sd.OutputStream(samplerate = fs,
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

    log(f'Desired freq is: {freq:.1f}')
    freq = int(round(freq))
    log(f'Rounded to: {freq}')

    num_samples = int(duration * wave_table_reso)
    table_len = int(wave_table_reso // freq)
    log(f'Desired note duration of {num_samples} ({duration}*{wave_table_reso}) divides by {freq}*4 to get table length of: {table_len}')
    wave_table = (np.random.randint(0, 2, table_len)*2 -1).astype(float)
    n_iter = num_samples // table_len

    # # calculate linear multiplication terms for exponential decay:
    # a = np.ones(n_iter) * decay
    # b = np.arange(n_iter)
    # decay_schedule = pow(a,b)

    pointer = 0
    iter_num = 0

    samples = np.zeros(num_samples)
    prev_val = samples[0]

    for i in range(1, num_samples):
        # print(f'{step} Averaging {wave_table[pointer]} and {prev_val} to get {(wave_table[pointer] + prev_val) * 0.5}')
        wave_table[pointer] = ((wave_table[pointer] + samples[i-1]) * 0.5)
        samples[i] = (wave_table[pointer]) # * decay_schedule[iter_num]
        if pointer+1 >= table_len:
            iter_num += 1

        pointer = (pointer + 1) % table_len
        # step += 1
    log(f'Actual frequency of output is: {detect_freq(samples):.1f}')

    return samples

def sine_wave_table(table_len):
    t = np.linspace(0, 2*np.pi, table_len)
    wave_table = np.sin(t)
    return wave_table

def discrete_wave_table(table_len):
    wave_table = (np.random.randint(0, 2, table_len)*2 -1).astype(float)
    return wave_table

def unif_wave_table(table_len):
    wave_table = (np.random.rand(table_len)*2 -1).astype(float)
    return wave_table

def fast_karplus_strong(freq, duration, decay=0.99, wave_table_reso=44100, func=unif_wave_table):
    log(f'Desired freq is: {freq:.1f}')
    freq = int(round(freq))
    log(f'Rounded to: {freq}')

    num_samples = duration * wave_table_reso
    table_len = int(wave_table_reso // freq)
    log(f'Desired note duration of {num_samples} ({duration}*{wave_table_reso}) to get table length of: {table_len}')

    wave_table = func(table_len)

    n_iter = int(num_samples // table_len)

    # calculate linear multiplication terms for exponential decay:
    a = np.ones((1,n_iter)) * decay
    b = np.arange(n_iter)
    a_vec = pow(a,b)

    # matrix of successively decaying linear multiplication terms:
    alpha_mat = np.eye(n_iter, table_len)
    for i in range(table_len):
        alpha_mat[:,i] = a_vec

    # tile wave table across as many rows as decay iterations:
    x_mat = np.tile(wave_table,(n_iter,1))
    y_mat = alpha_mat * x_mat

    y_arr = y_mat.reshape(-1)
    return y_arr

def play_karplus(note, duration=2, falloff=True, fast=False, **kwargs):
    if isinstance(note, str):
        freq = OctaveNote(note).pitch
    elif isinstance(note, OctaveNote):
        freq = note.pitch
    elif isinstance(note, (int, float)):
        freq = float(note)

    if fast:
        if falloff:
            samples = fast_karplus_strong(freq, duration=duration, decay=0.9925)
            samples = exp_falloff(samples, peak_at=0.01)
        else:
            # don't use explicit falloff postprocessing, just the natural decay term:
            samples = fast_karplus_strong(freq, duration=duration, decay=0.9825)
    else:
        # slow karplus strong algorithm naturally decays, does not need additional expo term
        samples = karplus_strong(freq, duration=duration)
        if falloff:
            samples = lin_falloff(samples)
    play_wave(samples)

wave_cache = {}

def synth_wave(freq, duration, type='KS', falloff=True, cache=True):
    """type must be one of:
    'sine': sine wave synthesis
    'KS': (slow) karplus-strong algorithm
    'fast': fast karplus-strong approximation"""
    params = (freq, duration, type, falloff)
    if cache:
        if params in wave_cache:
            return wave_cache[params]

    if type == 'pure':
        wave = sine_wave(freq, duration, correct=True)
        if falloff:
            wave = exp_falloff(wave)
    elif type == 'KS':
        wave = karplus_strong(freq, duration)
        if falloff:
            wave = lin_falloff(wave)
    elif type == 'fast':
        wave = fast_karplus_strong(freq, duration, decay=0.99)
        if falloff:
            wave = exp_falloff(wave, peak_at=0.01)
    else:
        raise Exception('type arg supplied to synth_wave must be one of: sine, KS, fast')
    if cache:
        if params not in wave_cache:
            wave_cache[params] = wave
    return wave

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
    """detects the frequency of a pure sinusoid signal
    by counting peaks in the waveform. probably doesn't work meaningfully
    well for composite signals"""
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

# def rms(wave):
#     """returns root mean squared deviation (i.e. std dev)
#     of a sound wave or other 1d array"""
#     dev = wave - np.mean(wave)
#     sq_dev = dev ** 2
#     mean_sq_dev = np.mean(sq_dev)
#     rms = mean_sq_dev ** 0.5
#     return rms
#
# def decibels(wave, ref_pressure=20):
#     """loudness of a supplied sound wave, in decibels"""
#     return 20 * np.log(rms(wave) / ref_pressure)
#
#
# def equal_loudness_contour(freq):
#     Lp = (10/af)* np.log(Af)
