"""
core/mixer.py — Mixing DSP chain.
Runs BEFORE processor.py (mastering).
Takes vocal + instrumental arrays, returns a single blended stereo mix.
"""
import numpy as np
from scipy.signal import lfilter
from pedalboard import Pedalboard, Compressor, Gain, Reverb, NoiseGate

from core.processor import _apply_eq
from core.schemas import (
    MixDecisions,
    NoiseGateSettings,
    TransientShaperSettings,
    EQSettings,
    ChannelCompSettings,
    ReverbSettings,
    DelaySettings,
    MixSettings,
)


def _apply_noise_gate(
    vocal: np.ndarray, sample_rate: int, settings: NoiseGateSettings
) -> np.ndarray:
    """Kill room noise between phrases. hold_ms is not supported by pedalboard; ignored."""
    vocal = vocal.astype(np.float64)
    if np.max(np.abs(vocal)) < 1e-6:
        return vocal.astype(np.float32)

    board = Pedalboard([
        NoiseGate(
            threshold_db=settings.threshold_db,
            attack_ms=settings.attack_ms,
            release_ms=settings.release_ms,
        )
    ])
    vocal_f32 = np.clip(vocal, -1.0, 1.0).astype(np.float32)
    return board(vocal_f32, sample_rate).astype(np.float32)


def _apply_transient_shaper(
    vocal: np.ndarray, sample_rate: int, settings: TransientShaperSettings
) -> np.ndarray:
    """Boost attack transients and optionally cut sustain via dual-envelope detection."""
    vocal = vocal.astype(np.float64)
    if np.max(np.abs(vocal)) < 1e-6:
        return vocal.astype(np.float32)

    fast_samples = max(int(0.001 * sample_rate), 1)   # 1 ms fast envelope
    slow_samples = max(int(0.010 * sample_rate), 1)   # 10 ms slow envelope

    alpha_fast = 1.0 - np.exp(-1.0 / fast_samples)
    alpha_slow = 1.0 - np.exp(-1.0 / slow_samples)

    boost_linear = 10.0 ** (settings.attack_boost_db / 20.0)
    cut_linear = 10.0 ** (-settings.sustain_cut_db / 20.0)

    result = np.copy(vocal)
    for ch in range(vocal.shape[0]):
        signal = vocal[ch]
        abs_sig = np.abs(signal)

        fast_env = lfilter([alpha_fast], [1.0, -(1.0 - alpha_fast)], abs_sig)
        slow_env = lfilter([alpha_slow], [1.0, -(1.0 - alpha_slow)], abs_sig)

        diff = fast_env - slow_env
        max_diff = np.max(np.abs(diff))
        diff_norm = diff / max_diff if max_diff > 1e-6 else np.zeros_like(diff)

        # Positive diff = attack phase → boost; negative = sustain → cut
        gain = np.where(
            diff_norm >= 0,
            1.0 + (boost_linear - 1.0) * diff_norm,
            1.0 + (cut_linear - 1.0) * (-diff_norm),
        )
        processed = np.clip(signal * gain, -1.0, 1.0)
        result[ch] = np.clip(
            signal * (1.0 - settings.mix) + processed * settings.mix, -1.0, 1.0
        )

    return result.astype(np.float32)


def _apply_channel_eq(
    vocal: np.ndarray, sample_rate: int, settings: EQSettings
) -> np.ndarray:
    """Carve vocal frequency space using the same EQ engine as processor.py."""
    vocal_f64 = vocal.astype(np.float64)
    if np.max(np.abs(vocal_f64)) < 1e-6:
        return vocal_f64.astype(np.float32)
    result = _apply_eq(vocal_f64.copy(), sample_rate, settings)
    return np.clip(result, -1.0, 1.0).astype(np.float32)


def _apply_channel_compression(
    vocal: np.ndarray, sample_rate: int, settings: ChannelCompSettings
) -> np.ndarray:
    """Tame vocal dynamics before blending."""
    vocal = vocal.astype(np.float64)
    if np.max(np.abs(vocal)) < 1e-6:
        return vocal.astype(np.float32)

    board = Pedalboard([
        Compressor(
            threshold_db=settings.threshold_db,
            ratio=settings.ratio,
            attack_ms=settings.attack_ms,
            release_ms=settings.release_ms,
        ),
        Gain(gain_db=settings.makeup_gain_db),
    ])
    vocal_f32 = np.clip(vocal, -1.0, 1.0).astype(np.float32)
    result = board(vocal_f32, sample_rate).astype(np.float64)
    return np.clip(result, -1.0, 1.0).astype(np.float32)


def _apply_reverb(
    vocal: np.ndarray, sample_rate: int, settings: ReverbSettings
) -> np.ndarray:
    """
    Add space and depth. pre_delay_ms is applied by shifting the reverb input
    forward in time so the dry signal reaches the listener first.
    """
    vocal = vocal.astype(np.float64)
    if np.max(np.abs(vocal)) < 1e-6:
        return vocal.astype(np.float32)

    pre_delay_samples = int(settings.pre_delay_ms * sample_rate / 1000.0)

    if pre_delay_samples > 0:
        pad = np.zeros((vocal.shape[0], pre_delay_samples), dtype=np.float64)
        reverb_input = np.concatenate([pad, vocal], axis=1)[:, : vocal.shape[1]]
    else:
        reverb_input = vocal

    board = Pedalboard([
        Reverb(
            room_size=settings.room_size,
            damping=settings.damping,
            wet_level=1.0,   # 100% wet; dry handled below for correct pre-delay
            dry_level=0.0,
            width=1.0,
        )
    ])
    reverb_input_f32 = np.clip(reverb_input, -1.0, 1.0).astype(np.float32)
    wet_f32 = board(reverb_input_f32, sample_rate)

    # Align shape to input (guard against plugin sample-count drift)
    n_in = vocal.shape[1]
    n_out = wet_f32.shape[1]
    if n_out < n_in:
        wet_f32 = np.pad(wet_f32, ((0, 0), (0, n_in - n_out)))
    else:
        wet_f32 = wet_f32[:, :n_in]

    wet_f64 = np.clip(wet_f32, -1.0, 1.0).astype(np.float64)
    result = vocal * (1.0 - settings.wet_mix) + wet_f64 * settings.wet_mix
    return np.clip(result, -1.0, 1.0).astype(np.float32)


