import numpy as np
import pytest

from core.mixer import (
    _apply_channel_compression,
    _apply_channel_eq,
    _apply_delay,
    _apply_noise_gate,
    _apply_panning,
    _apply_reverb,
    _apply_transient_shaper,
    mix_tracks,
)
from core.schemas import (
    ChannelCompSettings,
    DelaySettings,
    EQBand,
    EQSettings,
    MixDecisions,
    MixSettings,
    NoiseGateSettings,
    ReverbSettings,
    TransientShaperSettings,
)

SR = 44100


# ---------------------------------------------------------------------------
# Audio generators (synthetic only — no real files)
# ---------------------------------------------------------------------------

def make_stereo(freq=440, duration=2.0, sr=SR, amplitude=0.5):
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    wave = (np.sin(2 * np.pi * freq * t) * amplitude).astype(np.float32)
    return np.stack([wave, wave])


def make_mono(freq=440, duration=2.0, sr=SR, amplitude=0.5):
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    wave = (np.sin(2 * np.pi * freq * t) * amplitude).astype(np.float32)
    return wave.reshape(1, -1)


def make_silence(channels=2, duration=2.0, sr=SR):
    return np.zeros((channels, int(sr * duration)), dtype=np.float32)


def make_short(freq=440, sr=SR, amplitude=0.5):
    return make_stereo(freq=freq, duration=0.1, sr=sr, amplitude=amplitude)


def make_full_amplitude(freq=440, duration=2.0, sr=SR):
    return make_stereo(freq=freq, duration=duration, sr=sr, amplitude=0.99)


# ---------------------------------------------------------------------------
# Standard DSP assertions
# ---------------------------------------------------------------------------

def assert_dsp_output(output, expected_shape):
    assert output.shape == expected_shape, f"Shape {output.shape} != {expected_shape}"
    assert output.dtype == np.float32, f"Expected float32, got {output.dtype}"
    assert np.max(np.abs(output)) <= 1.0, f"Clipping: max={np.max(np.abs(output)):.4f}"
    assert np.all(np.isfinite(output)), "NaN or Inf in output"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def gate_s():
    return NoiseGateSettings(threshold_db=-40.0, attack_ms=1.0, release_ms=100.0)


@pytest.fixture
def transient_s():
    return TransientShaperSettings(attack_boost_db=6.0, sustain_cut_db=3.0, mix=1.0)


@pytest.fixture
def eq_s():
    return EQSettings(
        bands=[EQBand(frequency=1000.0, gain_db=2.0, q=1.0, filter_type="peak")],
        label="test eq",
    )


@pytest.fixture
def comp_s():
    return ChannelCompSettings(
        threshold_db=-12.0, ratio=4.0, attack_ms=5.0, release_ms=100.0, makeup_gain_db=3.0
    )


@pytest.fixture
def reverb_s():
    return ReverbSettings(room_size=0.5, damping=0.5, wet_mix=0.3, pre_delay_ms=20.0)


@pytest.fixture
def delay_s():
    return DelaySettings(delay_ms=125.0, feedback=0.3, wet_mix=0.3, enabled=True)


@pytest.fixture
def mix_decisions():
    return MixDecisions(
        noise_gate=NoiseGateSettings(threshold_db=-40.0, attack_ms=1.0, release_ms=100.0),
        transient_shaper=TransientShaperSettings(attack_boost_db=3.0, sustain_cut_db=0.0, mix=1.0),
        channel_eq=EQSettings(
            bands=[EQBand(frequency=200.0, gain_db=-2.0, q=0.7, filter_type="peak")],
            label="channel eq",
        ),
        channel_comp=ChannelCompSettings(
            threshold_db=-12.0, ratio=3.0, attack_ms=5.0, release_ms=100.0, makeup_gain_db=2.0
        ),
        reverb=ReverbSettings(room_size=0.4, damping=0.5, wet_mix=0.2, pre_delay_ms=10.0),
        delay=DelaySettings(delay_ms=125.0, feedback=0.2, wet_mix=0.2, enabled=True),
        mix_settings=MixSettings(vocal_gain_db=0.0, instrumental_gain_db=-3.0, vocal_pan=0.0),
        reasoning="test",
    )


# ---------------------------------------------------------------------------
# _apply_noise_gate
# ---------------------------------------------------------------------------

