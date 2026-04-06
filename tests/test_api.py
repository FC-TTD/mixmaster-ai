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

from api import app

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
