"""Source-backed loudness/true-peak presets for the supported WAV mastering path.

These are enforceable subsets of delivery guidance, never certificates that a
complete broadcaster or platform specification has been met.
"""
from dataclasses import dataclass
import re
from typing import Literal


BasisKind = Literal["交付规范", "母带建议", "制作建议", "节目响度建议", "工作参考"]


@dataclass(frozen=True)
class DeliveryProfile:
    key: str
    label: str
    target_lufs: float | None
    max_true_peak_dbtp: float
    source_url: str
    note: str
    basis_kind: BasisKind = "工作参考"
    louder_true_peak_dbtp: float | None = None


PROFILES = {
    "music_streaming": DeliveryProfile(
        "music_streaming", "音乐流媒体参考（Spotify / SoundCloud）", -14, -1,
        "https://support.spotify.com/bj-en/artists/article/loudness-normalization/",
        "适用于未指定平台的音乐流媒体参考；不代表所有平台的统一交付标准。",
        basis_kind="工作参考",
        louder_true_peak_dbtp=-2,
    ),
    "music_platform_reference": DeliveryProfile(
        "music_platform_reference", "音乐平台通用母带参考（非指定平台标准）", -14, -1,
        "https://support.spotify.com/bj-en/artists/article/loudness-normalization/",
        "Apple Music、QQ 音乐、网易云音乐等未核实到同一套官方固定 LUFS/dBTP；使用可追溯的通用音乐母带参考，不宣称满足该平台专属标准。",
        basis_kind="工作参考",
    ),
    "short_video_mobile_reference": DeliveryProfile(
        "short_video_mobile_reference", "短视频移动端", -15, -1,
        "https://www.nrta.gov.cn/art/2023/9/14/art_3715_65554.html",
        "参照中国网络视听嘈杂接收环境参数；仅校验响度与真峰值。",
        basis_kind="工作参考",
    ),
    "cn_video_mobile_reference": DeliveryProfile(
        "cn_video_mobile_reference", "国内网络视听平台｜移动端工作参考", -15, -1,
        "https://www.nrta.gov.cn/art/2023/9/14/art_3715_65554.html",
        "识别为爱奇艺、优酷、腾讯视频等国内网络视听平台；未给接收环境时暂按移动端/嘈杂环境制作。采用 GY/T 377 的音频参考值，不是该平台公布的专属交付标准。",
        basis_kind="工作参考",
    ),
    "cn_video_quiet_reference": DeliveryProfile(
        "cn_video_quiet_reference", "国内网络视听平台｜安静环境工作参考", -24, -1,
        "https://www.nrta.gov.cn/art/2023/9/14/art_3715_65554.html",
        "识别为国内网络视听平台，且需求指出电视端、客厅或安静收听；采用 GY/T 377 的安静环境音频参考值，不是该平台公布的专属交付标准。",
        basis_kind="工作参考",
    ),
    "video_mobile_reference": DeliveryProfile(
        "video_mobile_reference", "在线视频平台｜移动端工作参考", -15, -1,
        "https://www.nrta.gov.cn/art/2023/9/14/art_3715_65554.html",
        "平台未提供可核实的固定母带数值；借用中国网络视听移动端音频参数作为制作起点，不代表 YouTube、TikTok 或 Instagram 的官方标准。",
        basis_kind="工作参考",
    ),
    "spotify": DeliveryProfile(
        "spotify", "Spotify 母带建议", -14, -1,
        "https://support.spotify.com/bj-en/artists/article/loudness-normalization/",
        "官方母带建议；不是 Spotify 播放端响度处理的认证。",
        basis_kind="母带建议",
        louder_true_peak_dbtp=-2,
    ),
    "soundcloud": DeliveryProfile(
        "soundcloud", "SoundCloud 母带建议", -14, -1,
        "https://help.soundcloud.com/hc/en-us/articles/360053660014-Will-SoundCloud-play-my-track-at-the-level-it-s-mastered",
        "官方母带建议；不包含平台上传格式的完整验证。",
        basis_kind="母带建议",
        louder_true_peak_dbtp=-2,
    ),
    "apple_podcasts": DeliveryProfile(
        "apple_podcasts", "Apple Podcasts 响度建议", -16, -1,
        "https://podcasters.apple.com/support/893-audio-requirements",
        "仅对应音频响度与真峰值建议；当前仍导出 WAV。",
        basis_kind="制作建议",
    ),
    "ebu_r128": DeliveryProfile(
        "ebu_r128", "EBU R 128 节目响度参考", -23, -1,
        "https://tech.ebu.ch/files/live/sites/tech/files/shared/r/r128.pdf",
        "仅核对综合响度与真峰值；未认证响度范围、元数据或分发链。",
        basis_kind="节目响度建议",
    ),
    "bbc_tv": DeliveryProfile(
        "bbc_tv", "BBC/DPP 电视响度参考", -23, -1,
        "https://downloads.bbc.co.uk/scotland/commissioning/TechnicalDeliveryStandardsBBCFile.pdf",
        "仅核对响度与真峰值；不生成 AS-11 文件或节目元数据。",
        basis_kind="交付规范",
    ),
    "cn_digital_tv": DeliveryProfile(
        "cn_digital_tv", "中国数字电视 GY/T 282—2014", -24, -2,
        "https://www.nrta.gov.cn/module/download/downfile.jsp?classid=0&filename=d31ca72b07b042d883c165df58d40820.pdf",
        "仅核对完整音频的平均响度与真峰值；机构另有交付要求时以其要求为准。",
        basis_kind="交付规范",
    ),
    "cn_network_av_noisy": DeliveryProfile(
        "cn_network_av_noisy", "中国网络视听 GY/T 377—2023（嘈杂环境版）", -15, -1,
        "https://www.nrta.gov.cn/art/2023/9/14/art_3715_65554.html",
        "适用于车载、户外等嘈杂接收环境；仅核对音频响度与真峰值。",
        basis_kind="交付规范",
    ),
    "cn_network_av_quiet": DeliveryProfile(
        "cn_network_av_quiet", "中国网络视听 GY/T 377—2023（安静环境版）", -24, -1,
        "https://www.nrta.gov.cn/art/2023/9/14/art_3715_65554.html",
        "适用于安静接收环境；仅核对音频响度与真峰值。",
        basis_kind="交付规范",
    ),
    "cn_network_av_custom": DeliveryProfile(
        "cn_network_av_custom", "中国网络视听：客户自定响度", None, -1,
        "https://www.nrta.gov.cn/art/2023/9/14/art_3715_65554.html",
        "客户响度不是 GY/T 377 的 -15/-24 LKFS 两种默认场景之一；只沿用同规范的真峰值参考，不声称符合其预设版本。",
        basis_kind="工作参考",
    ),
    "atsc_a85_short": DeliveryProfile(
        "atsc_a85_short", "ATSC A/85:2026-07 短节目参考", -24, -2,
        "https://www.atsc.org/wp-content/uploads/2026/07/A85-2026-07-Annex-M.pdf",
        "仅用于短节目全节目响度；长节目对白门控与元数据不在本链路能力内。",
        basis_kind="节目响度建议",
    ),
}


