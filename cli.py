from dotenv import load_dotenv
load_dotenv()

import argparse
import os
from pathlib import Path

from core.job import load_audio
from core.analyzer import analyze
from core.agent import decide, decide_mix
from core.mixer import mix_tracks
from core.processor import process
from core.schemas import LimiterSettings
from core.writer import write


def _master_pipeline(job, bit_depth):
    """Analyze (if needed) → mastering decisions → process with true-peak retry → write."""
    job = decide(job)

    for attempt in range(2):
        job = process(job)
        if job.true_peak_dbtp <= job.dsp_decisions.limiter.ceiling_dbtp + 0.1:
            break
        if attempt < 1:
            old = job.dsp_decisions.limiter
            job.dsp_decisions.limiter = LimiterSettings(
                ceiling_dbtp=max(old.ceiling_dbtp - 1.0, -24.0),
                release_ms=old.release_ms,
            )
            job.processed_audio = None
            job.status = "pending"

    write(job, bit_depth=bit_depth)
    return job


def main():
    parser = argparse.ArgumentParser(
        prog="mixmaster",
        description="AI-driven audio mastering CLI",
    )

    parser.add_argument(
        "input",
        type=str,
        help="Path to the input audio file (WAV, FLAC, AIFF, MP3, OGG). "
             "In mix+master mode this is the vocal file.",
    )
    parser.add_argument(
        "output",
        type=str,
        help="Path for the output audio file",
    )
    parser.add_argument(
        "prompt",
        type=str,
        help="Creative brief (e.g. 'warm master for streaming')",
    )
    parser.add_argument(
        "--instrumental",
        type=str,
        default=None,
        dest="instrumental",
        help="Path to instrumental audio file. When provided, runs mix+master mode.",
    )
    parser.add_argument(
        "--bit-depth",
        type=int,
        choices=[16, 24, 32],
        default=24,
        dest="bit_depth",
        help="Output bit depth (default: 24)",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        dest="api_key",
        help="Anthropic API key (overrides ANTHROPIC_API_KEY env var)",
    )

    args = parser.parse_args()

    if args.api_key is not None:
        os.environ["ANTHROPIC_API_KEY"] = args.api_key

    input_path = Path(args.input)
    output_path = Path(args.output)

    if args.instrumental is None:
        # --- Mode 1: master only (existing behavior) ---
        job = load_audio(input_path, output_path, args.prompt)
        job = analyze(job)
        job = _master_pipeline(job, args.bit_depth)

        print(f"✓ Output:      {job.output_path}")
        print(f"✓ Loudness:    {job.loudness_lufs:.1f} LUFS")
        print(f"✓ True peak:   {job.true_peak_dbtp:.1f} dBTP")
        print(f"✓ Bit depth:   {args.bit_depth}-bit")
        print(f"✓ Reasoning:   {job.dsp_decisions.reasoning}")

    else:
        # --- Mode 2: mix + master ---
        vocal_path = input_path
        instr_path = Path(args.instrumental)

        vocal_job = load_audio(vocal_path, output_path, args.prompt)
        instr_job = load_audio(instr_path, output_path, args.prompt)

        # Analyze vocal → mixing decisions
        vocal_job = analyze(vocal_job)
        vocal_job = decide_mix(vocal_job)

        # Mix vocal + instrumental into one stereo array
        mixed_audio = mix_tracks(
            vocal_job.audio,
            instr_job.audio,
            vocal_job.sample_rate,
            vocal_job.mix_decisions,
        )

        # Replace audio on the job with the mix, re-analyze for mastering
        vocal_job.audio = mixed_audio
        vocal_job.num_channels = mixed_audio.shape[0]
        vocal_job.duration_seconds = mixed_audio.shape[1] / vocal_job.sample_rate
        vocal_job.analysis = {}
        vocal_job = analyze(vocal_job)

        # Master the mix
        vocal_job = _master_pipeline(vocal_job, args.bit_depth)

        print(f"✓ Output:      {vocal_job.output_path}")
        print(f"✓ Loudness:    {vocal_job.loudness_lufs:.1f} LUFS")
        print(f"✓ True peak:   {vocal_job.true_peak_dbtp:.1f} dBTP")
        print(f"✓ Bit depth:   {args.bit_depth}-bit")
        print(f"✓ Mix:         {vocal_job.mix_decisions.reasoning}")
        print(f"✓ Master:      {vocal_job.dsp_decisions.reasoning}")


if __name__ == "__main__":
    main()
