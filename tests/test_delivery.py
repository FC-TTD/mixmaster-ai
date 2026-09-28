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


def test_generic_streaming_brief_gets_complete_reference_targets():
    spec = parse_delivery_spec("按照流媒体作品标准输出。")
    assert spec.profile_name is not None
    assert spec.target_lufs == -14
    assert spec.max_true_peak_dbtp == -1
    assert spec.sample_rate_hz is None
    assert spec.channels is None


def test_streaming_explicit_numbers_override_reference_targets():
    spec = parse_delivery_spec("流媒体发布，-16 LUFS，真峰值 -3 dBTP")
    assert spec.target_lufs == -16
    assert spec.max_true_peak_dbtp == -3


def test_louder_streaming_target_gets_stricter_true_peak_reference():
    spec = parse_delivery_spec("流媒体，-12 LUFS")
    assert spec.target_lufs == -12
    assert spec.max_true_peak_dbtp == -2


def test_video_platform_uses_labeled_work_reference_not_spotify_standard():
    spec = parse_delivery_spec("按 YouTube 流媒体标准，-14 LUFS")
    assert spec.profile_id == "video_mobile_reference"
    assert spec.profile_basis_kind == "工作参考"
    assert spec.target_lufs == -14
    assert spec.loudness_origin == "客户指定"
    assert spec.max_true_peak_dbtp == -1
    assert spec.true_peak_origin == "工作参考"
    spec = parse_delivery_spec("按 YouTube 流媒体要求，-14 LUFS，真峰值 -1 dBTP")
    assert spec.profile_basis_kind == "工作参考"
    assert spec.target_lufs == -14
    assert spec.max_true_peak_dbtp == -1


@pytest.mark.parametrize("brief, lufs, peak", [
    ("Apple Music 发布", -14, -1),
    ("QQ 音乐发布", -14, -1),
    ("网易云音乐发布", -14, -1),
    ("抖音短视频发布", -15, -1),
    ("爱奇艺平台标准输出", -15, -1),
    ("iQIYI 平台标准输出", -15, -1),
    ("爱奇艺电视端安静环境输出", -24, -1),
    ("优酷平台输出", -15, -1),
    ("腾讯视频平台输出", -15, -1),
    ("Bilibili 视频输出", -15, -1),
    ("芒果TV 输出", -15, -1),
    ("快手短视频输出", -15, -1),
    ("中国电视播出", -24, -2),
    ("BBC 电视", -23, -1),
])
def test_named_destination_uses_one_declared_reference(brief, lufs, peak):
    spec = parse_delivery_spec(brief)
    assert spec.target_lufs == lufs
    assert spec.max_true_peak_dbtp == peak
    assert spec.profile_name is not None
    assert spec.profile_source_url is not None


def test_sibilance_and_iqiyi_brief_still_resolves_for_processing():
    spec = parse_delivery_spec("齿音过重，按照爱奇艺平台标准输出。")
    assert spec.profile_id == "cn_video_mobile_reference"
    assert spec.profile_basis_kind == "工作参考"
    assert spec.target_lufs == -15
    assert spec.max_true_peak_dbtp == -1


@pytest.mark.parametrize("brief, kind", [
    ("Spotify 发布", "母带建议"),
    ("SoundCloud 发布", "母带建议"),
    ("Apple Music 发布", "工作参考"),
    ("QQ 音乐发布", "工作参考"),
    ("抖音发布", "工作参考"),
    ("爱奇艺平台标准输出", "工作参考"),
    ("Apple Podcasts 播客", "制作建议"),
    ("中国数字电视 GY/T 282", "交付规范"),
    ("ATSC A/85 短节目", "节目响度建议"),
])
def test_profile_origin_is_distinguished_from_platform_requirement(brief, kind):
    spec = parse_delivery_spec(brief)
    assert spec.profile_basis_kind == kind
    assert spec.loudness_origin == kind
    assert spec.true_peak_origin == kind


def test_explicit_values_override_each_selected_reference_dimension():
    spec = parse_delivery_spec("网易云音乐交付：-17 LUFS，真峰值 -2 dBTP")
    assert spec.target_lufs == -17
    assert spec.max_true_peak_dbtp == -2
    assert spec.loudness_origin == "客户指定"
    assert spec.true_peak_origin == "客户指定"
    spec = parse_delivery_spec("抖音短视频：-16 LKFS")
    assert spec.target_lufs == -16
    assert spec.max_true_peak_dbtp == -1
    assert spec.loudness_origin == "客户指定"
    assert spec.true_peak_origin == "工作参考"
    spec = parse_delivery_spec("爱奇艺平台输出，-18 LUFS，真峰值 -3 dBTP")
    assert spec.target_lufs == -18
    assert spec.max_true_peak_dbtp == -3
    assert spec.loudness_origin == "客户指定"
    assert spec.true_peak_origin == "客户指定"


@pytest.mark.parametrize("brief", [
    "EBU R 128 s2 广播内容网络分发",
    "Netflix 近场电影混音",
    "Apple Digital Masters 认证",
    "Spotify 高音量模式",
])
def test_non_mastering_target_never_inherits_music_streaming_preset(brief):
    with pytest.raises(ValueError):
        parse_delivery_spec(brief)


def test_theatrical_delivery_does_not_invent_loudness():
    with pytest.raises(ValueError, match="没有可在当前单音频链路核实"):
        parse_delivery_spec("院线电影母带")


def test_unsupported_bit_depth_fails_clearly():
    with pytest.raises(ValueError, match="不支持的导出位深"):
        parse_delivery_spec("交付 20-bit PCM")


def test_conflicting_peak_limits_fail_clearly():
    with pytest.raises(ValueError, match="互相冲突"):
        parse_delivery_spec("最大 -1 dBFS，另要 -12 dBFS")
