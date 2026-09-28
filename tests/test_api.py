import pytest
import numpy as np
import soundfile as sf
import io
from pathlib import Path
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from core.schemas import (
    DSPDecisions, EQSettings, CompressorSettings,
    SaturatorSettings, StereoImageSettings, LimiterSettings,
)

from api import app, gradio_master
from core.delivery import parse_delivery_spec

client = TestClient(app)


def _mock_dsp_decisions():
    return DSPDecisions(
        corrective_eq=EQSettings(bands=[], label="corrective"),
        compressor=CompressorSettings(
            threshold_db=-18.0,
            ratio=2.0,
            attack_ms=10.0,
            release_ms=200.0,
            makeup_gain_db=2.0,
        ),
        tonal_eq=EQSettings(bands=[], label="tonal"),
        saturator=SaturatorSettings(drive_db=2.0, mix=0.3, mode="tape"),
        stereo_image=StereoImageSettings(width=1.0, mono_low_hz=80.0),
        limiter=LimiterSettings(ceiling_dbtp=-1.0, release_ms=100.0),
        target_lufs=-14.0,
        reasoning="mocked for CI test",
    )


def _make_wav_bytes(duration_s: float = 1.0, sr: int = 44100) -> bytes:
    rng = np.random.default_rng(42)
    noise = rng.standard_normal((int(sr * duration_s), 2)).astype(np.float32) * 0.1
    buf = io.BytesIO()
    sf.write(buf, noise, sr, format="WAV", subtype="PCM_16")
    buf.seek(0)
    return buf.read()


def test_health_check():
    response = client.get("/docs")
    assert response.status_code == 200


def test_master_invalid_bit_depth():
    wav_bytes = _make_wav_bytes()
    response = client.post(
        "/master",
        data={"prompt": "test", "bit_depth": 8},
        files={"file": ("test.wav", wav_bytes, "audio/wav")},
    )
    assert response.status_code == 400
    assert "bit_depth" in response.json()["detail"].lower()


def test_master_missing_file():
    response = client.post(
        "/master",
        data={"prompt": "test", "bit_depth": 24},
    )
    assert response.status_code == 422


def test_video_work_reference_is_labeled_in_ui_summary():
    job = MagicMock()
    job.delivery_spec = parse_delivery_spec("齿音过重，按照爱奇艺平台标准输出。")
    job.loudness_lufs = -15.02
    job.output_sample_peak_dbfs = -1.4
    job.true_peak_dbtp = -1.1
    job.output_sample_rate = 24000
    job.output_channels = 1
    job.output_bit_depth = 24
    job.output_is_dual_mono = False
    job.mix_decisions = None
    job.dsp_decisions = _mock_dsp_decisions()
    with patch("api._run_master", return_value=job):
        _, report = gradio_master("/tmp/example.wav", "齿音过重，按照爱奇艺平台标准输出。", 24, None)
    assert "工作参考｜国内网络视听平台" in report
    assert "-15 LUFS（工作参考）" in report
    assert "真峰值不超过 -1 dBTP（工作参考）" in report
    assert "官方依据：" not in report


@pytest.mark.parametrize("platform", ["抖音", "快手", "小红书"])
def test_short_video_reference_copy_does_not_name_another_platform(platform):
    prompt = f"按{platform}平台标准输出"
    job = MagicMock()
    job.delivery_spec = parse_delivery_spec(prompt)
    job.loudness_lufs = -15.0
    job.output_sample_peak_dbfs = -1.3
    job.true_peak_dbtp = -1.1
    job.output_sample_rate = 24000
    job.output_channels = 1
    job.output_bit_depth = 24
    job.output_is_dual_mono = False
    job.mix_decisions = None
    job.dsp_decisions = _mock_dsp_decisions()
    with patch("api._run_master", return_value=job):
        _, report = gradio_master("/tmp/example.wav", prompt, 24, None)
    assert "选用依据：短视频移动端工作参考（非平台官方标准）。" in report
    assert "适用边界：参照中国网络视听嘈杂接收环境参数；仅校验响度与真峰值。" in report
    assert "抖音平台" not in report
