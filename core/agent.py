import os
import json
import anthropic
import numpy as np
from openai import OpenAI
from core.job import Job
from core.schemas import DSPDecisions, MixDecisions, EQBand
from core.delivery import parse_delivery_spec
import re


def _honor_explicit_tone_request(decisions: DSPDecisions, brief: str) -> None:
    """Keep an explicit creative request from disappearing in a neutral LLM plan."""
    deess = bool(re.search(r"齿音(?:过重|太重|重|刺耳|明显|多)|去齿音|压(?:低|制)?齿音|sibilan|de.?ess", brief, re.I))
    brighten = bool(re.search(r"音色太暗|声音太暗|高频(?:太弱|不足|偏弱|不够|缺失)|(?:增加|增强|提升|提亮|补足)(?:高频|亮度|空气感)", brief))
    darken = bool(re.search(r"高频弱化|(?:削弱|压低|降低|减少)(?:高频|亮度)|高频(?:太强|过亮|刺耳)", brief))
    if deess:
        decisions.de_esser.enabled = True
        decisions.de_esser.max_reduction_db = max(4.0, decisions.de_esser.max_reduction_db)
        decisions.reasoning = decisions.reasoning.rstrip("。； ") + f"。实际启用动态齿音控制：中心 {decisions.de_esser.center_hz:g} Hz，最大衰减 {decisions.de_esser.max_reduction_db:g} dB；频点为起点，仍需听感复核"
    if brighten and darken:
        raise ValueError("同时要求增强与弱化高频，请明确最终方向。")
    requested_gain = 3.5 if brighten else -3.5 if darken else None
    if requested_gain is None:
        return
    shelves = [band for band in decisions.tonal_eq.bands if band.filter_type == "high_shelf"]
    if shelves:
        shelf = shelves[0]
        shelf.frequency = min(max(shelf.frequency, 4500), 5500)
        shelf.gain_db = max(shelf.gain_db, requested_gain) if brighten else min(shelf.gain_db, requested_gain)
    else:
        decisions.tonal_eq.bands.append(EQBand(frequency=5500, gain_db=requested_gain, q=0.7, filter_type="high_shelf"))
    decisions.reasoning = decisions.reasoning.rstrip("。； ") + f"。实际高架 EQ：{shelf.gain_db if shelves else requested_gain:+.1f} dB，{shelf.frequency if shelves else 5500:g} Hz；避免把频谱均值当作听感证明"


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

    system_prompt = """You set MixMaster AI mastering DSP parameters from a client brief and measured audio features. You receive numbers, not playable audio or a reference track. Do not claim to hear the track, identify a precise resonance or sibilance, or certify a delivery standard from these measurements.

The implemented chain is corrective EQ → dynamic de-esser → compressor → tonal EQ → saturator → M/S stereo imager → Pedalboard Limiter → export loudness adjustment. Return every DSPDecisions field. An empty EQ list, compressor ratio 1 with zero makeup, saturator mix 0, and stereo width 1 are available when a change is not justified. The imager still removes side energy below mono_low_hz, so use the lowest sensible cutoff when no bass correction is warranted.

Evidence and capability boundaries:
- integrated_lufs measures input loudness; -70 means unavailable, not a genuinely quiet track. true_peak_dbtp is an input estimate, not the exported peak. crest_factor_db and dynamic_range_db describe dynamics.
- Band RMS, spectral centroid, and spectral flatness are broad descriptors. They cannot locate a narrow resonance, prove harshness, or define an ideal tonal balance without a reference. Do not invent a specific problem frequency.
- stereo_width is measured side/mid energy, not the width control. low_end_mono_compatibility measures low-frequency side/mid energy. A mono input cannot acquire genuine stereo width in this chain; dual-mono export merely copies the same signal to L/R.
- The installed Pedalboard Limiter threshold is a compression threshold, despite the legacy schema name limiter.ceiling_dbtp. It is NOT the final output ceiling. Do not put a client's dBFS or dBTP limit in that field. The exporter separately enforces sample peak, true peak, sample rate, channels, and bit depth and measures the encoded WAV.

Decision rules, in priority order:
1. Follow explicit client numbers and creative goals where supported. Separate loudness (LUFS), sample peak (dBFS), true peak (dBTP), and file format. Never assume that mentioning a broadcaster, television, or platform defines all of its technical specifications. If a brief gives only a maximum peak, do not invent a mandatory LUFS target.
2. Use the resolved delivery specification below as binding for supported numeric targets. It combines the client's explicit values with missing values from exactly one source-backed profile. Client numbers always win. Do not borrow a missing number from another broadcaster or platform, or call a profile-level loudness/peak check a complete standards certification. Without a resolved target, choose near valid measured integrated loudness and preserve dynamics; if loudness is unavailable, choose a conservative target and disclose uncertainty. Peak limits are enforced after DSP; do not arbitrarily lower target_lufs.
3. A client's explicit tonal complaint is actionable evidence of intent, even though you cannot hear the audio. For 齿音过重 enable de_esser around 5–8 kHz with about 4–6 dB maximum dynamic reduction, avoiding a broad static treble cut. For 音色太暗 or 高频不足 add a broad high shelf around 4.5–8.5 kHz, initially +2.5 to +4 dB; for 高频弱化 or 削弱高频 use -2.5 to -4 dB. Distinguish “highs are weak” from “make highs weaker”. If brightening and de-essing are both requested, use both stages. Corrective narrow EQ still needs defensible frequency evidence; do not invent a notch from a band average. An explicit requested change must produce a non-neutral stage and remain conservative enough to avoid obvious artifacts.
4. Preserve transients. If input LUFS is within 2 LU of the chosen target, crest_factor_db is below 6 dB, or the brief requests natural dynamics, use gentle compression. For crest factor below 6 dB, the original 1.5–2.0 ratio range is an upper starting point, not a mandate to compress. Avoid extra makeup gain when no compression is needed; loudness normalization happens later.
5. Use saturation only for a requested density or harmonic color; otherwise set mix to 0. Do not widen when measured stereo_width exceeds 1.5. If low_end_mono_compatibility exceeds 0.3, set mono_low_hz above 100 Hz; otherwise avoid unnecessary low-frequency side removal. Do not promise widening of mono input.
6. Select limiter threshold and release for restrained sound, not delivery compliance. Keep enough headroom for the export stage. A loudness target and a strict peak ceiling may be incompatible; the exporter gives peak safety priority and reports any shortfall. Do not claim post-export compliance until the encoded file is measured.

Return exactly one JSON object matching DSPDecisions. In concise Chinese reasoning, state the client goal, the measurements behind material adjustments, any neutral stages, and meaningful uncertainty. Never claim listening, verified file compliance, or effects the chain cannot perform."""

    analysis_str = "\n".join(
        f"  {k}: {v:.6f}" for k, v in job.analysis.items()
    )

    user_message = (
        f"<client_brief>\n{job.prompt}\n</client_brief>\n\n"
        "<resolved_delivery_spec>\n"
        f"profile: {job.delivery_spec.profile_name or 'none'}\n"
        f"profile_note: {job.delivery_spec.profile_note or 'none'}\n"
        f"target_lufs: {job.delivery_spec.target_lufs}\n"
        f"max_sample_peak_dbfs: {job.delivery_spec.max_sample_peak_dbfs}\n"
        f"max_true_peak_dbtp: {job.delivery_spec.max_true_peak_dbtp}\n"
        "These values are enforced on the exported file; describe an applied preset as a reference, not a universal platform standard.\n"
        "</resolved_delivery_spec>\n\n"
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
        _honor_explicit_tone_request(decisions, job.prompt)
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
