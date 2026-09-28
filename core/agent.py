import os
import json
import anthropic
import numpy as np
from openai import OpenAI
from core.job import Job
from core.schemas import DSPDecisions, MixDecisions
from core.delivery import parse_delivery_spec


def _llm_provider() -> str:
    return os.environ.get("LLM_PROVIDER", "anthropic").strip().lower()


def _openai_client() -> OpenAI:
    return OpenAI(
        api_key=os.environ.get("OPENAI_API_KEY") or "EMPTY",
        base_url=os.environ.get("OPENAI_BASE_URL", "http://aiproxy/v1"),
    )


def _extract_json_object(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()

    decoder = json.JSONDecoder()
    for index, char in enumerate(cleaned):
        if char != "{":
            continue
        try:
            parsed, _ = decoder.raw_decode(cleaned[index:])
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            continue
    raise ValueError(f"No JSON object found in model response: {text[:500]}")


def _call_openai_json(system_prompt: str, user_message: str, schema: dict) -> dict:
    model = os.environ.get("OPENAI_MODEL", "gpt-6-luna")
    response = _openai_client().chat.completions.create(
        model=model,
        temperature=float(os.environ.get("OPENAI_TEMPERATURE", "0.1")),
        max_tokens=int(os.environ.get("OPENAI_MAX_TOKENS", "4096")),
        reasoning_effort=os.environ.get("OPENAI_REASONING_EFFORT", "low"),
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    system_prompt
                    + "\n\nReturn exactly one JSON object. Do not wrap it in Markdown. "
                    "The JSON must validate against this schema:\n"
                    + json.dumps(schema, ensure_ascii=False)
                ),
            },
            {"role": "user", "content": user_message},
        ],
    )
    content = response.choices[0].message.content or ""
    return _extract_json_object(content)


def _validated_openai_decision(model_type, system_prompt: str, user_message: str):
    """Give Luna one focused repair opportunity for malformed or invalid JSON."""
    schema = model_type.model_json_schema()
    for attempt in range(2):
        try:
            return model_type.model_validate(_call_openai_json(system_prompt, user_message, schema))
        except ValueError as error:
            if attempt:
                raise
            user_message += (
                "\n\nThe previous response failed schema validation. "
                "Return a complete corrected JSON object only. Error: "
                + str(error)[:1200]
            )


