import os
import json
import anthropic
import numpy as np
from openai import OpenAI
from core.job import Job
from core.schemas import DSPDecisions, MixDecisions
from core.delivery import parse_delivery_spec
from core.mix_context import mix_input_features


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

The implemented chain is corrective EQ → compressor → tonal EQ → saturator → M/S stereo imager → Pedalboard Limiter → export loudness adjustment. Return every DSPDecisions field. An empty EQ list, compressor ratio 1 with zero makeup, saturator mix 0, and stereo width 1 are available when a change is not justified. The imager still removes side energy below mono_low_hz, so use the lowest sensible cutoff when no bass correction is warranted.

Evidence and capability boundaries:
- integrated_lufs measures input loudness; -70 means unavailable, not a genuinely quiet track. true_peak_dbtp is an input estimate, not the exported peak. crest_factor_db and dynamic_range_db describe dynamics.
- Band RMS, spectral centroid, and spectral flatness are broad descriptors. They cannot locate a narrow resonance, prove harshness, or define an ideal tonal balance without a reference. Do not invent a specific problem frequency.
- stereo_width is measured side/mid energy, not the width control. low_end_mono_compatibility measures low-frequency side/mid energy. A mono input cannot acquire genuine stereo width in this chain; dual-mono export merely copies the same signal to L/R.
- The installed Pedalboard Limiter threshold is a compression threshold, despite the legacy schema name limiter.ceiling_dbtp. It is NOT the final output ceiling. Do not put a client's dBFS or dBTP limit in that field. The exporter separately enforces sample peak, true peak, sample rate, channels, and bit depth and measures the encoded WAV.

Decision rules, in priority order:
1. Follow explicit client numbers and creative goals where supported. Separate loudness (LUFS), sample peak (dBFS), true peak (dBTP), and file format. Never assume that mentioning a broadcaster, television, or platform defines all of its technical specifications. If a brief gives only a maximum peak, do not invent a mandatory LUFS target.
2. If the client gives a supported LUFS target, use it. Otherwise treat the original project's -14 streaming, -9 club, and -23 broadcast as optional stylistic starting points, never universal platform standards. Without a clear destination, choose a target near the valid measured integrated loudness and preserve dynamics; if loudness is unavailable, choose a conservative target and disclose uncertainty. Peak limits are enforced after DSP; do not attempt to meet a peak limit by arbitrarily lowering target_lufs.
3. Corrective EQ requires an explicit audible problem in the brief or defensible broad measured evidence. Do not infer a narrow notch from a band average. Use tonal EQ for requested warmth, presence, or air with restrained broad moves; otherwise leave EQ neutral.
4. Preserve transients. If input LUFS is within 2 LU of the chosen target, crest_factor_db is below 6 dB, or the brief requests natural dynamics, use gentle compression. For crest factor below 6 dB, the original 1.5–2.0 ratio range is an upper starting point, not a mandate to compress. Avoid extra makeup gain when no compression is needed; loudness normalization happens later.
5. Use saturation only for a requested density or harmonic color; otherwise set mix to 0. Do not widen when measured stereo_width exceeds 1.5. If low_end_mono_compatibility exceeds 0.3, set mono_low_hz above 100 Hz; otherwise avoid unnecessary low-frequency side removal. Do not promise widening of mono input.
6. Select limiter threshold and release for restrained sound, not delivery compliance. Keep enough headroom for the export stage. A loudness target and a strict peak ceiling may be incompatible; the exporter gives peak safety priority and reports any shortfall. Do not claim post-export compliance until the encoded file is measured.

Return exactly one JSON object matching DSPDecisions. In concise Chinese reasoning, state the client goal, the measurements behind material adjustments, any neutral stages, and meaningful uncertainty. Never claim listening, verified file compliance, or effects the chain cannot perform."""

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


def decide_mix(job: Job, instrumental_job: Job) -> Job:
    job.status = "processing"

    system_prompt = (
        "Set vocal mixing parameters from the client brief and measured vocal AND instrumental features. You do not hear either track.\n"
        "\n"
        "The implemented chain is noise gate → transient shaper → VOCAL-only EQ → vocal compression → reverb → delay → center panning → blend. After vocal processing, the mixer peak-normalizes the vocal and instrumental separately, then applies their relative gain settings. The instrumental is not EQ'd.\n"
        "\n"
        "Rules:\n"
        "- The original project's raw-RMS >12 dB vocal boost rule is unreliable here because both stems are peak-normalized before blending. Use the supplied post_peak_normalization levels as a broad starting point for vocal_gain_db and instrumental_gain_db. Long pauses and vocal processing can change the actual balance; do not apply an automatic 12 dB boost. Favor moderate adjustments consistent with the requested vocal prominence.\n"
        "- Both stems' 300–3000 Hz RMS values describe broad energy overlap, not proven masking or an exact conflicting frequency. Do not automatically cut vocal mids based on spectral centroid; that can reduce intelligibility. Use restrained vocal EQ, level balance, or less reverb when the brief requests clarity. This chain cannot carve the instrumental EQ.\n"
        "- A global RMS cannot identify breaths, noise floor, or consonants. Use a gentle gate or near-neutral transient settings unless the brief and measurements justify stronger processing; protect quiet syllables.\n"
        "- For intimate, close, spoken, or dry vocals, reverb wet_mix must be <=0.35; for an explicitly dry request use near-zero wet mix. Delay must be disabled unless echo/delay is requested.\n"
        "- vocal_pan must be 0.0 (center). Use instrumental_gain_db and vocal_gain_db for relative balance, while avoiding excessive gain on either stem.\n"
        "- Explain the client goal, both stems' relevant measurements, the chosen balance, and uncertainty in concise Chinese. Do not claim to have listened or to have fixed a precise frequency without evidence."
    )

    analysis_str = "\n".join(
        f"  {k}: {v:.6f}" for k, v in job.analysis.items()
    )

    mix_features = mix_input_features(job, instrumental_job)
    user_message = (
        f"<client_brief>\n{job.prompt}\n</client_brief>\n\n"
        f"<vocal_audio sample_rate_hz=\"{job.sample_rate}\" channels=\"{job.num_channels}\" duration_seconds=\"{job.duration_seconds:.3f}\">\n"
        f"{analysis_str}\n</vocal_audio>\n\n"
        f"<instrumental_audio sample_rate_hz=\"{instrumental_job.sample_rate}\" channels=\"{instrumental_job.num_channels}\" duration_seconds=\"{instrumental_job.duration_seconds:.3f}\">\n"
        f"{json.dumps(mix_features['instrumental'], ensure_ascii=False)}\n</instrumental_audio>\n\n"
        f"<pre_mix_relative_levels>\n{json.dumps(mix_features, ensure_ascii=False)}\n</pre_mix_relative_levels>\n\n"
        "Return mixing parameters matching the actual chain and the available evidence."
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
