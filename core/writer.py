import numpy as np
import soundfile as sf
from pathlib import Path
from core.job import Job


def write(job: Job, bit_depth: int = 24) -> Path:
    if job.processed_audio is None:
        raise ValueError(
            "job.processed_audio is None. Run processor.process(job) before write()."
        )

    if bit_depth not in (16, 24, 32):
        raise ValueError(
            f"bit_depth must be 16, 24, or 32. Got: {bit_depth}"
        )

    target      = job.dsp_decisions.target_lufs
    current     = job.loudness_lufs
    gain_db     = target - current
    gain_linear = 10 ** (gain_db / 20.0)
    audio       = job.processed_audio.astype(np.float64) * gain_linear

    ceiling = 10 ** (-0.3 / 20.0)
    peak    = np.max(np.abs(audio))
    if peak > ceiling:
        audio = audio * (ceiling / peak)

    if bit_depth == 16:
        lsb   = 2.0 / (2 ** bit_depth)
        rng   = np.random.default_rng()
        noise = (
            rng.uniform(-lsb, lsb, audio.shape)
            - rng.uniform(-lsb, lsb, audio.shape)
        )
        audio = audio + noise

    if bit_depth == 16:
        subtype = "PCM_16"
        audio   = audio.astype(np.float32)
    elif bit_depth == 24:
        subtype = "PCM_24"
        audio   = audio.astype(np.float32)
    elif bit_depth == 32:
        subtype = "FLOAT"
        audio   = audio.astype(np.float32)

    sf.write(
        str(job.output_path),
        audio.T,
        job.sample_rate,
        subtype=subtype,
    )
    return job.output_path
