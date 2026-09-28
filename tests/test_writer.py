import pytest
import numpy as np
import pyloudnorm
import soundfile as sf
from pathlib import Path
from core.job import load_audio
from core.processor import process
from core.writer import write
from core.writer import _true_peak
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


def test_write_respects_broadcast_peak_ceiling(ready_job):
    ready_job.prompt = "立体声 48 kHz / 24-bit PCM，最大峰值不得超过 -12 dBFS"
    requested_peak = 10 ** (-12.0 / 20.0)
    unbounded_audio = ready_job.processed_audio * 10 ** (
        (ready_job.dsp_decisions.target_lufs - ready_job.loudness_lufs) / 20.0
    )
    assert np.max(np.abs(unbounded_audio)) > requested_peak

    result_path = write(ready_job, bit_depth=24)
    data, sample_rate = sf.read(str(result_path))

    assert sample_rate == 48000
    assert sf.info(str(result_path)).subtype == "PCM_24"
    assert data.shape[1] == 2
    assert np.max(np.abs(data)) <= requested_peak


def test_write_respects_true_peak_of_encoded_audio(ready_job):
    ready_job.prompt = "48 kHz，真峰值不得超过 -6 dBTP"
    result_path = write(ready_job, bit_depth=24)
    data, sample_rate = sf.read(str(result_path), always_2d=True)
    assert sample_rate == 48000
    assert _true_peak(data.T) <= -6 + 0.05


def test_impossible_loudness_and_peak_reports_conflict(ready_job):
    ready_job.prompt = "-6 LUFS，最大峰值 -12 dBFS"
    with pytest.raises(ValueError, match="无法同时达到"):
        write(ready_job)
    assert not ready_job.output_path.exists()


def test_short_mono_voice_with_sparse_peak_reaches_streaming_loudness(ready_job):
    voice = ready_job.processed_audio[:1].astype(np.float64)
    meter = pyloudnorm.Meter(ready_job.sample_rate)
    original_lufs = meter.integrated_loudness(voice[0])
    voice *= 10 ** ((-26.5 - original_lufs) / 20.0)
    voice[0, ready_job.sample_rate] = 10 ** (-7.5 / 20.0)
    ready_job.processed_audio = voice.astype(np.float32)
    ready_job.num_channels = 1
    ready_job.prompt = "按照流媒体作品标准输出，-14 LUFS"

    result_path = write(ready_job)
    data, sample_rate = sf.read(str(result_path))
    actual_lufs = pyloudnorm.Meter(sample_rate).integrated_loudness(data)

    assert data.ndim == 1
    assert abs(actual_lufs + 14) <= 0.25
    assert np.max(np.abs(data)) <= 10 ** (-0.3 / 20.0)


def test_mono_delivery_keeps_mono_layout(ready_job):
    ready_job.processed_audio = ready_job.processed_audio[:1]
    ready_job.num_channels = 1
    ready_job.prompt = "单声道 24-bit PCM"
    result_path = write(ready_job)
    assert sf.info(str(result_path)).channels == 1


def test_mono_input_can_meet_stereo_file_spec_as_dual_mono(ready_job):
    ready_job.processed_audio = ready_job.processed_audio[:1]
    ready_job.num_channels = 1
    ready_job.prompt = "立体声 48 kHz / 24-bit PCM，最大峰值不得超过 -12 dBFS"
    result_path = write(ready_job)
    data, sample_rate = sf.read(str(result_path), always_2d=True)
    assert sample_rate == 48000
    assert sf.info(str(result_path)).subtype == "PCM_24"
    assert data.shape[1] == 2
    np.testing.assert_array_equal(data[:, 0], data[:, 1])
    assert np.max(np.abs(data)) <= 10 ** (-12 / 20)
    assert ready_job.output_channels == 2
    assert ready_job.output_is_dual_mono
