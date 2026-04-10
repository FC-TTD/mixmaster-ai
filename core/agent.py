import os
import json
import anthropic
import numpy as np
from core.job import Job
from core.schemas import DSPDecisions, MixDecisions


def decide(job: Job) -> Job:
    job.status = "processing"

    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    tool = {
        "name": "set_dsp_decisions",
        "description": "Set all DSP processing parameters for the audio mastering chain.",
        "input_schema": DSPDecisions.model_json_schema(),
    }

    system_prompt = (
        "You are a professional audio mastering engineer with 20 years of experience.\n"
        "You will receive measured audio analysis data and a client's creative brief.\n"
        "Your job is to set precise DSP parameters for a mastering chain.\n"
        "\n"
        "The chain order is: corrective EQ → compressor → tonal EQ → saturator → stereo imager → limiter.\n"
        "\n"
        "Rules:\n"
        "- corrective_eq fixes technical problems (resonances, mud, harshness)\n"
        "- tonal_eq shapes the creative character (warmth, air, presence)\n"
        "- Set target_lufs based on the destination: -14 for streaming, -9 for club, -23 for broadcast\n"
        "- If integrated_lufs is already close to target (within 2 LU), use gentle compression\n"
        "- If crest_factor_db < 6, the audio is already compressed — use low ratio (1.5-2.0)\n"
        "- If stereo_width > 1.5, do not widen further\n"
        "- If low_end_mono_compatibility > 0.3, keep mono_low_hz above 100Hz\n"
        "- Always provide reasoning explaining your decisions"
    )

    analysis_str = "\n".join(
        f"  {k}: {v:.6f}" for k, v in job.analysis.items()
    )

    user_message = (
        f"CLIENT BRIEF: {job.prompt}\n"
        "\n"
        "AUDIO ANALYSIS:\n"
        f"{analysis_str}\n"
        "\n"
        "Call set_dsp_decisions with appropriate mastering parameters."
    )

    try:
        response = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=4096,
            temperature=0.2,
            system=system_prompt,
            tools=[tool],
            tool_choice={"type": "tool", "name": "set_dsp_decisions"},
            messages=[{"role": "user", "content": user_message}],
        )

        if not hasattr(response, "content") or not response.content:
            raise ValueError("Empty response from Claude API")

        tool_blocks = [b for b in response.content if b.type == "tool_use"]
        if not tool_blocks:
            raise ValueError("No tool_use block returned by Claude")
        tool_use_block = tool_blocks[-1]
        tool_name = getattr(tool_use_block, "name", None)
        if not isinstance(tool_name, str):
            tool_name = "set_dsp_decisions"
        if tool_name != "set_dsp_decisions":
            raise ValueError(f"Unexpected tool called: {tool_name}")

        decisions = DSPDecisions.model_validate(tool_use_block.input)
        job.dsp_decisions = decisions

    except Exception as e:
        job.status = "error"
        job.error = str(e)
        raise

    return job


def decide_mix(job: Job) -> Job:
    job.status = "processing"

    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    tool = {
        "name": "set_mix_decisions",
        "description": "Set all mixing parameters for blending a vocal with an instrumental track.",
        "input_schema": MixDecisions.model_json_schema(),
    }

    system_prompt = (
        "You are a professional mixing engineer with 20 years of experience in vocal production.\n"
        "You will receive measured audio analysis data and a client's creative brief.\n"
        "Your job is to set precise mixing parameters to blend a vocal with an instrumental backing track.\n"
        "\n"
        "The mixing chain order is: noise gate → transient shaper → channel EQ → compression → reverb → delay → panning → blend.\n"
        "\n"
        "Rules:\n"
        "- If vocal RMS is more than 12dB below instrumental RMS, compensate with a positive vocal_gain_db\n"
        "- If spectral centroid of the vocal clashes with the instrumental mid range (300–3000 Hz), apply a channel EQ cut in that region\n"
        "- reverb wet_mix must not exceed 0.35 for intimate or close vocal styles (spoken word, whisper, confessional)\n"
        "- delay must be disabled (enabled: false) unless the prompt explicitly requests echo or delay\n"
        "- vocal_pan must always be 0.0 (center); use instrumental_gain_db for level balance only\n"
        "- Always provide reasoning explaining your decisions"
    )

    analysis_str = "\n".join(
        f"  {k}: {v:.6f}" for k, v in job.analysis.items()
    )

    user_message = (
        f"CLIENT BRIEF: {job.prompt}\n"
        "\n"
        "VOCAL AUDIO ANALYSIS:\n"
        f"{analysis_str}\n"
        "\n"
        "Call set_mix_decisions with appropriate mixing parameters."
    )

    try:
        response = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=4096,
            temperature=0.3,
            system=system_prompt,
            tools=[tool],
            tool_choice={"type": "tool", "name": "set_mix_decisions"},
            messages=[{"role": "user", "content": user_message}],
        )

        if not hasattr(response, "content") or not response.content:
            raise ValueError("Empty response from Claude API")

        tool_blocks = [b for b in response.content if b.type == "tool_use"]
        if not tool_blocks:
            raise ValueError("No tool_use block returned by Claude")
        tool_use_block = tool_blocks[-1]
        tool_name = getattr(tool_use_block, "name", None)
        if not isinstance(tool_name, str):
            tool_name = "set_mix_decisions"
        if tool_name != "set_mix_decisions":
            raise ValueError(f"Unexpected tool called: {tool_name}")

        decisions = MixDecisions.model_validate(tool_use_block.input)
        job.mix_decisions = decisions

    except Exception as e:
        job.status = "error"
        job.error = str(e)
        raise

    return job
