from dotenv import load_dotenv
load_dotenv()

import os
import uuid
import tempfile
import shutil
from pathlib import Path

import numpy as np
import gradio as gr
import soundfile as sf
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
import uvicorn

from core.job import load_audio
from core.analyzer import analyze
from core.agent import decide, decide_mix
from core.mixer import mix_tracks
from core.processor import process
from core.writer import write


app = FastAPI(title="MixMaster AI", version="1.0.0")


# ---------------------------------------------------------------------------
# Shared pipeline helpers
# ---------------------------------------------------------------------------

def _run_master(input_path: Path, output_path: Path, prompt: str, bit_depth: int):
    """Mode 1 — master only."""
    job = load_audio(input_path, output_path, prompt)
    job = analyze(job)
    job = decide(job)
    job = process(job)
    write(job, bit_depth=bit_depth)
    return job


def _run_mix_and_master(
    vocal_path: Path,
    instr_path: Path,
    output_path: Path,
    prompt: str,
    bit_depth: int,
):
    """Mode 2 — mix vocal + instrumental, then master."""
    vocal_job = load_audio(vocal_path, output_path, prompt)
    instr_job = load_audio(instr_path, output_path, prompt)

    vocal_job = analyze(vocal_job)
    vocal_job = decide_mix(vocal_job)

    mixed_audio = mix_tracks(
        vocal_job.audio,
        instr_job.audio,
        vocal_job.sample_rate,
        vocal_job.mix_decisions,
    )

    vocal_job.audio = mixed_audio
    vocal_job.num_channels = mixed_audio.shape[0]
    vocal_job.duration_seconds = mixed_audio.shape[1] / vocal_job.sample_rate
    vocal_job.analysis = {}
    vocal_job = analyze(vocal_job)

    vocal_job = decide(vocal_job)
    vocal_job = process(vocal_job)
    write(vocal_job, bit_depth=bit_depth)
    return vocal_job


# ---------------------------------------------------------------------------
# REST endpoints
# ---------------------------------------------------------------------------

@app.post("/master")
async def master_audio(
    file: UploadFile = File(...),
    prompt: str = Form(...),
    bit_depth: int = Form(24),
):
    if bit_depth not in (16, 24, 32):
        raise HTTPException(
            status_code=400,
            detail=f"bit_depth must be 16, 24, or 32. Got: {bit_depth}",
        )

    tmp_dir = Path(tempfile.mkdtemp())
    original_name = Path(file.filename) if file.filename else Path("audio.wav")
    input_path = tmp_dir / f"input{original_name.suffix or '.wav'}"
    output_path = tmp_dir / f"mastered_{original_name.stem}.wav"

    with open(input_path, "wb") as f:
        f.write(await file.read())

    try:
        job = _run_master(input_path, output_path, prompt, bit_depth)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return FileResponse(
        path=str(output_path),
        media_type="audio/wav",
        filename=output_path.name,
    )


@app.post("/mix-and-master")
async def mix_and_master_audio(
    vocal: UploadFile = File(...),
    instrumental: UploadFile = File(...),
    prompt: str = Form(...),
    bit_depth: int = Form(24),
):
    if bit_depth not in (16, 24, 32):
        raise HTTPException(
            status_code=400,
            detail=f"bit_depth must be 16, 24, or 32. Got: {bit_depth}",
        )

    tmp_dir = Path(tempfile.mkdtemp())

    vocal_name = Path(vocal.filename) if vocal.filename else Path("vocal.wav")
    instr_name = Path(instrumental.filename) if instrumental.filename else Path("instr.wav")

    vocal_path = tmp_dir / f"vocal{vocal_name.suffix or '.wav'}"
    instr_path = tmp_dir / f"instrumental{instr_name.suffix or '.wav'}"
    output_path = tmp_dir / f"mixed_mastered_{vocal_name.stem}.wav"

    with open(vocal_path, "wb") as f:
        f.write(await vocal.read())
    with open(instr_path, "wb") as f:
        f.write(await instrumental.read())

    try:
        job = _run_mix_and_master(vocal_path, instr_path, output_path, prompt, bit_depth)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return FileResponse(
        path=str(output_path),
        media_type="audio/wav",
        filename=output_path.name,
    )


# ---------------------------------------------------------------------------
# Gradio UI
# ---------------------------------------------------------------------------

def gradio_master(
    audio_path: str,
    prompt: str,
    bit_depth: int,
    instrumental_path: str | None,
) -> tuple:
    tmp_dir = Path(tempfile.mkdtemp())
    input_path = Path(audio_path)
    output_path = tmp_dir / f"mastered_{input_path.stem}.wav"

    try:
        if instrumental_path:
            instrument_input_path = instrumental_path
            if isinstance(instrumental_path, tuple):
                instrumental_sample_rate, instrumental_audio = instrumental_path
                instrument_input_path = tmp_dir / "instrumental_gradio.wav"
                sf.write(str(instrument_input_path), instrumental_audio, instrumental_sample_rate)
            job = _run_mix_and_master(
                input_path, Path(instrument_input_path), output_path, prompt, int(bit_depth)
            )
        else:
            job = _run_master(input_path, output_path, prompt, int(bit_depth))
    except Exception as e:
        return None, f"❌ Error: {str(e)}"

    lines = [
        f"✓ Loudness:   {job.loudness_lufs:.1f} LUFS",
        f"✓ True peak:  {job.true_peak_dbtp:.1f} dBTP",
        f"✓ Bit depth:  {int(bit_depth)}-bit",
    ]
    if job.mix_decisions:
        lines.append(f"\nMix Reasoning:\n{job.mix_decisions.reasoning}")
    lines.append(f"\nMaster Reasoning:\n{job.dsp_decisions.reasoning}")

    return str(output_path), "\n".join(lines)


with gr.Blocks(title="MixMaster AI") as demo:
    gr.Markdown("# 🎚️ MixMaster AI\nAI-powered audio mixing and mastering")

    with gr.Row():
        with gr.Column():
            audio_input = gr.Audio(
                type="filepath",
                label="Upload Audio (or Vocal for mix+master mode)",
            )
            instrumental_input = gr.Audio(
                type="filepath",
                label="Instrumental (optional — enables mix+master mode)",
            )
            prompt_input = gr.Textbox(
                label="Creative Brief",
                placeholder="e.g. warm vintage master for streaming",
            )
            bit_depth_input = gr.Radio(
                choices=[16, 24, 32],
                value=24,
                label="Bit Depth",
            )
            master_btn = gr.Button("Master", variant="primary")

        with gr.Column():
            audio_output = gr.Audio(label="Mastered Audio")
            summary_output = gr.Textbox(label="AI Reasoning", lines=12)

    master_btn.click(
        fn=gradio_master,
        inputs=[audio_input, prompt_input, bit_depth_input, instrumental_input],
        outputs=[audio_output, summary_output],
    )

app = gr.mount_gradio_app(app, demo, path="/")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7860)