def test_apply_noise_gate_stereo(gate_s):
    audio = make_stereo()
    assert_dsp_output(_apply_noise_gate(audio, SR, gate_s), audio.shape)


def test_apply_noise_gate_silence(gate_s):
    audio = make_silence()
    result = _apply_noise_gate(audio, SR, gate_s)
    assert result.shape == audio.shape
    assert result.dtype == np.float32
    assert np.all(np.isfinite(result))


def test_apply_noise_gate_mono(gate_s):
    audio = make_mono()
    assert_dsp_output(_apply_noise_gate(audio, SR, gate_s), audio.shape)


def test_apply_noise_gate_short(gate_s):
    audio = make_short()
    assert_dsp_output(_apply_noise_gate(audio, SR, gate_s), audio.shape)


def test_apply_noise_gate_full_amplitude(gate_s):
    audio = make_full_amplitude()
    assert_dsp_output(_apply_noise_gate(audio, SR, gate_s), audio.shape)


# ---------------------------------------------------------------------------
# _apply_transient_shaper
# ---------------------------------------------------------------------------

def test_apply_transient_shaper_stereo(transient_s):
    audio = make_stereo()
    assert_dsp_output(_apply_transient_shaper(audio, SR, transient_s), audio.shape)


def test_apply_transient_shaper_silence(transient_s):
    audio = make_silence()
    result = _apply_transient_shaper(audio, SR, transient_s)
    assert result.shape == audio.shape
    assert result.dtype == np.float32
    assert np.all(np.isfinite(result))


def test_apply_transient_shaper_mono(transient_s):
    audio = make_mono()
    assert_dsp_output(_apply_transient_shaper(audio, SR, transient_s), audio.shape)


def test_apply_transient_shaper_short(transient_s):
    audio = make_short()
    assert_dsp_output(_apply_transient_shaper(audio, SR, transient_s), audio.shape)


def test_apply_transient_shaper_full_amplitude(transient_s):
    audio = make_full_amplitude()
    assert_dsp_output(_apply_transient_shaper(audio, SR, transient_s), audio.shape)


def test_apply_transient_shaper_zero_boost():
    settings = TransientShaperSettings(attack_boost_db=0.0, sustain_cut_db=0.0, mix=1.0)
    audio = make_stereo()
    result = _apply_transient_shaper(audio, SR, settings)
    assert_dsp_output(result, audio.shape)


# ---------------------------------------------------------------------------
# _apply_channel_eq
# ---------------------------------------------------------------------------

def test_apply_channel_eq_stereo(eq_s):
    audio = make_stereo()
    assert_dsp_output(_apply_channel_eq(audio, SR, eq_s), audio.shape)


def test_apply_channel_eq_silence(eq_s):
    audio = make_silence()
    result = _apply_channel_eq(audio, SR, eq_s)
    assert result.shape == audio.shape
    assert result.dtype == np.float32
    assert np.all(np.isfinite(result))


def test_apply_channel_eq_mono(eq_s):
    audio = make_mono()
    assert_dsp_output(_apply_channel_eq(audio, SR, eq_s), audio.shape)


def test_apply_channel_eq_short(eq_s):
    audio = make_short()
    assert_dsp_output(_apply_channel_eq(audio, SR, eq_s), audio.shape)


def test_apply_channel_eq_full_amplitude(eq_s):
    audio = make_full_amplitude()
    assert_dsp_output(_apply_channel_eq(audio, SR, eq_s), audio.shape)


def test_apply_channel_eq_no_bands():
    eq_empty = EQSettings(bands=[], label="passthrough")
    audio = make_stereo()
    result = _apply_channel_eq(audio, SR, eq_empty)
    assert_dsp_output(result, audio.shape)


# ---------------------------------------------------------------------------
# _apply_channel_compression
# ---------------------------------------------------------------------------

def test_apply_channel_compression_stereo(comp_s):
    audio = make_stereo()
    assert_dsp_output(_apply_channel_compression(audio, SR, comp_s), audio.shape)


def test_apply_channel_compression_silence(comp_s):
    audio = make_silence()
    result = _apply_channel_compression(audio, SR, comp_s)
    assert result.shape == audio.shape
    assert result.dtype == np.float32
    assert np.all(np.isfinite(result))


