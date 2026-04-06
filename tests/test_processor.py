import pytest
import numpy as np
import soundfile as sf
from pathlib import Path
from core.job import load_audio
from core.processor import process
from core.schemas import (
    DSPDecisions, EQSettings, EQBand,
    CompressorSettings, SaturatorSettings,
    StereoImageSettings, LimiterSettings,
)


@pytest.fixture
def processed_job(tmp_path):
    rng = np.random.default_rng(42)
    noise = rng.standard_normal((2, 44100 * 3)).astype(np.float32) * 0.125
    sf.write(str(tmp_path / "noise.wav"), noise.T, 44100)

    job = load_audio(
        tmp_path / "noise.wav",
        tmp_path / "out.wav",
        "warm master",
    )

    job.analysis = {
        "rms_db": 0.0,
        "crest_factor_db": 0.0,
        "dynamic_range_db": 0.0,
        "integrated_lufs": 0.0,
        "true_peak_dbtp": 0.0,
        "rms_sub_db": 0.0,
        "rms_low_db": 0.0,
        "rms_mid_db": 0.0,
        "rms_high_db": 0.0,
        "spectral_centroid_hz": 0.0,
        "spectral_flatness": 0.0,
        "stereo_width": 0.0,
        "low_end_mono_compatibility": 0.0,
    }

    job.dsp_decisions = DSPDecisions(
        corrective_eq=EQSettings(bands=[], label="corrective"),
        compressor=CompressorSettings(
            threshold_db=-18.0,
            ratio=2.0,
            attack_ms=10.0,
            release_ms=200.0,
            makeup_gain_db=2.0,
        ),
        tonal_eq=EQSettings(
            bands=[
                EQBand(
                    frequency=10000.0,
                    gain_db=1.5,
                    q=0.7,
                    filter_type="high_shelf",
                )
            ],
            label="tonal",
        ),
        saturator=SaturatorSettings(drive_db=2.0, mix=0.3, mode="tape"),
        stereo_image=StereoImageSettings(width=1.1, mono_low_hz=80.0),
        limiter=LimiterSettings(ceiling_dbtp=-1.0, release_ms=100.0),
        target_lufs=-14.0,
        reasoning="test",
    )

    return process(job)


def test_processed_audio_shape(processed_job):
    assert processed_job.processed_audio.shape == processed_job.audio.shape


def test_processed_audio_dtype(processed_job):
    assert processed_job.processed_audio.dtype == np.float32


def test_loudness_measured(processed_job):
    assert processed_job.loudness_lufs is not None
    assert isinstance(processed_job.loudness_lufs, float)
    assert -80.0 < processed_job.loudness_lufs < 0.0


def test_status_done(processed_job):
    assert processed_job.status == "done"
