"""Export a WAV and verify the requirements against its encoded samples."""
from math import gcd
from pathlib import Path

import numpy as np
import pyloudnorm
from pedalboard import Limiter
from scipy.signal import resample_poly
import soundfile as sf

from core.delivery import parse_delivery_spec
from core.job import Job


def _dbfs(peak: float) -> float:
    return float(20 * np.log10(max(peak, np.finfo(np.float64).tiny)))


def _true_peak(audio: np.ndarray) -> float:
    """4x intersample peak estimate, including both channels and chunk edges."""
    highest = 0.0
    length = audio.shape[1]
    for channel in audio:
        for start in range(0, length, 65536):
            left = max(0, start - 64)
            right = min(length, start + 65536 + 64)
            upsampled = resample_poly(channel[left:right], 4, 1)
            trim_left = (start - left) * 4
            trim_right = (right - min(length, start + 65536)) * 4
            middle = upsampled[trim_left:len(upsampled) - trim_right if trim_right else None]
            if middle.size:
                highest = max(highest, float(np.max(np.abs(middle))))
    return _dbfs(highest)


def _cap_peaks(audio: np.ndarray, sample_cap: float, true_cap: float | None) -> np.ndarray:
    """Apply final output gain against the requested sample and true-peak ceilings."""
    reduction = max(0.0, _dbfs(float(np.max(np.abs(audio)))) - sample_cap)
    if true_cap is not None:
        reduction = max(reduction, _true_peak(audio) - true_cap)
    if reduction:
        # Leave room for PCM quantization and the finite 4x true-peak estimate.
        audio = audio * 10 ** (-(reduction + 0.1) / 20.0)
    return audio


def _control_peaks_for_loudness(
    audio: np.ndarray,
    sample_rate: int,
    meter: pyloudnorm.Meter,
    target: float,
    sample_cap: float,
    true_cap: float | None,
) -> np.ndarray:
    """Limit short transients before final gain instead of lowering the whole programme.

    Pedalboard's Limiter threshold controls compression, not the exported peak.
    Its makeup gain can reach 0 dBFS, so the final ceiling is always checked
    and applied independently. Keep the extra drive bounded to protect audio.
    """
    source = audio.astype(np.float32)
    def meter_input(x: np.ndarray) -> np.ndarray:
        return x.T if x.shape[0] == 2 else x[0]

    best: np.ndarray | None = None
    best_error = float("inf")
    for threshold in (-0.3, -3.0, -6.0):
        limiter = Limiter(threshold_db=threshold, release_ms=80.0)

        def render(drive_db: float) -> tuple[np.ndarray, float]:
            driven = source * np.float32(10 ** (drive_db / 20.0))
            limited = limiter.process(driven, sample_rate, reset=True).astype(np.float64)
            capped = _cap_peaks(limited, sample_cap, true_cap)
            loudness = float(meter.integrated_loudness(meter_input(capped)))
            return capped, loudness

        low, high = -6.0, 8.0
        bounds = {}
        for drive in (0.0, low, high):
            candidate, loudness = render(drive)
            bounds[drive] = loudness
            error = abs(loudness - target)
            if error < best_error:
                best, best_error = candidate, error
            if error <= 0.2:
                return candidate
        if bounds[high] < target - 0.25 or bounds[low] > target + 0.25:
            continue
        for _ in range(8):
            middle = (low + high) / 2.0
            candidate, loudness = render(middle)
            error = abs(loudness - target)
            if error < best_error:
                best, best_error = candidate, error
            if error <= 0.2:
                return candidate
            if loudness < target:
                low = middle
            else:
                high = middle
    if best is None:
        raise ValueError("峰值控制后无法测量综合响度。")
    return best