def _apply_delay(
    vocal: np.ndarray, sample_rate: int, settings: DelaySettings
) -> np.ndarray:
    """Echo effect with feedback via a recursive numpy delay line."""
    if not settings.enabled or settings.delay_ms <= 0.0 or settings.wet_mix <= 0.0:
        return vocal.astype(np.float32)

    vocal = vocal.astype(np.float64)
    if np.max(np.abs(vocal)) < 1e-6:
        return vocal.astype(np.float32)

    delay_samples = int(settings.delay_ms * sample_rate / 1000.0)
    if delay_samples == 0:
        return vocal.astype(np.float32)

    channels, n_samples = vocal.shape
    result = np.copy(vocal)

    for ch in range(channels):
        signal = vocal[ch]
        wet = np.zeros(n_samples, dtype=np.float64)
        for i in range(n_samples):
            delayed_input = signal[i - delay_samples] if i >= delay_samples else 0.0
            delayed_wet = wet[i - delay_samples] if i >= delay_samples else 0.0
            wet[i] = delayed_input + settings.feedback * delayed_wet
        result[ch] = signal * (1.0 - settings.wet_mix) + wet * settings.wet_mix

    return np.clip(result, -1.0, 1.0).astype(np.float32)


def _apply_panning(audio: np.ndarray, pan: float) -> np.ndarray:
    """
    Place audio in the stereo field using linear panning.
    Mono input is duplicated to stereo before panning.
    Always returns shape (2, samples).
    pan: -1.0 = full left, 0.0 = center, 1.0 = full right.
    """
    pan = float(np.clip(pan, -1.0, 1.0))
    audio = audio.astype(np.float64)

    if audio.shape[0] == 1:
        audio = np.stack([audio[0], audio[0]])

    if pan <= 0.0:
        left_gain, right_gain = 1.0, 1.0 + pan   # right attenuates as pan goes left
    else:
        left_gain, right_gain = 1.0 - pan, 1.0   # left attenuates as pan goes right

    result = np.stack([audio[0] * left_gain, audio[1] * right_gain])
    return np.clip(result, -1.0, 1.0).astype(np.float32)


def mix_tracks(
    vocal: np.ndarray,
    instrumental: np.ndarray,
    sample_rate: int,
    decisions: MixDecisions,
) -> np.ndarray:
    """
    Apply the full mixing chain to vocal, then blend with instrumental.
    Returns a stereo mix (2, samples) ready for mastering via processor.py.
    """
    vocal = vocal.astype(np.float64)
    instrumental = instrumental.astype(np.float64)

    # Ensure both tracks are stereo
    if vocal.shape[0] == 1:
        vocal = np.stack([vocal[0], vocal[0]])
    if instrumental.shape[0] == 1:
        instrumental = np.stack([instrumental[0], instrumental[0]])

    # Pad shorter track to match longer
    max_samples = max(vocal.shape[1], instrumental.shape[1])
    if vocal.shape[1] < max_samples:
        vocal = np.pad(vocal, ((0, 0), (0, max_samples - vocal.shape[1])))
    if instrumental.shape[1] < max_samples:
        instrumental = np.pad(
            instrumental, ((0, 0), (0, max_samples - instrumental.shape[1]))
        )

    # Apply full mixing chain to vocal
    vocal_f32 = vocal.astype(np.float32)
    vocal_f32 = _apply_noise_gate(vocal_f32, sample_rate, decisions.noise_gate)
    vocal_f32 = _apply_transient_shaper(vocal_f32, sample_rate, decisions.transient_shaper)
    vocal_f32 = _apply_channel_eq(vocal_f32, sample_rate, decisions.channel_eq)
    vocal_f32 = _apply_channel_compression(vocal_f32, sample_rate, decisions.channel_comp)
    vocal_f32 = _apply_reverb(vocal_f32, sample_rate, decisions.reverb)
    vocal_f32 = _apply_delay(vocal_f32, sample_rate, decisions.delay)
    vocal_f32 = _apply_panning(vocal_f32, decisions.mix_settings.vocal_pan)

    vocal_f64 = vocal_f32.astype(np.float64)

    # Normalize each track individually, then apply relative gain weights
    vocal_peak = np.max(np.abs(vocal_f64))
    if vocal_peak > 1e-6:
        vocal_f64 /= vocal_peak

    instr_peak = np.max(np.abs(instrumental))
    if instr_peak > 1e-6:
        instrumental /= instr_peak

    vocal_gain = 10.0 ** (decisions.mix_settings.vocal_gain_db / 20.0)
    instr_gain = 10.0 ** (decisions.mix_settings.instrumental_gain_db / 20.0)
    vocal_f64 *= vocal_gain
    instrumental *= instr_gain

    mix = vocal_f64 + instrumental
    peak = np.max(np.abs(mix))
    if peak > 0.99:
        mix *= 0.99 / peak

    return mix.astype(np.float32)