def decide(job: Job) -> Job:
    job.status = "processing"
    job.delivery_spec = parse_delivery_spec(job.prompt)

    system_prompt = """You set mastering parameters for MixMaster AI from a client's brief and measured audio features. You receive numbers, not playable audio or a reference track. Do not claim to have heard the track or locate a specific resonance, sibilance, or distortion from broad measurements alone.

The available mastering chain is corrective EQ → compressor → tonal EQ → saturator → M/S stereo imager → limiter, followed by loudness adjustment during export. Return parameters for every stage using the supplied DSPDecisions schema; use neutral settings or empty EQ bands when processing is not justified.

Interpret the measurements before deciding:
- rms_db is overall level; integrated_lufs is measured loudness; true_peak_dbtp is a peak estimate, not a guarantee about the exported file.
- crest_factor_db and dynamic_range_db describe dynamics. A low crest factor, especially below 6 dB, suggests that further compression may damage punch.
- rms_sub_db, rms_low_db, rms_mid_db, and rms_high_db are energy in broad bands, not a reference tonal curve. spectral_centroid_hz and spectral_flatness are broad descriptors, not detectors of specific faults.
- stereo_width is the input side/mid energy ratio, not the stereo-imager width control. low_end_mono_compatibility is the low-frequency side/mid ratio; a higher value indicates more side energy in the bass. Mono input cannot be widened by this chain.
- integrated_lufs=-70 indicates an unavailable or invalid loudness measurement; do not treat it as a genuine quiet master.

Decision rules:
1. Extract the requested destination, explicit loudness or peak specification, tonal direction, dynamic character, and stereo preference from the client brief. Technical delivery constraints (sample rate, channels, PCM bit depth, maximum sample peak in dBFS, maximum true peak in dBTP) are enforced by the exporter, independently of DSP settings. Never encode a requested -12 dBFS sample-peak limit as limiter.ceiling_dbtp. They have different meanings. The installed Pedalboard Limiter's threshold_db is a compression threshold and is NOT an output ceiling; choose limiter parameters for sound, while the exporter enforces explicit peak limits.
2. Choose target_lufs from an explicit client specification when present and within schema bounds. Otherwise use the original project's -14 LUFS streaming, -9 LUFS club, and -23 LUFS broadcast values only as contextual starting points, not mandatory standards. A television or streaming destination alone does not establish a delivery standard: do not invent a mandatory LUFS or peak value. Reserve aggressive club loudness and broadcast targets for requests that actually call for them. If no destination is given, favor preserving the input's dynamics over arbitrary loudness gain.
3. Use corrective_eq only for a defensible broad correction or an explicitly identified problem. Do not invent a narrow resonance frequency. Use no bands when the data are insufficient. Use tonal_eq for a requested creative direction such as warmth, presence, or air; prefer restrained broad moves over large boosts.
4. Set compressor threshold, ratio, timing, and makeup gain to preserve transients. When measured loudness is within 2 LU of the chosen target, the crest factor is low, or the brief asks for natural dynamics, use gentle or near-neutral compression. Do not use compression to solve every loudness difference.
5. Add saturation only when the brief supports extra density or harmonic color; otherwise set its mix to zero. Keep stereo width near neutral unless the brief and measured stereo data support a change. Do not widen an already very wide signal; if low-frequency side energy is high (ratio above 0.3), set mono_low_hz above 100 Hz.
6. Select a limiter threshold with sensible dynamics. The export stage may change gain and peak level after limiting. Do not promise that the final file will meet target LUFS, sample peak, or true peak without a post-export measurement. If an explicit peak limit conflicts with a loudness target, the peak limit takes priority and the exporter will report the loudness shortfall.

Return one JSON object matching DSPDecisions exactly. Write reasoning in concise Chinese: cite the client's goal and the measurements that drove the main choices, and state any important uncertainty. Do not describe unperformed listening or verification."""

    analysis_str = "\n".join(
        f"  {k}: {v:.6f}" for k, v in job.analysis.items()
    )

    user_message = (
        f"<client_brief>\n{job.prompt}\n</client_brief>\n\n"
        "<input_audio>\n"
        f"sample_rate_hz: {job.sample_rate}\n"
        f"channels: {job.num_channels}\n"
        f"duration_seconds: {job.duration_seconds:.3f}\n"
        "</input_audio>\n\n"
        "<audio_analysis>\n"
        f"{analysis_str}\n"
        "</audio_analysis>\n\n"
        "Select mastering parameters that fit the client brief and measured evidence."
    )

    try:
        if _llm_provider() == "openai":
            decisions = _validated_openai_decision(DSPDecisions, system_prompt, user_message)
        else:
            client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
            tool = {
                "name": "set_dsp_decisions",
                "description": "Set all DSP processing parameters for the audio mastering chain.",
                "input_schema": DSPDecisions.model_json_schema(),
            }
            response = client.messages.create(
                model=os.environ.get("ANTHROPIC_MODEL", "claude-opus-4-5"),
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
        if job.delivery_spec.target_lufs is not None:
            decisions.target_lufs = job.delivery_spec.target_lufs
        job.dsp_decisions = decisions

    except Exception as e:
        job.status = "error"
        job.error = str(e)
        raise

    return job


def decide_mix(job: Job) -> Job:
    job.status = "processing"

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
        "- Always provide reasoning explaining your decisions\n"
        "- The reasoning field must be written in concise Chinese"
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
        if _llm_provider() == "openai":
            decisions = _validated_openai_decision(MixDecisions, system_prompt, user_message)
        else:
            client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
            tool = {
                "name": "set_mix_decisions",
                "description": "Set all mixing parameters for blending a vocal with an instrumental track.",
                "input_schema": MixDecisions.model_json_schema(),
            }
            response = client.messages.create(
                model=os.environ.get("ANTHROPIC_MODEL", "claude-opus-4-5"),
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
