import pytest
import numpy as np
import soundfile as sf
from pathlib import Path
from core.job import load_audio
from core.processor import process
from core.writer import write
from core.schemas import (
    DSPDecisions, EQSettings, EQBand,
    CompressorSettings, SaturatorSettings,
    StereoImageSettings, LimiterSettings,
)


@pytest.fixture
def ready_job(tmp_path):
    rng = np.random.default_rng(7)
    noise = rng.standard_normal((2, 44100 * 3)).astype(np.float32) * 0.125
    sf.write(str(tmp_path / "input.wav"), noise.T, 44100)

    job = load_audio(
        tmp_path / "input.wav",
        tmp_path / "output.wav",
        "master for streaming",
    )

    job.analysis = {
        "rms_db":                    -18.0,
        "crest_factor_db":            10.0,
        "dynamic_range_db":            8.0,
        "integrated_lufs":           -20.0,
        "true_peak_dbtp":             -2.0,
        "rms_sub_db":                -28.0,
        "rms_low_db":                -20.0,
        "rms_mid_db":                -18.0,
        "rms_high_db":               -22.0,
        "spectral_centroid_hz":     1200.0,
        "spectral_flatness":           0.8,
        "stereo_width":                0.0,
        "low_end_mono_compatibility":  0.0,
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
        reasoning="writer test",
    )

    job = process(job)
    return job


def test_write_creates_file(ready_job):
    result_path = write(ready_job)
    assert result_path.exists()
    assert result_path == ready_job.output_path


def test_write_16bit_dither(ready_job):
    result_path = write(ready_job, bit_depth=16)
    assert result_path.exists()
    data, sr = sf.read(str(result_path))
    assert sr == ready_job.sample_rate
    assert data.ndim == 2
    assert data.shape[1] == 2


def test_write_32bit_float(ready_job):
    result_path = write(ready_job, bit_depth=32)
    assert result_path.exists()
    data, sr = sf.read(str(result_path))
    assert sr == ready_job.sample_rate
    assert data.shape[0] > 0
