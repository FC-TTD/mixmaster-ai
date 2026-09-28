import pytest

from core.delivery import parse_delivery_spec
from core.writer import write


def test_cgtn_delivery_contract():
    spec = parse_delivery_spec(
        "播出声采用立体声、48 kHz / 24-bit PCM，最大峰值不得超过 -12 dBFS"
    )
    assert spec.sample_rate_hz == 48000
    assert spec.channels == 2
    assert spec.bit_depth == 24
    assert spec.max_sample_peak_dbfs == -12
    assert spec.max_true_peak_dbtp is None


def test_independent_sample_and_true_peak_limits():
    spec = parse_delivery_spec("44.1 kHz，16 bit，-14 LUFS，峰值 -1 dBFS，真峰值 -2 dBTP")
    assert spec.sample_rate_hz == 44100
    assert spec.bit_depth == 16
    assert spec.target_lufs == -14
    assert spec.max_sample_peak_dbfs == -1
    assert spec.max_true_peak_dbtp == -2


def test_unsupported_bit_depth_fails_clearly():
    with pytest.raises(ValueError, match="不支持的导出位深"):
        parse_delivery_spec("交付 20-bit PCM")


def test_conflicting_peak_limits_fail_clearly():
    with pytest.raises(ValueError, match="互相冲突"):
        parse_delivery_spec("最大 -1 dBFS，另要 -12 dBFS")
