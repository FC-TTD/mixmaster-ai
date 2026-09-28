"""Explicit delivery requirements from a client brief.

The LLM chooses creative DSP settings; technical file constraints are parsed and
verified in code so an unsupported promise cannot become a successful export.
"""
from dataclasses import dataclass
import re

from core.delivery_profiles import resolve_profile


_NUMBER = r"([+-]?\d+(?:\.\d+)?)"


@dataclass(frozen=True)
class DeliverySpec:
    profile_id: str | None = None
    profile_name: str | None = None
    profile_basis_kind: str | None = None
    profile_source_url: str | None = None
    profile_note: str | None = None
    loudness_origin: str | None = None
    true_peak_origin: str | None = None
    sample_rate_hz: int | None = None
    channels: int | None = None
    bit_depth: int | None = None
    max_sample_peak_dbfs: float | None = None
    max_true_peak_dbtp: float | None = None
    target_lufs: float | None = None


def _single(values: list[float], name: str) -> float | None:
    if not values:
        return None
    if any(value != values[0] for value in values[1:]):
        raise ValueError(f"交付要求中{name}有互相冲突的数值，请明确一个目标。")
    return values[0]


def parse_delivery_spec(brief: str) -> DeliverySpec:
    text = brief.replace("−", "-").replace("–", "-").replace("—", "-")
    if re.search(r"(?:5\.1|7\.1)\s*(?:声道|surround)|杜比全景声|dolby\s*atmos", text, re.I):
        raise ValueError("当前仅支持单声道或立体声 WAV，不能交付环绕声或 Dolby Atmos。")
    if re.search(r"(?:输出|导出|交付|export)\s*(?:为|成|as)?\s*(?:MP3|AAC|FLAC)\b", text, re.I):
        raise ValueError("当前只能导出 WAV；不能按要求交付 MP3、AAC 或 FLAC。")
    if re.search(r"32\s*(?:-|\s)?\s*(?:bit|位)\s*PCM", text, re.I):
        raise ValueError("当前 32-bit 导出为 float WAV，不支持 32-bit 整数 PCM。")
    if re.search(r"\bITU[- ]?R\s*BS\.?1770\b", text, re.I) and not re.search(r"EBU\s*R\s*128|ATSC\s*A\s*/?\s*85", text, re.I):
        raise ValueError("ITU-R BS.1770 是测量算法，未规定单一交付响度；请指定平台、交付规范或 LUFS 与 dBTP。")
    rates = []
    for match in re.finditer(rf"(?<![\d.]){_NUMBER}\s*(k(?:hz|赫兹)|hz|赫兹|千赫)(?!\w)", text, re.I):
        rate = float(match.group(1)) * (1000 if match.group(2).lower().startswith("k") or match.group(2) == "千赫" else 1)
        rates.append(rate)
    rate = _single(rates, "采样率")
    if rate is not None and (rate != int(rate) or not 8000 <= rate <= 192000):
        raise ValueError(f"不支持的采样率 {rate:g} Hz；支持 8–192 kHz 的整数采样率。")

    bit_values = [float(m.group(1)) for m in re.finditer(rf"(?<![\d.]){_NUMBER}\s*(?:-|\s)?\s*(?:bit|位)(?!\w)", text, re.I)]
    bit = _single(bit_values, "位深")
    if bit is not None and bit not in (16, 24, 32):
        raise ValueError(f"不支持的导出位深 {bit:g}；仅支持 16-bit PCM、24-bit PCM 和 32-bit float WAV。")

    channels = []
    if re.search(r"立体声|stereo|双声道", text, re.I):
        channels.append(2.0)
    if re.search(r"单声道|\bmono\b", text, re.I):
        channels.append(1.0)
    channel = _single(channels, "声道")

    sample_peaks = [float(m.group(1)) for m in re.finditer(rf"{_NUMBER}\s*dBFS\b", text, re.I)]
    true_peaks = [float(m.group(1)) for m in re.finditer(rf"{_NUMBER}\s*dBTP\b", text, re.I)]
    loudness = [float(m.group(1)) for m in re.finditer(rf"{_NUMBER}\s*(?:LUFS|LKFS)\b", text, re.I)]
    sample_peak = _single(sample_peaks, "dBFS 峰值")
    true_peak = _single(true_peaks, "dBTP 真峰值")
    target = _single(loudness, "LUFS 响度")
    for label, value in (("dBFS 峰值", sample_peak), ("dBTP 真峰值", true_peak)):
        if value is not None and not -60 <= value <= 0:
            raise ValueError(f"{label} {value:g} 超出可用的 -60 至 0 dB 范围。")
    if target is not None and not -40 <= target <= -6:
        raise ValueError(f"目标响度 {target:g} LUFS 超出可用的 -40 至 -6 LUFS 范围。")

    loudness_origin = "客户指定" if target is not None else None
    true_peak_origin = "客户指定" if true_peak is not None else None
    profile = resolve_profile(text, target, true_peak)
    if profile:
        if target is None:
            target = profile.target_lufs
            if target is not None:
                loudness_origin = profile.basis_kind
        if true_peak is None:
            true_peak = (
                profile.louder_true_peak_dbtp
                if profile.louder_true_peak_dbtp is not None
                and profile.target_lufs is not None
                and target > profile.target_lufs
                else profile.max_true_peak_dbtp
            )
            true_peak_origin = profile.basis_kind

    return DeliverySpec(
        profile_id=profile.key if profile else None,
        profile_name=profile.label if profile else None,
        profile_basis_kind=profile.basis_kind if profile else None,
        profile_source_url=profile.source_url if profile else None,
        profile_note=profile.note if profile else None,
        loudness_origin=loudness_origin,
        true_peak_origin=true_peak_origin,
        sample_rate_hz=int(rate) if rate is not None else None,
        channels=int(channel) if channel is not None else None,
        bit_depth=int(bit) if bit is not None else None,
        max_sample_peak_dbfs=sample_peak,
        max_true_peak_dbtp=true_peak,
        target_lufs=target,
    )
