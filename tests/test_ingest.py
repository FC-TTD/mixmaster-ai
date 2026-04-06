from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from core.job import load_audio


@pytest.fixture
def sample_wav_path(tmp_path):
    wav_path = tmp_path / "test_stereo.wav"
    audio = np.zeros((44100 * 2, 2), dtype=np.float32)
    sf.write(str(wav_path), audio, 44100)
    yield wav_path


def test_load_shape_and_dtype(sample_wav_path):
    job = load_audio(sample_wav_path, Path("out.wav"), "make it loud")
    assert job.audio.ndim == 2
    assert job.audio.shape[0] == job.num_channels
    assert job.audio.shape[1] > 0
    assert job.audio.dtype == np.float32


def test_stereo_channels(sample_wav_path):
    job = load_audio(sample_wav_path, Path("out.wav"), "test")
    assert job.num_channels == 2
    assert job.audio.shape[0] == 2


def test_invalid_path_raises():
    with pytest.raises(ValueError):
        load_audio(Path("/nonexistent/fake_audio.wav"), Path("out.wav"), "test")