def test_apply_channel_compression_mono(comp_s):
    audio = make_mono()
    assert_dsp_output(_apply_channel_compression(audio, SR, comp_s), audio.shape)


def test_apply_channel_compression_short(comp_s):
    audio = make_short()
    assert_dsp_output(_apply_channel_compression(audio, SR, comp_s), audio.shape)


def test_apply_channel_compression_full_amplitude(comp_s):
    audio = make_full_amplitude()
    assert_dsp_output(_apply_channel_compression(audio, SR, comp_s), audio.shape)


# ---------------------------------------------------------------------------
# _apply_reverb
# ---------------------------------------------------------------------------

def test_apply_reverb_stereo(reverb_s):
    audio = make_stereo()
    assert_dsp_output(_apply_reverb(audio, SR, reverb_s), audio.shape)


def test_apply_reverb_silence(reverb_s):
    audio = make_silence()
    result = _apply_reverb(audio, SR, reverb_s)
    assert result.shape == audio.shape
    assert result.dtype == np.float32
    assert np.all(np.isfinite(result))


def test_apply_reverb_mono(reverb_s):
    audio = make_mono()
    result = _apply_reverb(audio, SR, reverb_s)
    assert result.shape == audio.shape
    assert result.dtype == np.float32
    assert np.max(np.abs(result)) <= 1.0
    assert np.all(np.isfinite(result))


def test_apply_reverb_short(reverb_s):
    audio = make_short()
    assert_dsp_output(_apply_reverb(audio, SR, reverb_s), audio.shape)


def test_apply_reverb_full_amplitude(reverb_s):
    audio = make_full_amplitude()
    assert_dsp_output(_apply_reverb(audio, SR, reverb_s), audio.shape)


def test_apply_reverb_no_predelay():
    settings = ReverbSettings(room_size=0.5, damping=0.5, wet_mix=0.2, pre_delay_ms=0.0)
    audio = make_stereo()
    assert_dsp_output(_apply_reverb(audio, SR, settings), audio.shape)


# ---------------------------------------------------------------------------
# _apply_delay
# ---------------------------------------------------------------------------

def test_apply_delay_stereo(delay_s):
    audio = make_stereo(duration=0.5)
    assert_dsp_output(_apply_delay(audio, SR, delay_s), audio.shape)


def test_apply_delay_silence(delay_s):
    audio = make_silence(duration=0.5)
    result = _apply_delay(audio, SR, delay_s)
    assert result.shape == audio.shape
    assert result.dtype == np.float32
    assert np.all(np.isfinite(result))


def test_apply_delay_mono(delay_s):
    audio = make_mono(duration=0.5)
    result = _apply_delay(audio, SR, delay_s)
    assert result.shape == audio.shape
    assert result.dtype == np.float32
    assert np.max(np.abs(result)) <= 1.0
    assert np.all(np.isfinite(result))


def test_apply_delay_short(delay_s):
    audio = make_short()
    result = _apply_delay(audio, SR, delay_s)
    assert result.shape == audio.shape
    assert result.dtype == np.float32
    assert np.max(np.abs(result)) <= 1.0
    assert np.all(np.isfinite(result))


def test_apply_delay_full_amplitude(delay_s):
    audio = make_full_amplitude(duration=0.5)
    assert_dsp_output(_apply_delay(audio, SR, delay_s), audio.shape)


def test_apply_delay_disabled():
    settings = DelaySettings(delay_ms=250.0, feedback=0.3, wet_mix=0.3, enabled=False)
    audio = make_stereo()
    result = _apply_delay(audio, SR, settings)
    assert result.shape == audio.shape
    assert result.dtype == np.float32
    # Disabled delay returns input unchanged (cast to float32)
    np.testing.assert_array_almost_equal(result, audio.astype(np.float32))


def test_apply_delay_zero_wet_mix():
    settings = DelaySettings(delay_ms=250.0, feedback=0.3, wet_mix=0.0, enabled=True)
    audio = make_stereo(duration=0.5)
    result = _apply_delay(audio, SR, settings)
    # wet_mix=0 means no delay applied — same as disabled
    assert result.dtype == np.float32


# ---------------------------------------------------------------------------
# _apply_panning
# ---------------------------------------------------------------------------

