"""Measurements that reflect the two inputs to the actual mixing path."""
from math import gcd

import numpy as np
from scipy.signal import butter, resample_poly, sosfilt

from core.job import Job


def align_instrumental(instrumental: Job, sample_rate: int) -> Job:
    """The mixer uses one sample rate; convert the beat before blending."""
    if instrumental.sample_rate == sample_rate:
        return instrumental
    common = gcd(instrumental.sample_rate, sample_rate)
    instrumental.audio = resample_poly(
        instrumental.audio,
        sample_rate // common,
        instrumental.sample_rate // common,
        axis=1,
    ).astype(np.float32)
    instrumental.sample_rate = sample_rate
    instrumental.duration_seconds = instrumental.audio.shape[1] / sample_rate
    return instrumental


def _stem_levels(audio: np.ndarray, sample_rate: int) -> dict[str, float]:
    data = audio.astype(np.float64)
    peak = float(np.max(np.abs(data)))
    raw_rms = float(np.sqrt(np.mean(data * data)))
    mono = np.mean(data, axis=0)
    mid_filter = butter(4, (300, 3000), btype="bandpass", fs=sample_rate, output="sos")
    mid = sosfilt(mid_filter, mono)
    mid_rms = float(np.sqrt(np.mean(mid * mid)))
    eps = np.finfo(np.float64).tiny
    peak_db = 20 * np.log10(max(peak, eps))
    return {
        "raw_peak_dbfs": float(peak_db),
        "raw_rms_dbfs": float(20 * np.log10(max(raw_rms, eps))),
        "post_peak_normalization_rms_dbfs": float(20 * np.log10(max(raw_rms / max(peak, eps), eps))),
        "post_peak_normalization_mid_rms_dbfs": float(20 * np.log10(max(mid_rms / max(peak, eps), eps))),
    }


def mix_input_features(vocal: Job, instrumental: Job) -> dict[str, dict[str, float] | float]:
    if vocal.sample_rate != instrumental.sample_rate:
        raise ValueError("人声与伴奏采样率必须先对齐，才能比较并混合。")
    vocal_levels = _stem_levels(vocal.audio, vocal.sample_rate)
    instrumental_levels = _stem_levels(instrumental.audio, instrumental.sample_rate)
    return {
        "vocal": vocal_levels,
        "instrumental": instrumental_levels,
        "vocal_minus_instrumental_normalized_rms_db": (
            vocal_levels["post_peak_normalization_rms_dbfs"]
            - instrumental_levels["post_peak_normalization_rms_dbfs"]
        ),
        "vocal_minus_instrumental_normalized_mid_rms_db": (
            vocal_levels["post_peak_normalization_mid_rms_dbfs"]
            - instrumental_levels["post_peak_normalization_mid_rms_dbfs"]
        ),
    }
