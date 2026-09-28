import pytest
import numpy as np
import soundfile as sf
from pathlib import Path
from unittest.mock import patch, MagicMock
from core.job import load_audio
from core.agent import decide, _validated_openai_decision
from core.schemas import DSPDecisions


@pytest.fixture(autouse=True)
def use_mocked_anthropic_provider(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")


@pytest.fixture
def analysis_job(tmp_path):
    t = np.linspace(0, 2.0, int(44100 * 2), endpoint=False)
    sine = (0.5 * np.sin(2 * np.pi * 1000 * t)).astype(np.float32)
    audio_2ch = np.stack([sine, sine]).T  # (samples, 2) for soundfile
    path = tmp_path / "agent_test.wav"
    sf.write(str(path), audio_2ch, 44100)
    job = load_audio(path, tmp_path / "out.wav", "master for streaming")
    job.analysis = {
        "rms_db": -12.0,
        "crest_factor_db": 10.0,
        "dynamic_range_db": 8.0,
        "integrated_lufs": -16.0,
        "true_peak_dbtp": -1.0,
        "rms_sub_db": -20.0,
        "rms_low_db": -14.0,
        "rms_mid_db": -12.0,
        "rms_high_db": -18.0,
        "spectral_centroid_hz": 1000.0,
        "spectral_flatness": 0.01,
        "stereo_width": 0.0,
        "low_end_mono_compatibility": 0.0,
    }
    return job


def _make_fake_response():
    """Build a mock anthropic response object with a tool_use block."""
    fake_input = {
        "corrective_eq": {
            "bands": [
                {
                    "frequency": 200.0,
                    "gain_db": -3.0,
                    "q": 1.0,
                    "filter_type": "peak",
                }
            ],
            "label": "corrective",
        },
        "compressor": {
            "threshold_db": -18.0,
            "ratio": 3.0,
            "attack_ms": 10.0,
            "release_ms": 200.0,
            "makeup_gain_db": 4.0,
        },
        "tonal_eq": {
            "bands": [
                {
                    "frequency": 10000.0,
                    "gain_db": 1.5,
                    "q": 0.7,
                    "filter_type": "high_shelf",
                }
            ],
            "label": "tonal",
        },
        "saturator": {
            "drive_db": 2.0,
            "mix": 0.3,
            "mode": "tape",
        },
        "stereo_image": {
            "width": 1.1,
            "mono_low_hz": 80.0,
        },
        "limiter": {
            "ceiling_dbtp": -1.0,
            "release_ms": 100.0,
        },
        "target_lufs": -14.0,
        "reasoning": "Gentle mastering for streaming with slight high-shelf air.",
    }

    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.input = fake_input

    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = "I will call the tool now."

    fake_response = MagicMock()
    # Deliberately put text_block first to verify next() type filter works
    fake_response.content = [text_block, tool_block]
    return fake_response


def test_decide_populates_dsp_decisions(analysis_job):
    with patch("core.agent.anthropic.Anthropic") as MockClient:
        mock_instance = MagicMock()
        MockClient.return_value = mock_instance
        mock_instance.messages.create.return_value = _make_fake_response()

        job = decide(analysis_job)

    assert job.dsp_decisions is not None
    assert isinstance(job.dsp_decisions, DSPDecisions)
    assert job.dsp_decisions.target_lufs == -14.0
    assert job.dsp_decisions.compressor.ratio == 3.0
    assert job.dsp_decisions.limiter.ceiling_dbtp == -1.0
    assert job.delivery_spec.target_lufs == -14.0
    assert job.delivery_spec.max_true_peak_dbtp == -1.0
    prompt_to_model = mock_instance.messages.create.call_args.kwargs["messages"][0]["content"]
    assert "target_lufs: -14" in prompt_to_model
    assert "max_true_peak_dbtp: -1" in prompt_to_model
    assert job.error is None


def test_decide_sets_status_processing(analysis_job):
    with patch("core.agent.anthropic.Anthropic") as MockClient:
        mock_instance = MagicMock()
        MockClient.return_value = mock_instance
        mock_instance.messages.create.return_value = _make_fake_response()

        job = decide(analysis_job)

    # Status becomes "processing" on entry. Since no error occurs and the
    # function does not reset it to another terminal state, it remains
    # "processing" after a successful call. This is correct — processor.py
    # will advance it to "done" in Phase 3.
    assert job.status == "processing"


def test_decide_on_api_error(analysis_job):
    with patch("core.agent.anthropic.Anthropic") as MockClient:
        mock_instance = MagicMock()
        MockClient.return_value = mock_instance
        mock_instance.messages.create.side_effect = Exception("API failure")

        with pytest.raises(Exception, match="API failure"):
            decide(analysis_job)

    assert analysis_job.status == "error"
    assert analysis_job.error == "API failure"


def test_openai_repairs_invalid_decision_once():
    valid = _make_fake_response().content[-1].input
    with patch("core.agent._call_openai_json", side_effect=[{"target_lufs": -14}, valid]) as call:
        result = _validated_openai_decision(DSPDecisions, "rules", "brief")
    assert result.target_lufs == -14
    assert call.call_count == 2
    assert "failed schema validation" in call.call_args.args[1]
