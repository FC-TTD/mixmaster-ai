import numpy as np
import pytest
import soundfile as sf
from pathlib import Path
from core.job import load_audio
from core.analyzer import analyze


@pytest.fixture
def sine_job(tmp_path):
    amplitude = np.sqrt(2) * 10 ** (-6.0 / 20)  # RMS at -6dBFS (peak = -6 + 3.01 dBFS)
    t = np.linspace(0, 3.0, int(44100 * 3), endpoint=False)
    sine = (amplitude * np.sin(2 * np.pi * 1000 * t)).astype(np.float32)
    audio_2ch = np.stack([sine, sine])  # shape (2, samples)
    path = tmp_path / "sine.wav"
    sf.write(str(path), audio_2ch.T, 44100)  # sf needs (samples, channels)
    return load_audio(path, tmp_path / "out.wav", "test")


def test_analysis_keys(sine_job):
    job = analyze(sine_job)
    expected_keys = {
        "rms_db", "crest_factor_db", "dynamic_range_db", "integrated_lufs",
        "true_peak_dbtp", "rms_sub_db", "rms_low_db", "rms_mid_db",
        "rms_high_db", "spectral_centroid_hz", "spectral_flatness",
        "stereo_width", "low_end_mono_compatibility",
    }
    assert set(job.analysis.keys()) == expected_keys
    assert all(isinstance(v, float) for v in job.analysis.values())


def test_rms_sine_wave(sine_job):
    job = analyze(sine_job)
    assert abs(job.analysis["rms_db"] - (-6.0)) < 1.0


def test_stereo_width_mono(tmp_path):
    t = np.linspace(0, 1.0, 44100, endpoint=False)
    mono_audio = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
    path = tmp_path / "mono.wav"
    sf.write(str(path), mono_audio, 44100)
    job = load_audio(path, tmp_path / "out.wav", "test")
    job = analyze(job)
    assert job.analysis["stereo_width"] == 0.0


def test_status_after_analyze(sine_job):
    job = analyze(sine_job)
    assert job.status == "pending"
