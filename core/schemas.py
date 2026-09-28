from typing import Literal
from pydantic import BaseModel, Field


class EQBand(BaseModel):
    frequency: float = Field(..., ge=20.0, le=20000.0)
    gain_db: float = Field(..., ge=-18.0, le=6.0)
    q: float = Field(..., ge=0.1, le=10.0)
    filter_type: Literal["low_shelf", "high_shelf", "peak", "high_pass", "low_pass"]


class EQSettings(BaseModel):
    bands: list[EQBand] = Field(..., max_length=8)
    label: str


class CompressorSettings(BaseModel):
    threshold_db: float = Field(..., ge=-60.0, le=0.0)
    ratio: float = Field(..., ge=1.0, le=20.0)
    attack_ms: float = Field(..., ge=0.1, le=100.0)
    release_ms: float = Field(..., ge=10.0, le=1000.0)
    makeup_gain_db: float = Field(..., ge=0.0, le=24.0)


class SaturatorSettings(BaseModel):
    drive_db: float = Field(..., ge=0.0, le=12.0)
    mix: float = Field(..., ge=0.0, le=1.0)
    mode: Literal["tape", "tube", "clip"]


class StereoImageSettings(BaseModel):
    width: float = Field(..., ge=0.0, le=2.5)
    mono_low_hz: float = Field(..., ge=20.0, le=300.0)


class LimiterSettings(BaseModel):
    ceiling_dbtp: float = Field(..., ge=-24.0, le=0.0, description="Legacy field name: Pedalboard Limiter compression threshold in dB, not a final output ceiling in dBTP.")
    release_ms: float = Field(..., ge=50.0, le=500.0)


class DSPDecisions(BaseModel):
    corrective_eq: EQSettings
    compressor: CompressorSettings
    tonal_eq: EQSettings
    saturator: SaturatorSettings
    stereo_image: StereoImageSettings
    limiter: LimiterSettings
    target_lufs: float = Field(..., ge=-40.0, le=-6.0)
    reasoning: str


class NoiseGateSettings(BaseModel):
    threshold_db: float = Field(-40.0, ge=-80.0, le=0.0)
    attack_ms: float = Field(..., ge=0.1, le=50.0)
    release_ms: float = Field(..., ge=10.0, le=500.0)
    hold_ms: float = Field(0.0, ge=0.0, le=200.0)


class TransientShaperSettings(BaseModel):
    attack_boost_db: float = Field(..., ge=0.0, le=12.0)
    sustain_cut_db: float = Field(0.0, ge=0.0, le=12.0)
    mix: float = Field(1.0, ge=0.0, le=1.0)


class ChannelCompSettings(BaseModel):
    threshold_db: float = Field(..., ge=-60.0, le=0.0)
    ratio: float = Field(..., ge=1.0, le=20.0)
    attack_ms: float = Field(..., ge=0.1, le=100.0)
    release_ms: float = Field(..., ge=10.0, le=1000.0)
    makeup_gain_db: float = Field(..., ge=0.0, le=24.0)


class ReverbSettings(BaseModel):
    room_size: float = Field(..., ge=0.0, le=1.0)
    damping: float = Field(..., ge=0.0, le=1.0)
    wet_mix: float = Field(..., ge=0.0, le=0.5)
    pre_delay_ms: float = Field(0.0, ge=0.0, le=100.0)


class DelaySettings(BaseModel):
    delay_ms: float = Field(..., ge=0.0, le=500.0)
    feedback: float = Field(..., ge=0.0, le=0.8)
    wet_mix: float = Field(..., ge=0.0, le=0.5)
    enabled: bool = False


class MixSettings(BaseModel):
    vocal_gain_db: float = Field(..., ge=-12.0, le=12.0)
    instrumental_gain_db: float = Field(..., ge=-12.0, le=12.0)
    vocal_pan: float = Field(0.0, ge=-1.0, le=1.0)


class MixDecisions(BaseModel):
    noise_gate: NoiseGateSettings
    transient_shaper: TransientShaperSettings
    channel_eq: EQSettings
    channel_comp: ChannelCompSettings
    reverb: ReverbSettings
    delay: DelaySettings
    mix_settings: MixSettings
    reasoning: str
