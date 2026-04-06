from dotenv import load_dotenv
load_dotenv()

import argparse
import os
from pathlib import Path

from core.job import load_audio
from core.analyzer import analyze
from core.agent import decide
from core.processor import process
from core.schemas import LimiterSettings
from core.writer import write


def main():
    parser = argparse.ArgumentParser(
        prog="mixmaster",
        description="AI-driven audio mastering CLI",
    )

    parser.add_argument(
        "input",
        type=str,
        help="Path to the input audio file (WAV, FLAC, AIFF, MP3, OGG)",
    )
    parser.add_argument(
        "output",
        type=str,
        help="Path for the output audio file",
    )
    parser.add_argument(
        "prompt",
        type=str,
        help="Creative brief for the mastering engineer (e.g. 'warm master for streaming')",
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

    job = load_audio(Path(args.input), Path(args.output), args.prompt)
    job = analyze(job)

    job = decide(job)

    for attempt in range(2):
        job = process(job)
        if job.true_peak_dbtp <= job.dsp_decisions.limiter.ceiling_dbtp + 0.1:
            break
        if attempt < 1:
            old = job.dsp_decisions.limiter
            job.dsp_decisions.limiter = LimiterSettings(
                ceiling_dbtp=max(old.ceiling_dbtp - 1.0, -3.0),
                release_ms=old.release_ms
            )
            job.processed_audio = None
            job.status = "pending"

    write(job, bit_depth=args.bit_depth)

    print(f"✓ Output:      {job.output_path}")
    print(f"✓ Loudness:    {job.loudness_lufs:.1f} LUFS")
    print(f"✓ True peak:   {job.true_peak_dbtp:.1f} dBTP")
    print(f"✓ Bit depth:   {args.bit_depth}-bit")
    print(f"✓ Reasoning:   {job.dsp_decisions.reasoning}")


if __name__ == "__main__":
    main()
