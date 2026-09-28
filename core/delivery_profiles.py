"""Source-backed loudness/true-peak presets for the supported WAV mastering path.

These are enforceable subsets of delivery guidance, never certificates that a
complete broadcaster or platform specification has been met.
"""
from dataclasses import dataclass
import re


@dataclass(frozen=True)
class DeliveryProfile:
    key: str
    label: str
    target_lufs: float | None
    max_true_peak_dbtp: float
    source_url: str
    note: str
    louder_true_peak_dbtp: float | None = None


PROFILES = {
    "music_streaming": DeliveryProfile(
        "music_streaming", "音乐流媒体参考（Spotify / SoundCloud）", -14, -1,
        "https://support.spotify.com/bj-en/artists/article/loudness-normalization/",
        "适用于未指定平台的音乐流媒体参考；不代表所有平台的统一交付标准。",
        louder_true_peak_dbtp=-2,
    ),
    "music_platform_reference": DeliveryProfile(
        "music_platform_reference", "音乐平台通用母带参考（非指定平台标准）", -14, -1,
        "https://support.spotify.com/bj-en/artists/article/loudness-normalization/",
        "Apple Music、QQ 音乐、网易云音乐等未核实到同一套官方固定 LUFS/dBTP；使用可追溯的通用音乐母带参考，不宣称满足该平台专属标准。",
    ),
    "short_video_mobile_reference": DeliveryProfile(
        "short_video_mobile_reference", "短视频移动端响度参考（非抖音平台标准）", -15, -1,
        "https://www.nrta.gov.cn/module/download/downfile.jsp?classid=0&filename=0e71703f4538412db1a08f2089101dda.pdf",
        "借用中国网络视听嘈杂接收环境的音频参数作为移动端工作参考；抖音未公布同一套固定母带数值，不代表抖音验收标准。",
    ),
    "spotify": DeliveryProfile(
        "spotify", "Spotify 母带建议", -14, -1,
        "https://support.spotify.com/bj-en/artists/article/loudness-normalization/",
        "官方母带建议；不是 Spotify 播放端响度处理的认证。",
        louder_true_peak_dbtp=-2,
    ),
    "soundcloud": DeliveryProfile(
        "soundcloud", "SoundCloud 母带建议", -14, -1,
        "https://help.soundcloud.com/hc/en-us/articles/360053660014-Will-SoundCloud-play-my-track-at-the-level-it-s-mastered",
        "官方母带建议；不包含平台上传格式的完整验证。",
        louder_true_peak_dbtp=-2,
    ),
    "apple_podcasts": DeliveryProfile(
        "apple_podcasts", "Apple Podcasts 响度建议", -16, -1,
        "https://podcasters.apple.com/support/893-audio-requirements",
        "仅对应音频响度与真峰值建议；当前仍导出 WAV。",
    ),
    "ebu_r128": DeliveryProfile(
        "ebu_r128", "EBU R 128 节目响度参考", -23, -1,
        "https://tech.ebu.ch/files/live/sites/tech/files/shared/r/r128.pdf",
        "仅核对综合响度与真峰值；未认证响度范围、元数据或分发链。",
    ),
    "bbc_tv": DeliveryProfile(
        "bbc_tv", "BBC/DPP 电视响度参考", -23, -1,
        "https://downloads.bbc.co.uk/scotland/commissioning/TechnicalDeliveryStandardsBBCFile.pdf",
        "仅核对响度与真峰值；不生成 AS-11 文件或节目元数据。",
    ),
    "cn_digital_tv": DeliveryProfile(
        "cn_digital_tv", "中国数字电视 GY/T 282—2014", -24, -2,
        "https://www.nrta.gov.cn/module/download/downfile.jsp?classid=0&filename=d31ca72b07b042d883c165df58d40820.pdf",
        "仅核对完整音频的平均响度与真峰值；机构另有交付要求时以其要求为准。",
    ),
    "cn_network_av_noisy": DeliveryProfile(
        "cn_network_av_noisy", "中国网络视听 GY/T 377—2023（嘈杂环境版）", -15, -1,
        "https://www.nrta.gov.cn/module/download/downfile.jsp?classid=0&filename=0e71703f4538412db1a08f2089101dda.pdf",
        "适用于车载、户外等嘈杂接收环境；仅核对音频响度与真峰值。",
    ),
    "cn_network_av_quiet": DeliveryProfile(
        "cn_network_av_quiet", "中国网络视听 GY/T 377—2023（安静环境版）", -24, -1,
        "https://www.nrta.gov.cn/module/download/downfile.jsp?classid=0&filename=0e71703f4538412db1a08f2089101dda.pdf",
        "适用于安静接收环境；仅核对音频响度与真峰值。",
    ),
    "cn_network_av_custom": DeliveryProfile(
        "cn_network_av_custom", "中国网络视听：客户自定响度", None, -1,
        "https://www.nrta.gov.cn/module/download/downfile.jsp?classid=0&filename=0e71703f4538412db1a08f2089101dda.pdf",
        "客户响度不是 GY/T 377 的 -15/-24 LKFS 两种默认场景之一；只沿用同规范的真峰值参考，不声称符合其预设版本。",
    ),
    "atsc_a85_short": DeliveryProfile(
        "atsc_a85_short", "ATSC A/85:2026-07 短节目参考", -24, -2,
        "https://www.atsc.org/wp-content/uploads/2026/07/A85-2026-07-Annex-M.pdf",
        "仅用于短节目全节目响度；长节目对白门控与元数据不在本链路能力内。",
    ),
}


_OTHER_PLATFORMS = re.compile(
    r"youtube|netflix|tiktok|优酷|爱奇艺|腾讯视频|bilibili|哔哩哔哩|b站|"
    r"院线|电影院|电影公映|影院",
    re.I,
)


def resolve_profile(brief: str, explicit_target: float | None, explicit_true_peak: float | None) -> DeliveryProfile | None:
    """Select exactly one named, supported profile; never mix platform values."""
    text = brief.lower()
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

    network_av = bool(re.search(r"gy\s*/?\s*t\s*377|网络视听|中国网络视频", text, re.I))
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
    if not found and re.search(r"抖音|douyin|短视频", text, re.I):
        found.append(PROFILES["short_video_mobile_reference"])
    if not found and re.search(r"音乐流媒体|流媒体|串流|streaming|音乐平台", text, re.I) and not _OTHER_PLATFORMS.search(text):
        found.append(PROFILES["music_streaming"])

    if len(found) > 1 or (_OTHER_PLATFORMS.search(text) and found):
        raise ValueError("交付要求中提到多个不同规范或平台，请选择一套标准；不会拼接不同平台的参数。")
    if found:
        return found[0]

    if _OTHER_PLATFORMS.search(text) and (explicit_target is None or explicit_true_peak is None):
        raise ValueError("该平台没有可在当前单音频链路核实并自动补齐的完整响度/真峰值预设；请同时给出 LUFS 与 dBTP。")
    return None