def write(job: Job, bit_depth: int = 24) -> Path:
    if job.processed_audio is None or job.dsp_decisions is None:
        raise ValueError("Run agent.decide(job) and processor.process(job) before write().")
    if bit_depth not in (16, 24, 32):
        raise ValueError(f"bit_depth must be 16, 24, or 32. Got: {bit_depth}")

    spec = job.delivery_spec or parse_delivery_spec(job.prompt)
    bit_depth = spec.bit_depth or bit_depth
    sample_rate = spec.sample_rate_hz or job.sample_rate
    if spec.channels is not None and spec.channels != job.num_channels and not (
        job.num_channels == 1 and spec.channels == 2
    ):
        raise ValueError(
            f"要求 {spec.channels} 声道，但输入是 {job.num_channels} 声道；当前母带链不能可靠地变换声道布局。"
        )
    if job.num_channels not in (1, 2):
        raise ValueError(f"当前仅支持单声道或立体声输入，收到 {job.num_channels} 声道。")

    audio = job.processed_audio.astype(np.float64)
    if sample_rate != job.sample_rate:
        common = gcd(sample_rate, job.sample_rate)
        audio = resample_poly(audio, sample_rate // common, job.sample_rate // common, axis=1)
    dual_mono = job.num_channels == 1 and spec.channels == 2
    if dual_mono:
        # Stereo PCM delivery from a mono source: identical L/R, no invented width.
        audio = np.repeat(audio, 2, axis=0)
    if not np.all(np.isfinite(audio)):
        raise ValueError("处理后的音频包含无效采样值，无法安全导出。")

    meter = pyloudnorm.Meter(sample_rate)
    measured = float(meter.integrated_loudness(audio.T if audio.shape[0] == 2 else audio[0]))
    if not np.isfinite(measured):
        raise ValueError("音频过短或过静，无法测量综合响度。")
    target = spec.target_lufs if spec.target_lufs is not None else job.dsp_decisions.target_lufs
    audio *= 10 ** ((target - measured) / 20.0)

    sample_cap = min(-0.3, spec.max_sample_peak_dbfs if spec.max_sample_peak_dbfs is not None else 0.0)
    true_cap = spec.max_true_peak_dbtp
    capped = _cap_peaks(audio, sample_cap, true_cap)
    capped_lufs = float(meter.integrated_loudness(capped.T if capped.shape[0] == 2 else capped[0]))
    if spec.target_lufs is not None and capped_lufs < target - 0.25:
        audio = _control_peaks_for_loudness(audio, sample_rate, meter, target, sample_cap, true_cap)
    else:
        audio = capped

    if bit_depth == 16:
        lsb = 2.0 / (2 ** bit_depth)
        rng = np.random.default_rng()
        audio += rng.uniform(-lsb, lsb, audio.shape) - rng.uniform(-lsb, lsb, audio.shape)
    subtype = {16: "PCM_16", 24: "PCM_24", 32: "FLOAT"}[bit_depth]
    sf.write(str(job.output_path), audio.T.astype(np.float32), sample_rate, subtype=subtype)

    encoded, actual_rate = sf.read(str(job.output_path), dtype="float32", always_2d=True)
    actual = encoded.T.astype(np.float64)
    actual_peak = _dbfs(float(np.max(np.abs(actual))))
    actual_true_peak = _true_peak(actual)
    actual_lufs = float(meter.integrated_loudness(encoded))
    if not np.isfinite(actual_lufs):
        raise ValueError("导出文件的综合响度无法测量。")
    errors = []
    if actual_rate != sample_rate:
        errors.append("采样率不符")
    if actual.shape[0] != (spec.channels or job.num_channels):
        errors.append("声道数不符")
    if sf.info(str(job.output_path)).subtype != subtype:
        errors.append("编码位深不符")
    if spec.max_sample_peak_dbfs is not None and actual_peak > spec.max_sample_peak_dbfs + 0.01:
        errors.append(f"采样峰值 {actual_peak:.2f} dBFS 超过 {spec.max_sample_peak_dbfs:g} dBFS")
    if true_cap is not None and actual_true_peak > true_cap + 0.05:
        errors.append(f"真峰值 {actual_true_peak:.2f} dBTP 超过 {true_cap:g} dBTP")
    if spec.target_lufs is not None and abs(actual_lufs - target) > 0.25:
        errors.append(
            f"峰值上限与 {target:g} LUFS 目标无法同时达到；实际响度 {actual_lufs:.2f} LUFS"
        )
    if errors:
        job.output_path.unlink(missing_ok=True)
        raise ValueError("交付要求未满足：" + "；".join(errors))

    job.output_sample_rate = actual_rate
    job.output_channels = actual.shape[0]
    job.output_is_dual_mono = dual_mono
    job.output_bit_depth = bit_depth
    job.output_sample_peak_dbfs = actual_peak
    job.true_peak_dbtp = actual_true_peak
    job.loudness_lufs = actual_lufs
    return job.output_path
