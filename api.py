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
        return None, f"处理失败：{str(e)}"

    lines = []
    spec = job.delivery_spec
    if spec is not None:
        if spec.profile_name:
            lines.append(f"选用依据：{spec.profile_basis_kind}｜{spec.profile_name}。仅核对当前音频链支持的数值，不代表完整平台验收。")
            if spec.profile_note:
                lines.append(f"适用边界：{spec.profile_note}")
            if spec.profile_source_url:
                lines.append(f"参考数值的原始来源：{spec.profile_source_url}")
        targets = []
        if spec.target_lufs is not None:
            targets.append(f"{spec.target_lufs:g} LUFS（{spec.loudness_origin}）")
        if spec.max_true_peak_dbtp is not None:
            targets.append(f"真峰值不超过 {spec.max_true_peak_dbtp:g} dBTP（{spec.true_peak_origin}）")
        if spec.max_sample_peak_dbfs is not None:
            targets.append(f"采样峰值不超过 {spec.max_sample_peak_dbfs:g} dBFS")
        if targets:
            lines.append("交付目标：" + "；".join(targets))
    lines.extend([
        f"✓ 导出综合响度：{job.loudness_lufs:.1f} LUFS",
        f"✓ 导出采样峰值：{job.output_sample_peak_dbfs:.1f} dBFS",
        f"✓ 导出真峰值（4×估计）：{job.true_peak_dbtp:.1f} dBTP",
        f"✓ 导出格式：{job.output_sample_rate} Hz / {job.output_channels} 声道 / {job.output_bit_depth}-bit WAV",
    ])
    applied = []
    if job.dsp_decisions.de_esser.enabled:
        deess = job.dsp_decisions.de_esser
        applied.append(f"动态齿音控制 {deess.center_hz:g} Hz，最大衰减 {deess.max_reduction_db:g} dB")
    for band in job.dsp_decisions.tonal_eq.bands:
        if band.filter_type == "high_shelf" and band.gain_db:
            applied.append(f"高架 EQ {band.frequency:g} Hz / {band.gain_db:+g} dB")
    if applied:
        lines.append("已执行听感处理：" + "；".join(applied) + "。请试听确认。")
    if job.output_is_dual_mono:
        lines.append("说明：输入为单声道；为满足立体声文件要求，左右声道使用相同信号（双单声道），没有新增立体声空间信息。")
    if job.mix_decisions:
        lines.append(f"\n贴唱混音决策：\n{job.mix_decisions.reasoning}")
    lines.append(f"\n母带处理决策：\n{job.dsp_decisions.reasoning}")

    return str(output_path), "\n".join(lines)


with gr.Blocks(title="MixMaster AI") as demo:
    gr.Markdown(
        "# MixMaster AI\n"
        "基于大模型声学分析的自动化混音与母带引擎。\n"
        "上传音频并输入需求，AI 将自动串联 EQ、压缩、饱和度等 DSP 链路并完成渲染。\n\n"
        "💡 **工作模式：**\n"
        "1. 单轨母带：仅传「主音频」，对上传的音频进行最终响度与频段标准化。\n"
        "2. 贴唱混音：同传「干声」与「伴奏」，自动执行人声混音并做整体母带融合。"
    )

    with gr.Row():
        with gr.Column():
            gr.Markdown("**主音频**  \n请上传混音成品或人声干声。母带模式请上传完整混音；贴唱混音模式请上传人声。")
            audio_input = gr.Audio(
                type="filepath",
                label="主音频",
            )
            with gr.Accordion(label="伴奏（可选）", open=False):
                gr.Markdown("上传伴奏后自动触发“贴唱混音”模式。若只需对单一音轨做母带处理，请留空。")
                instrumental_input = gr.Audio(
                    type="filepath",
                    label="伴奏",
                )
            prompt_input = gr.Textbox(
                label="声音要求",
                placeholder="例如：按流媒体参考预设输出；提升人声清晰度；或明确指定 -14 LUFS、真峰值 -1 dBTP",
                info="AI对话，用自然语言描述目标听感或技术指标。",
            )
            bit_depth_input = gr.Radio(
                choices=[16, 24, 32],
                value=24,
                label="导出位深",
                info="16-bit：日常试听分发；24-bit：工业级交付（推荐）；32-bit float：供二次后期编辑。",
            )
            gr.Markdown("开始处理。耗时取决于原始文件时长与 GPU 并发队列。")
            master_btn = gr.Button("开始处理", variant="primary")

        with gr.Column():
            gr.Markdown("**输出音频**  \n渲染完成，可在此进行原片与母带版本的实时监听对比及无损下载。")
            audio_output = gr.Audio(
                label="输出音频",
            )
            summary_output = gr.Textbox(
                label="处理说明",
                lines=12,
                info="展示大模型调用各级 DSP 插件的决策逻辑，及处理前后 LUFS、True Peak 等核心测算数据。",
            )

    master_btn.click(
        fn=gradio_master,
        inputs=[audio_input, prompt_input, bit_depth_input, instrumental_input],
        outputs=[audio_output, summary_output],
    )

app = gr.mount_gradio_app(app, demo, path="/")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7860)
