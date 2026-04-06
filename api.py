from dotenv import load_dotenv
load_dotenv()

import os
import uuid
import tempfile
import shutil
from pathlib import Path

import numpy as np
import gradio as gr
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
import uvicorn

from core.job import load_audio
from core.analyzer import analyze
from core.agent import decide
from core.processor import process
from core.writer import write


app = FastAPI(title="MixMaster AI", version="1.0.0")


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
    original_stem = original_name.stem
    original_ext  = original_name.suffix or ".wav"
    input_path    = tmp_dir / f"input{original_ext}"
    output_path   = tmp_dir / f"mastered_{original_stem}.wav"

    with open(input_path, "wb") as f:
        content = await file.read()
        f.write(content)

    try:
        job = load_audio(input_path, output_path, prompt)
        job = analyze(job)
        job = decide(job)
        job = process(job)
        write(job, bit_depth=bit_depth)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return FileResponse(
        path=str(output_path),
        media_type="audio/wav",
        filename=output_path.name,
    )


def gradio_master(
    audio_path: str,
    prompt: str,
    bit_depth: int,
) -> tuple:
    tmp_dir = Path(tempfile.mkdtemp())

    input_path  = Path(audio_path)
    output_path = tmp_dir / f"mastered_{input_path.stem}.wav"

    try:
        job = load_audio(input_path, output_path, prompt)
        job = analyze(job)
        job = decide(job)
        job = process(job)
        write(job, bit_depth=int(bit_depth))
    except Exception as e:
        return None, f"❌ Error: {str(e)}"

    summary = (
        f"✓ Loudness:   {job.loudness_lufs:.1f} LUFS\n"
        f"✓ True peak:  {job.true_peak_dbtp:.1f} dBTP\n"
        f"✓ Bit depth:  {int(bit_depth)}-bit\n"
        f"\nAI Reasoning:\n{job.dsp_decisions.reasoning}"
    )

    return str(output_path), summary


with gr.Blocks(title="MixMaster AI") as demo:
    gr.Markdown("# 🎚️ MixMaster AI\nAI-powered audio mastering")

    with gr.Row():
        with gr.Column():
            audio_input = gr.Audio(
                type="filepath",
                label="Upload Audio",
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
            summary_output = gr.Textbox(label="AI Reasoning", lines=10)

    master_btn.click(
        fn=gradio_master,
        inputs=[audio_input, prompt_input, bit_depth_input],
        outputs=[audio_output, summary_output],
    )

app = gr.mount_gradio_app(app, demo, path="/")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7860)