_OTHER_PLATFORMS = re.compile(
    r"netflix|院线|电影院|电影公映|影院|apple\s*digital\s*masters|"
    r"\bebu\s*r\s*128\s*s2\b",
    re.I,
)


def resolve_profile(brief: str, explicit_target: float | None, explicit_true_peak: float | None) -> DeliveryProfile | None:
    """Select exactly one named, supported profile; never mix platform values."""
    text = brief.lower()
    cn_video = bool(re.search(r"爱奇艺|iqiyi|优酷|youku|腾讯视频|tencent\s*video|bilibili|哔哩哔哩|b站|芒果\s*tv|mango\s*tv|搜狐视频", text, re.I))
    general_video = bool(re.search(r"youtube|tiktok|instagram(?:\s*reels)?|reels|影视流媒体|视频流媒体|电影流媒体", text, re.I))
    quiet_viewing = bool(re.search(r"安静|居家|客厅|电视端|家庭影院|大屏", text))
    noisy_viewing = bool(re.search(r"嘈杂|车载|户外|公交|地铁|手机|移动端|短视频", text))
    if quiet_viewing and noisy_viewing and (cn_video or general_video):
        raise ValueError("同时指定安静与嘈杂/移动接收环境，请明确一套交付场景。")
    if re.search(r"\bebu\s*r\s*128\s*s2\b|广播内容.*网络分发", text, re.I):
        if explicit_target is None or explicit_true_peak is None:
            raise ValueError("EBU R 128 s2 是广播内容网络分发建议：可维持 -23 LUFS，特定分发适配可在 -20 至 -16 LUFS；它没有统一 dBTP 配对值，请给出本次 LUFS 与 dBTP。")
        return None
    if re.search(r"\bspotify\b", text, re.I) and re.search(r"播放归一化|播放音量模式|高音量模式|低音量模式|\b(?:loud|quiet)\s+mode\b", text, re.I) and explicit_target is None:
        raise ValueError("Spotify 的播放音量模式是播放端归一化目标，不是母带交付目标；请明确需要的母带 LUFS 与 dBTP。")
    found: list[DeliveryProfile] = []

    def add(key: str, pattern: str) -> None:
        if re.search(pattern, text, re.I):
            found.append(PROFILES[key])

    add("spotify", r"\bspotify\b")
    add("soundcloud", r"\bsoundcloud\b")
    add("apple_podcasts", r"apple\s*podcasts?|苹果播客")
    add("ebu_r128", r"\bebu\s*r\s*128\b|欧洲广播联盟.*响度")
    add("bbc_tv", r"bbc.*(?:电视|tv|dpp)|(?:电视|tv|dpp).*bbc")
    add("cn_digital_tv", r"gy\s*/?\s*t\s*282|中国数字电视|国内数字电视|广电数字电视")
    if not found and re.search(r"中国电视|国内电视|电视播出|广电播出|cgtn|央视|中央电视台", text, re.I):
        found.append(PROFILES["cn_digital_tv"])

    network_av = bool(re.search(r"gy\s*/?\s*t\s*377", text, re.I)) or (
        not (cn_video or general_video) and bool(re.search(r"网络视听|中国网络视频", text, re.I))
    )
    if network_av:
        noisy = bool(re.search(r"嘈杂|车载|户外|公交|地铁|运动环境", text))
        quiet = bool(re.search(r"安静|居家|家庭环境|静音环境", text))
        if noisy and quiet:
            raise ValueError("网络视听同时指定嘈杂与安静接收环境，请选择一个版本。")
        if noisy or (not quiet and explicit_target == -15):
            found.append(PROFILES["cn_network_av_noisy"])
        elif quiet or explicit_target == -24:
            found.append(PROFILES["cn_network_av_quiet"])
        elif explicit_target is None:
            raise ValueError("GY/T 377 有 -15 LKFS（嘈杂环境）和 -24 LKFS（安静环境）两版，请说明接收环境或目标响度。")
        else:
            # The client's explicit loudness wins; both variants share -1 dBTP.
            found.append(PROFILES["cn_network_av_custom"])

    atsc = bool(re.search(r"\batsc\s*a\s*/?\s*85\b", text, re.I))
    if atsc:
        if re.search(r"短节目|短片|广告|short[ -]?form|promo", text, re.I):
            found.append(PROFILES["atsc_a85_short"])
        elif explicit_target is None or explicit_true_peak is None:
            raise ValueError("ATSC A/85 长短节目采用不同测量方法；请说明“短节目”，或同时给出 LUFS 和 dBTP。")

    if not found and re.search(r"apple\s*music|qq\s*音乐|网易云音乐|酷狗音乐|酷我音乐|tidal|amazon\s*music", text, re.I):
        found.append(PROFILES["music_platform_reference"])
    if not found and re.search(r"抖音|douyin|快手|kuaishou|小红书|短视频", text, re.I):
        found.append(PROFILES["short_video_mobile_reference"])
    if not found and cn_video:
        found.append(PROFILES["cn_video_quiet_reference" if quiet_viewing or explicit_target == -24 else "cn_video_mobile_reference"])
    if not found and general_video:
        found.append(PROFILES["video_mobile_reference"])
    if not found and re.search(r"音乐流媒体|流媒体|串流|streaming|音乐平台", text, re.I) and not _OTHER_PLATFORMS.search(text):
        found.append(PROFILES["music_streaming"])

    if len(found) > 1 or (_OTHER_PLATFORMS.search(text) and found):
        raise ValueError("交付要求中提到多个不同规范或平台，请选择一套标准；不会拼接不同平台的参数。")
    if found:
        return found[0]

    if _OTHER_PLATFORMS.search(text) and (explicit_target is None or explicit_true_peak is None):
        raise ValueError("该平台没有可在当前单音频链路核实并自动补齐的完整响度/真峰值预设；请同时给出 LUFS 与 dBTP。")
    return None
