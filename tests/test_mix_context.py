import numpy as np
import soundfile as sf

from core.job import load_audio
from core.mix_context import align_instrumental, mix_input_features


def _job(tmp_path, name, sample_rate, amplitude):
    t = np.arange(sample_rate * 2) / sample_rate
    signal = (amplitude * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
    path = tmp_path / f"{name}.wav"
    sf.write(path, signal, sample_rate)
    return load_audio(path, tmp_path / f"{name}-out.wav", "clean vocal mix")


def test_mix_levels_account_for_stem_peak_normalization(tmp_path):
    vocal = _job(tmp_path, "vocal", 44100, 0.05)
    beat = _job(tmp_path, "beat", 44100, 0.5)
    features = mix_input_features(vocal, beat)
    raw_difference = (
        features["vocal"]["raw_rms_dbfs"]
        - features["instrumental"]["raw_rms_dbfs"]
    )
    assert raw_difference < -19
    assert abs(features["vocal_minus_instrumental_normalized_rms_db"]) < 0.01


def test_instrumental_is_resampled_before_mix(tmp_path):
    beat = _job(tmp_path, "beat", 24000, 0.2)
    aligned = align_instrumental(beat, 48000)
    assert aligned.sample_rate == 48000
    assert aligned.audio.shape == (1, 96000)
    assert abs(aligned.duration_seconds - 2.0) < 0.001
