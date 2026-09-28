import numpy as np

from core.agent import _honor_explicit_tone_request
from core.processor import _apply_de_esser, _apply_eq
from core.schemas import (
    CompressorSettings, DSPDecisions, EQSettings, LimiterSettings,
    SaturatorSettings, StereoImageSettings,
)


def neutral_decisions() -> DSPDecisions:
    return DSPDecisions(
        corrective_eq=EQSettings(bands=[], label="corrective"),
        compressor=CompressorSettings(threshold_db=-20, ratio=1, attack_ms=10, release_ms=100, makeup_gain_db=0),
        tonal_eq=EQSettings(bands=[], label="tonal"),
        saturator=SaturatorSettings(drive_db=0, mix=0, mode="tape"),
        stereo_image=StereoImageSettings(width=1, mono_low_hz=20),
        limiter=LimiterSettings(ceiling_dbtp=-1, release_ms=100),
        target_lufs=-14,
        reasoning="neutral",
    )


def test_dark_tone_request_becomes_audible_high_shelf():
    decision = neutral_decisions()
    _honor_explicit_tone_request(decision, "音色太暗，高频不足")
    shelf = decision.tonal_eq.bands[0]
    assert shelf.filter_type == "high_shelf"
    assert shelf.gain_db >= 3
    sr = 24000
    t = np.arange(sr) / sr
    audio = (0.1 * np.sin(2 * np.pi * 700 * t) + 0.02 * np.sin(2 * np.pi * 7000 * t))[None, :]
    rendered = _apply_eq(audio.copy(), sr, decision.tonal_eq)
    assert np.std(rendered - 0.1 * np.sin(2 * np.pi * 700 * t)) > np.std(audio - 0.1 * np.sin(2 * np.pi * 700 * t)) * 1.25


def test_weaken_highs_is_not_misread_as_brighten():
    decision = neutral_decisions()
    _honor_explicit_tone_request(decision, "高频弱化")
    assert decision.tonal_eq.bands[0].gain_db <= -3


def test_sibilance_enables_dynamic_band_reduction():
    decision = neutral_decisions()
    _honor_explicit_tone_request(decision, "齿音过重")
    assert decision.de_esser.enabled
    sr = 24000
    t = np.arange(sr) / sr
    audio = 0.1 * np.sin(2 * np.pi * 500 * t) + 0.01 * np.sin(2 * np.pi * 6500 * t)
    burst = (t > 0.35) & (t < 0.5)
    audio[burst] += 0.2 * np.sin(2 * np.pi * 6500 * t[burst])
    processed = _apply_de_esser(audio[None, :].copy(), sr, decision.de_esser)[0]
    assert np.std(processed[burst] - 0.1 * np.sin(2 * np.pi * 500 * t[burst])) < np.std(audio[burst] - 0.1 * np.sin(2 * np.pi * 500 * t[burst])) * 0.85
    assert np.sqrt(np.mean((processed[~burst] - audio[~burst]) ** 2)) < 0.005