def test_apply_panning_center_stereo():
    audio = make_stereo()
    result = _apply_panning(audio, pan=0.0)
    assert result.shape == (2, audio.shape[1])
    assert result.dtype == np.float32
    assert np.max(np.abs(result)) <= 1.0
    assert np.all(np.isfinite(result))
    # Center pan: both channels unchanged
    np.testing.assert_array_almost_equal(result, audio.astype(np.float32))


def test_apply_panning_full_left():
    audio = make_stereo()
    result = _apply_panning(audio, pan=-1.0)
    assert result.shape == (2, audio.shape[1])
    assert result.dtype == np.float32
    # Right channel should be silent
    assert np.max(np.abs(result[1])) < 1e-6


def test_apply_panning_full_right():
    audio = make_stereo()
    result = _apply_panning(audio, pan=1.0)
    assert result.shape == (2, audio.shape[1])
    assert result.dtype == np.float32
    # Left channel should be silent
    assert np.max(np.abs(result[0])) < 1e-6


def test_apply_panning_mono_input():
    audio = make_mono()
    result = _apply_panning(audio, pan=0.0)
    # Mono → stereo with center pan
    assert result.shape == (2, audio.shape[1])
    assert result.dtype == np.float32
    assert np.max(np.abs(result)) <= 1.0
    assert np.all(np.isfinite(result))


def test_apply_panning_silence():
    audio = make_silence()
    result = _apply_panning(audio, pan=0.3)
    assert result.shape == (2, audio.shape[1])
    assert result.dtype == np.float32
    assert np.all(np.isfinite(result))


def test_apply_panning_full_amplitude():
    audio = make_full_amplitude()
    result = _apply_panning(audio, pan=0.5)
    assert result.shape == (2, audio.shape[1])
    assert result.dtype == np.float32
    assert np.max(np.abs(result)) <= 1.0


# ---------------------------------------------------------------------------
# mix_tracks
# ---------------------------------------------------------------------------

def test_mix_tracks_returns_stereo(mix_decisions):
    vocal = make_stereo(freq=440, duration=0.5)
    instr = make_stereo(freq=220, duration=0.5)
    result = mix_tracks(vocal, instr, SR, mix_decisions)
    assert result.shape == (2, vocal.shape[1])
    assert result.dtype == np.float32
    assert np.max(np.abs(result)) <= 1.0
    assert np.all(np.isfinite(result))


def test_mix_tracks_mono_inputs(mix_decisions):
    vocal = make_mono(duration=0.5)
    instr = make_mono(freq=220, duration=0.5)
    result = mix_tracks(vocal, instr, SR, mix_decisions)
    assert result.shape[0] == 2
    assert result.dtype == np.float32
    assert np.max(np.abs(result)) <= 1.0
    assert np.all(np.isfinite(result))


def test_mix_tracks_different_lengths(mix_decisions):
    vocal = make_stereo(duration=0.3)
    instr = make_stereo(freq=220, duration=0.5)
    result = mix_tracks(vocal, instr, SR, mix_decisions)
    assert result.shape == (2, instr.shape[1])
    assert result.dtype == np.float32
    assert np.max(np.abs(result)) <= 1.0
    assert np.all(np.isfinite(result))


def test_mix_tracks_silence_vocal(mix_decisions):
    vocal = make_silence(duration=0.5)
    instr = make_stereo(freq=220, duration=0.5)
    result = mix_tracks(vocal, instr, SR, mix_decisions)
    assert result.shape[0] == 2
    assert result.dtype == np.float32
    assert np.max(np.abs(result)) <= 1.0
    assert np.all(np.isfinite(result))


def test_mix_tracks_both_silence(mix_decisions):
    vocal = make_silence(duration=0.5)
    instr = make_silence(duration=0.5)
    result = mix_tracks(vocal, instr, SR, mix_decisions)
    assert result.shape[0] == 2
    assert result.dtype == np.float32
    assert np.all(np.isfinite(result))


def test_mix_tracks_full_amplitude(mix_decisions):
    vocal = make_full_amplitude(duration=0.5)
    instr = make_full_amplitude(freq=220, duration=0.5)
    result = mix_tracks(vocal, instr, SR, mix_decisions)
    assert result.shape[0] == 2
    assert result.dtype == np.float32
    assert np.max(np.abs(result)) <= 1.0
    assert np.all(np.isfinite(result))
