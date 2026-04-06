import numpy as np
from scipy.signal import butter, sosfiltfilt, resample
import librosa
import pyloudnorm
from core.job import Job


def _bandpass_rms_db(
    audio_mono: np.ndarray,
    sample_rate: int,
    low_hz: float | None,
    high_hz: float | None,
) -> float:
    nyquist = sample_rate / 2.0
    if high_hz is not None:
        high_hz = min(high_hz, nyquist * 0.99)
    if low_hz is not None:
        low_hz = max(low_hz, 1.0)

    filtered = audio_mono.copy()

    if high_hz is not None:
        sos = butter(4, high_hz, btype='low', fs=sample_rate, output='sos')
        filtered = sosfiltfilt(sos, filtered)

    if low_hz is not None:
        sos = butter(4, low_hz, btype='high', fs=sample_rate, output='sos')
        filtered = sosfiltfilt(sos, filtered)

    rms = np.sqrt(np.mean(filtered ** 2))
    return float(20 * np.log10(rms + np.finfo(np.float64).eps))


def analyze(job: Job) -> Job:
    job.status = "analyzing"

    if job.audio.ndim == 1:
        mono = job.audio.astype(np.float64)
    else:
        mono = np.mean(job.audio, axis=0).astype(np.float64)

    # rms_db
    rms = np.sqrt(np.mean(mono ** 2))
    rms_db = float(20 * np.log10(rms + np.finfo(np.float64).eps))

    # crest_factor_db
    peak_db = float(20 * np.log10(np.max(np.abs(mono)) + np.finfo(np.float64).eps))
    crest_factor_db = float(peak_db - rms_db)

    # dynamic_range_db
    if len(mono) < 2048:
        dynamic_range_db = 0.0
    else:
        frames = librosa.feature.rms(y=mono, frame_length=2048, hop_length=512)[0]
        frames_db = 20 * np.log10(frames + np.finfo(np.float64).eps)
        dynamic_range_db = float(np.percentile(frames_db, 90) - np.percentile(frames_db, 10))

    # integrated_lufs
    try:
        audio_for_lufs = mono if job.num_channels == 1 else job.audio.T
        if len(mono) < job.sample_rate * 0.4:
            integrated_lufs = -70.0
        else:
            meter = pyloudnorm.Meter(job.sample_rate)
            integrated_lufs = float(meter.integrated_loudness(audio_for_lufs))
            if not np.isfinite(integrated_lufs):
                integrated_lufs = -70.0
    except Exception:
        integrated_lufs = -70.0

    # true_peak_dbtp
    target_samples = len(mono) * 4
    upsampled = resample(mono, target_samples)
    true_peak_dbtp = float(20 * np.log10(np.max(np.abs(upsampled)) + np.finfo(np.float64).eps))

    # frequency bands
    rms_sub_db = _bandpass_rms_db(mono, job.sample_rate, low_hz=None, high_hz=80.0)
    rms_low_db = _bandpass_rms_db(mono, job.sample_rate, low_hz=80.0, high_hz=300.0)
    rms_mid_db = _bandpass_rms_db(mono, job.sample_rate, low_hz=300.0, high_hz=3000.0)
    rms_high_db = _bandpass_rms_db(mono, job.sample_rate, low_hz=3000.0, high_hz=None)

    # spectral_centroid_hz
    if np.allclose(mono, 0):
        spectral_centroid_hz = 0.0
        spectral_flatness = 0.0
    else:
        centroid = librosa.feature.spectral_centroid(y=mono, sr=job.sample_rate)
        spectral_centroid_hz = float(np.mean(centroid))

        # spectral_flatness
        flatness = librosa.feature.spectral_flatness(y=mono)
        spectral_flatness = float(np.mean(flatness))

    # stereo_width
    if job.num_channels < 2:
        stereo_width = 0.0
    else:
        L = job.audio[0]
        R = job.audio[1]
        mid = (L + R) / 2.0
        side = (L - R) / 2.0
        rms_mid = np.sqrt(np.mean(mid ** 2))
        rms_side = np.sqrt(np.mean(side ** 2))
        if rms_mid < 1e-6:
            stereo_width = 0.0
        else:
            stereo_width = float(rms_side / rms_mid)

    # low_end_mono_compatibility
    if job.num_channels < 2:
        low_end_mono_compatibility = 0.0
    else:
        L = job.audio[0]
        R = job.audio[1]
        sos = butter(4, 120.0, btype='low', fs=job.sample_rate, output='sos')
        L_lp = sosfiltfilt(sos, L)
        R_lp = sosfiltfilt(sos, R)
        mid_lp = (L_lp + R_lp) / 2.0
        side_lp = (L_lp - R_lp) / 2.0
        rms_mid_lp = np.sqrt(np.mean(mid_lp ** 2))
        rms_side_lp = np.sqrt(np.mean(side_lp ** 2))
        low_end_mono_compatibility = float(rms_side_lp / (rms_mid_lp + np.finfo(np.float64).eps))

    job.analysis = {
        "rms_db":                     rms_db,
        "crest_factor_db":            crest_factor_db,
        "dynamic_range_db":           dynamic_range_db,
        "integrated_lufs":            integrated_lufs,
        "true_peak_dbtp":             true_peak_dbtp,
        "rms_sub_db":                 rms_sub_db,
        "rms_low_db":                 rms_low_db,
        "rms_mid_db":                 rms_mid_db,
        "rms_high_db":                rms_high_db,
        "spectral_centroid_hz":       spectral_centroid_hz,
        "spectral_flatness":          spectral_flatness,
        "stereo_width":               stereo_width,
        "low_end_mono_compatibility": low_end_mono_compatibility,
    }

    job.status = "pending"
    return job
