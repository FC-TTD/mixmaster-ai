import numpy as np
import pyloudnorm
import soundfile as sf
from scipy.signal import sosfilt, butter, resample, iirfilter
from pedalboard import Pedalboard, Compressor, Gain, Limiter
from core.job import Job
from core.schemas import (
    DSPDecisions, EQSettings, EQBand,
    CompressorSettings, SaturatorSettings,
    StereoImageSettings, LimiterSettings,
)


def _design_peak_eq(
    freq: float, gain_db: float, q: float, sample_rate: int
) -> np.ndarray:
    import math

    q = max(q, 0.1)
    freq = float(np.clip(freq, 20.0, sample_rate * 0.49))

    A     = 10 ** (gain_db / 40.0)
    w0    = 2 * math.pi * freq / sample_rate
    alpha = math.sin(w0) / (2.0 * q)

    b0 =  1 + alpha * A
    b1 = -2 * math.cos(w0)
    b2 =  1 - alpha * A
    a0 =  1 + alpha / A
    a1 = -2 * math.cos(w0)
    a2 =  1 - alpha / A

    sos = np.array([[b0/a0, b1/a0, b2/a0, 1.0, a1/a0, a2/a0]])
    return sos  # shape (1, 6)


def _apply_eq(
    audio: np.ndarray, sample_rate: int, eq: EQSettings
) -> np.ndarray:
    if not eq.bands:
        return audio

    for band in eq.bands:
        freq = min(band.frequency, sample_rate / 2 * 0.99)

        if band.filter_type == "peak":
            sos = _design_peak_eq(freq, band.gain_db, band.q, sample_rate)
            for ch in range(audio.shape[0]):
                audio[ch] = sosfilt(sos, audio[ch])

        elif band.filter_type == "high_pass":
            sos = butter(4, freq, btype='high', fs=sample_rate, output='sos')
            for ch in range(audio.shape[0]):
                audio[ch] = sosfilt(sos, audio[ch])

        elif band.filter_type == "low_pass":
            sos = butter(4, freq, btype='low', fs=sample_rate, output='sos')
            for ch in range(audio.shape[0]):
                audio[ch] = sosfilt(sos, audio[ch])

        elif band.filter_type == "low_shelf":
            sos = butter(2, freq, btype='low', fs=sample_rate, output='sos')
            gain_linear = 10 ** (band.gain_db / 20.0)
            for ch in range(audio.shape[0]):
                filtered = sosfilt(sos, audio[ch])
                audio[ch] = audio[ch] + filtered * (gain_linear - 1.0)

        elif band.filter_type == "high_shelf":
            sos = butter(2, freq, btype='high', fs=sample_rate, output='sos')
            gain_linear = 10 ** (band.gain_db / 20.0)
            for ch in range(audio.shape[0]):
                filtered = sosfilt(sos, audio[ch])
                audio[ch] = audio[ch] + filtered * (gain_linear - 1.0)

    return audio


def _apply_compressor(
    audio: np.ndarray, sample_rate: int, comp: CompressorSettings
) -> np.ndarray:
    board = Pedalboard([
        Compressor(
            threshold_db=comp.threshold_db,
            ratio=comp.ratio,
            attack_ms=comp.attack_ms,
            release_ms=comp.release_ms,
        ),
        Gain(gain_db=comp.makeup_gain_db),
    ])
    audio = np.clip(audio, -1.0, 1.0)
    audio_f32 = audio.astype(np.float32)
    result_f32 = board(audio_f32, sample_rate)
    return result_f32.astype(np.float64)


def _apply_saturator(
    audio: np.ndarray, sat: SaturatorSettings
) -> np.ndarray:
    drive_linear = 10 ** (sat.drive_db / 20.0)

    if sat.mode == "tape":
        saturated = np.tanh(audio * drive_linear)
    elif sat.mode == "tube":
        saturated = np.where(
            audio >= 0,
            np.tanh(audio * drive_linear),
            np.tanh(audio * drive_linear * 0.7),
        )
    elif sat.mode == "clip":
        saturated = np.clip(audio * drive_linear, -1.0, 1.0)

    return audio * (1.0 - sat.mix) + saturated * sat.mix


def _apply_ms_image(
    audio: np.ndarray, sample_rate: int, image: StereoImageSettings
) -> np.ndarray:
    if audio.shape[0] == 1:
        return audio

    scale = 0.7071067811865476  # 1/sqrt(2)
    mid  = (audio[0] + audio[1]) * scale
    side = (audio[0] - audio[1]) * scale

    sos     = butter(4, image.mono_low_hz, btype='low', fs=sample_rate, output='sos')
    side_lf = sosfilt(sos, side)
    side    = side - side_lf  # high-pass the side signal

    width = float(np.clip(image.width, 0.0, 2.0))
    side = side * width

    audio[0] = (mid + side) * scale
    audio[1] = (mid - side) * scale
    return audio


def _apply_limiter(
    audio: np.ndarray, sample_rate: int, lim: LimiterSettings
) -> np.ndarray:
    board = Pedalboard([
        Limiter(
            threshold_db=lim.ceiling_dbtp,
            release_ms=lim.release_ms,
        )
    ])
    audio = np.clip(audio, -1.0, 1.0)
    audio_f32 = audio.astype(np.float32)
    return board(audio_f32, sample_rate).astype(np.float64)


def process(job: Job) -> Job:
    if job.dsp_decisions is None:
        raise ValueError(
            "job.dsp_decisions must be populated before calling process(). "
            "Run agent.decide(job) first."
        )

    audio = job.audio.copy().astype(np.float64)

    audio = _apply_eq(audio, job.sample_rate, job.dsp_decisions.corrective_eq)
    audio = _apply_compressor(audio, job.sample_rate, job.dsp_decisions.compressor)
    audio = _apply_eq(audio, job.sample_rate, job.dsp_decisions.tonal_eq)
    audio = _apply_saturator(audio, job.dsp_decisions.saturator)
    audio = _apply_ms_image(audio, job.sample_rate, job.dsp_decisions.stereo_image)
    # Gain safety: prevent limiter overload
    peak = np.max(np.abs(audio))
    if peak > 0.9:
        audio = audio * (0.9 / peak)
    audio = _apply_limiter(audio, job.sample_rate, job.dsp_decisions.limiter)

    meter = pyloudnorm.Meter(job.sample_rate)
    if job.num_channels == 1:
        audio_for_lufs = audio[0]
    else:
        audio_for_lufs = audio.T
    try:
        lufs = float(meter.integrated_loudness(audio_for_lufs))
        if not np.isfinite(lufs):
            lufs = -70.0
    except Exception:
        lufs = -70.0
    job.loudness_lufs = lufs

    mono_mix = np.mean(audio, axis=0)
    upsampled = resample(mono_mix, len(mono_mix) * 4)
    job.true_peak_dbtp = float(
        20 * np.log10(np.max(np.abs(upsampled)) + np.finfo(np.float64).eps)
    )

    job.processed_audio = audio.astype(np.float32)
    job.status = "done"
    return job
