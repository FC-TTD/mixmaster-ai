# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project does
MixMaster AI takes a raw audio file and a plain-English prompt and returns a release-ready mastered audio file.
No mixing engineer needed. Target users: bedroom singers, indie artists, producers.

## Commands
- Run all tests: `python -m pytest tests/ -v`
- Run a single test: `python -m pytest tests/test_analyzer.py::test_rms_sine_wave -v`
- Run CLI: `python cli.py input.wav output.wav "your prompt"`
- Start server: `python api.py` (Gradio UI at http://localhost:7860, REST API at `/master`)
- Activate venv (Windows): `venv\Scripts\activate`

## Architecture

### Pipeline flow
Every mastering job runs as a linear pipeline through a `Job` dataclass:

```
load_audio()  →  analyze()  →  decide()  →  process()  →  write()
 job.py          analyzer.py   agent.py     processor.py   writer.py
```

Each function takes a `Job`, mutates it, and returns it. The `Job` object is the single source of truth — never pass raw audio arrays between modules directly.

### Key modules
- **`core/job.py`** — `Job` dataclass (holds audio, analysis dict, DSP decisions, status) and `load_audio()`. Audio is always stored as `(channels, samples)` float32.
- **`core/analyzer.py`** — Measures 13 acoustic metrics (LUFS, RMS bands, crest factor, spectral features, stereo width, mono compatibility). Populates `job.analysis`.
- **`core/agent.py`** — Calls Claude API with forced tool use to populate `job.dsp_decisions` (`DSPDecisions` Pydantic model). All Claude API calls live here only.
- **`core/processor.py`** — Runs the DSP mastering chain: corrective EQ → compressor → tonal EQ → saturator → M/S stereo imager → limiter. Uses pedalboard for compressor/limiter, scipy for EQ filters.
- **`core/writer.py`** — LUFS normalization to `target_lufs`, TPDF dither (16-bit only), export via soundfile.
- **`core/schemas.py`** — All Pydantic v2 DSP parameter models (`DSPDecisions`, `EQSettings`, `CompressorSettings`, etc.). Every parameter has `ge`/`le` bounds.
- **`api.py`** — FastAPI + Gradio server. Entry point only; orchestrates pipeline, no DSP logic.
- **`cli.py`** — CLI entry point only; orchestrates pipeline, no DSP logic.

### Agents and commands
- `.claude/agents/` — `dsp-engineer`, `prompt-engineer`, `qa-engineer`
- `.claude/commands/` — `add-effect`, `build-mixer`, `run-tests`

## Coding rules

### Never break existing modules
`processor.py`, `analyzer.py`, `agent.py`, `writer.py`, `job.py`, `schemas.py` are working and tested. Do not modify them unless explicitly told to.

### Schema first
Before writing any DSP function, add its Pydantic schema to `schemas.py`. No magic numbers — every parameter must come from a schema with `ge`/`le` bounds. Use `Literal` types for string enums, never plain `str`.

### Audio array convention
- Shape: always `(channels, samples)` — never `(samples, channels)`
- `float32` for I/O and storage; `float64` for internal DSP math
- Convert: `audio.astype(np.float64)` at function entry, `.astype(np.float32)` at exit
- Clip to `[-1.0, 1.0]` before every pedalboard plugin call, no exceptions
- Check silence before processing: `if np.max(np.abs(audio)) < 1e-6: return audio unchanged`
- Never hardcode `44100` — always pass `sample_rate` explicitly
- Mono to stereo: `np.stack([audio[0], audio[0]])` — never `np.repeat` or `np.tile`
- When blending two signals: normalize each individually, apply gain weights, sum, then peak-normalize if `max abs > 0.99`. Never hard clip a blend.

### No side effects in DSP functions
Functions take arrays and return arrays. File I/O lives in `job.py` and `writer.py` only.

### Job status
Update `job.status` at the start and end of every processing step. Valid values: `pending`, `analyzing`, `processing`, `mixing`, `mastering`, `done`, `error`.

### Claude API conventions
- All Claude API calls in `core/agent.py` only
- Always use `tool_choice` forced — never let Claude respond in free text for DSP decisions
- Always include a `reasoning` field in every tool schema
- Temperature: 0.2 for mastering, 0.3 for mixing. Never above 0.4
- Wrap all API calls in try/except; set `job.status = "error"` and `job.error = str(e)` on failure

### Environment variables
- API keys from `os.environ` only
- `load_dotenv()` in entry points (`api.py`, `cli.py`) only — never inside `core/` modules

### Testing standards
- pytest only, no unittest
- One test file per module: `tests/test_<module>.py`
- Synthetic audio only (numpy sine waves) — never real audio files
- Required assertions for every DSP test: `output.shape == input.shape`, `output.dtype == np.float32`, `np.max(np.abs(output)) <= 1.0`, `np.all(np.isfinite(output))`
- Required edge cases per function: silent input, mono input, very short audio (0.1 s), full-amplitude input (0.99)
- Test naming: `test_[function_name]_[scenario]`
- No Claude API calls in tests — must run fully offline in under 30 seconds total

## Tech stack
- Python 3.12, pedalboard (Spotify), scipy/numpy, librosa, pyloudnorm, soundfile
- Anthropic Claude API (forced tool use for DSP decisions)
- FastAPI + Gradio, Pydantic v2

## AI team structure
- Architecture decisions → ask Tanzil before implementing
- DSP code → `dsp-engineer` agent
- Prompt engineering for `agent.py` → `prompt-engineer` agent
- Code review → `qa-engineer` agent

## Cost optimization
- Claude Code → complex architecture, new modules, hard debugging
- ChatGPT o3 → code audits, alternative implementations, senior review
- Codex → boilerplate, test generation, repetitive scaffolding
