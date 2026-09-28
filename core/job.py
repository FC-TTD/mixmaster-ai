import uuid
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from core.schemas import DSPDecisions, MixDecisions
from core.delivery import DeliverySpec


@dataclass
class Job:
    input_path: Path
    output_path: Path
    prompt: str
    sample_rate: int
    num_channels: int
    duration_seconds: float
    audio: np.ndarray
    job_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    analysis: dict = field(default_factory=dict)
    dsp_decisions: DSPDecisions | None = None
    mix_decisions: MixDecisions | None = None
    processed_audio: np.ndarray | None = None
    loudness_lufs: float | None = None
    true_peak_dbtp: float | None = None
    delivery_spec: DeliverySpec | None = None
    output_sample_rate: int | None = None
    output_bit_depth: int | None = None
    output_sample_peak_dbfs: float | None = None
    status: str = "pending"
    error: str | None = None


def load_audio(input_path: Path, output_path: Path, prompt: str) -> Job:
    audio = None
    sample_rate = None

    try:
        import soundfile as sf
        audio, sample_rate = sf.read(input_path, dtype="float32", always_2d=True)
        # soundfile returns (samples, channels) — transpose to (channels, samples)
        audio = audio.T
    except Exception:
        try:
            from pedalboard.io import AudioFile
            with AudioFile(str(input_path)) as f:
                audio = f.read(f.frames)  # returns (channels, samples) float32
                sample_rate = f.samplerate
        except Exception:
            raise ValueError(
                f"Cannot load audio file: {input_path}. "
                "Supported formats: WAV, AIFF, FLAC, MP3, OGG."
            )

    audio = audio.astype(np.float32)

    if audio.ndim == 1:
        audio = audio.reshape(1, len(audio))

    num_channels = audio.shape[0]
    num_samples = audio.shape[1]
    duration_seconds = num_samples / sample_rate

    return Job(
        input_path=input_path,
        output_path=output_path,
        prompt=prompt,
        sample_rate=sample_rate,
        num_channels=num_channels,
        duration_seconds=duration_seconds,
        audio=audio,
    )
