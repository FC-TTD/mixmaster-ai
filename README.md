# MixMaster AI

> Give it a vocal file, an instrumental file, and a plain-English prompt. Get back a release-ready mixed and mastered track.

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Powered by Claude](https://img.shields.io/badge/Powered%20by-Claude%20AI-orange.svg)](https://anthropic.com)

---

## What is this?

Professional mixing and mastering usually means expensive studio time, specialist engineers, and a long revision cycle.

**MixMaster AI removes most of that friction.**

You can run it in two ways:

- Give it a finished track plus a prompt and it will master the song.
- Give it a vocal file, an instrumental file, and a prompt and it will mix the vocal into the beat, then master the final stereo track.

Claude AI analyzes the audio, chooses DSP settings from your creative brief, runs a vocal mixing chain when needed, then applies a full mastering chain to deliver a polished WAV ready for release, review, or upload.

Built for producers, bedroom artists, songwriters, indie teams, and anyone who wants faster access to professional-sounding results.

---

## Features

- **Two production modes** - master an existing track, or mix a vocal with an instrumental and master the result
- **AI-driven DSP decisions** - Claude analyzes the audio and sets parameters from your plain-English prompt
- **Full vocal mixing chain** - noise gate -> transient shaper -> channel EQ -> compression -> reverb -> delay -> panning -> blend
- **Full mastering chain** - corrective EQ -> compressor -> tonal EQ -> saturator -> stereo imager -> limiter
- **Automatic beat looping** - short instrumentals are looped to the vocal length automatically, with no manual prep needed
- **Plain-English control** - ask for "warm streaming master" or "tight, dry pop vocal over a punchy beat"
- **Two REST endpoints** - `/master` for finished mixes and `/mix-and-master` for vocal + instrumental workflows
- **Gradio UI with two upload slots** - one for the main track or vocal, one for the instrumental
- **CLI-first workflow** - scriptable commands for both master-only and mix+master use cases
- **Multiple output bit depths** - export 16-bit, 24-bit, or 32-bit float WAV
- **61 tests passing** - coverage spans ingest, analysis, mixing, mastering, API, and export behavior

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| AI / LLM | Anthropic Claude |
| Mixing Engine (`core/mixer.py`) | pedalboard, scipy, numpy |
| Mastering Engine (`core/processor.py`) | pedalboard, scipy, numpy |
| Audio Analysis | librosa, pyloudnorm |
| Audio I/O | soundfile |
| API | FastAPI |
| UI | Gradio |
| Schemas | Pydantic v2 |
| Testing | pytest |

---

## Prerequisites

- Python 3.10 or higher
- An [Anthropic API key](https://console.anthropic.com/)

---

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/Tanzil-Ahmed/mixmaster-ai.git
cd mixmaster-ai
```

### 2. Create and activate virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up environment variables

```bash
cp .env.example .env
```

Open `.env` and add your Anthropic API key:

```env
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

---

## Usage

### Gradio UI (recommended)

```bash
python api.py
```

Open **http://localhost:7860** in your browser.

1. Upload your main file.
2. Optionally upload an instrumental to enable mix+master mode.
3. Enter a prompt such as `"tight modern pop vocal, polished and streaming-ready"`.
4. Choose bit depth.
5. Click **Master**.
6. Download the final WAV.

Notes:

- If you upload only one file, MixMaster AI runs in **master-only** mode.
- If you upload both a vocal and an instrumental, it runs in **mix+master** mode.
- If the beat is shorter than the vocal, looping is handled automatically.

---

### CLI

Master only:

```bash
python cli.py input.wav output.wav "warm master for streaming"
```

Mix + master:

```bash
python cli.py vocal.wav output.wav "tight modern pop vocal over a punchy beat" --instrumental beat.wav
```

With options:

```bash
python cli.py input.wav output.wav "broadcast master" --bit-depth 16
python cli.py vocal.wav output.wav "wide atmospheric vocal, polished and glued" --instrumental beat.wav --bit-depth 24
python cli.py input.wav output.wav "loud club master" --api-key sk-ant-xxx
```

---

### REST API

Start the server:

```bash
python api.py
```

Master-only endpoint:

```bash
curl -X POST http://localhost:7860/master \
  -F "file=@your_track.wav" \
  -F "prompt=warm master for streaming" \
  -F "bit_depth=24" \
  --output mastered.wav
```

Mix-and-master endpoint:

```bash
curl -X POST http://localhost:7860/mix-and-master \
  -F "vocal=@vocal.wav" \
  -F "instrumental=@beat.wav" \
  -F "prompt=intimate centered vocal, clean low end, release-ready finish" \
  -F "bit_depth=24" \
  --output mixed_mastered.wav
```

---

## How It Works

```text
Master-only mode:

Input Track
    |
    v
+------------------+
|     Analyzer     |  <- measures loudness, dynamics, tone, and stereo traits
+------------------+
    |
    v
+------------------+
|    Claude AI     |  <- reads analysis + your prompt -> sets mastering params
+------------------+
    |
    v
+---------------------------------------------------------------+
|                        Mastering Chain                         |
|  Corrective EQ -> Compressor -> Tonal EQ -> Saturator         |
|  -> Stereo Imager -> Limiter                                  |
+---------------------------------------------------------------+
    |
    v
+------------------+
|      Writer      |  <- loudness normalize + dither + export
+------------------+
    |
    v
Mastered WAV


Mix + master mode:

Vocal + Instrumental
    |
    v
+------------------+
|  Vocal Analyzer  |  <- analyzes the vocal for mix decisions
+------------------+
    |
    v
+------------------+
|    Claude AI     |  <- reads vocal analysis + prompt -> sets mix params
+------------------+
    |
    v
+--------------------------------------------------------------------------+
|                              Mixing Chain                                 |
|  Noise Gate -> Transient Shaper -> Channel EQ -> Compression              |
|  -> Reverb -> Delay -> Panning -> Blend                                  |
+--------------------------------------------------------------------------+
    |
    v
Stereo Mix
    |
    v
+------------------+
|     Analyzer     |  <- re-analyzes the full mix for mastering
+------------------+
    |
    v
+------------------+
|    Claude AI     |  <- sets mastering params for the mixed track
+------------------+
    |
    v
+---------------------------------------------------------------+
|                        Mastering Chain                         |
|  Corrective EQ -> Compressor -> Tonal EQ -> Saturator         |
|  -> Stereo Imager -> Limiter                                  |
+---------------------------------------------------------------+
    |
    v
+------------------+
|      Writer      |
+------------------+
    |
    v
Release-ready mixed and mastered WAV
```

### What Claude measures

| Metric | What it tells us |
|--------|------------------|
| RMS dB | Overall signal level |
| Crest factor | Dynamic range and punch |
| Integrated LUFS | Perceived loudness |
| True peak dBTP | Peak ceiling and clipping risk |
| RMS sub / low / mid / high | Tonal balance across bands |
| Spectral centroid | Brightness |
| Spectral flatness | Tonal vs noisy content |
| Stereo width | Stereo spread |
| Low-end mono compatibility | Bass phase stability |

These measurements are used both for vocal-aware mixing decisions and for the final mastering pass.

---

## Prompt Examples

```text
"warm vintage master for vinyl"
"clean streaming master, open top end, controlled low mids"
"loud and punchy club master, tight low end"
"broadcast master for podcast, natural and intelligible"
"tight modern pop vocal over a bright punchy beat"
"intimate centered vocal, dry and upfront, polished for streaming"
"wide atmospheric vocal over a cinematic instrumental, subtle delay throws"
"aggressive trap vocal, hard-hitting beat, clean low end, loud finish"
"indie pop mix with airy vocal, gentle glue, smooth top end"
"lo-fi vocal over dusty instrumental, softer transients, warm final master"
```

---

## Project Structure

```text
mixmaster-ai/
|-- .claude/              # Claude Code team workflow files
|-- api.py                # FastAPI + Gradio server
|-- cli.py                # Command-line interface
|-- CLAUDE.md             # Collaboration notes for Claude Code
|-- requirements.txt
|-- .env.example
|
|-- core/
|   |-- job.py            # Job dataclass + audio loader
|   |-- analyzer.py       # Audio analysis
|   |-- agent.py          # Claude AI decision engine for mixing and mastering
|   |-- mixer.py          # Vocal mixing chain and instrumental blending
|   |-- processor.py      # Mastering DSP chain
|   |-- writer.py         # Output normalization + export
|   `-- schemas.py        # Pydantic models for mix/master settings
|
`-- tests/
    |-- test_ingest.py
    |-- test_analyzer.py
    |-- test_agent.py
    |-- test_api.py
    |-- test_mixer.py
    |-- test_processor.py
    `-- test_writer.py
```

---

## Cost Guide

Master-only jobs make **one Claude call**. Mix+master jobs make **two Claude calls**: one for mixing decisions and one for mastering decisions.

| Workflow | Claude calls | Cost estimate |
|----------|--------------|---------------|
| Master only | 1 | Opus: ~$0.05-$0.15 / Sonnet: ~$0.01-$0.03 |
| Mix + master | 2 | Opus: ~$0.10-$0.30 / Sonnet: ~$0.02-$0.06 |

To use a cheaper model, change `claude-opus-4-5` to `claude-sonnet-4-5` in `core/agent.py`.

---

## TTD deployment

The TTD release keeps the original master-only and mix-and-master workflows, with a Chinese UI and an OpenAI-compatible DSP decision path. The current internal service is `http://ttd-stage:17862/`; it uses `gpt-6-luna` through `http://aiproxy/v1`. The mastering prompt is based on the upstream project's measured audio features, DSP chain, and parameter schema. The Anthropic path remains available through `LLM_PROVIDER=anthropic`.

The supported deployment definition is `docker-compose.yml` with `Dockerfile` and `deploy.sh`. Formal builds use a read-only archive of the recorded source commit and publish only an immutable `h-*` image through `deploy.sh build`. Set `MIXMASTER_IMAGE` to that image before running `deploy.sh deploy` or `docker compose`; the Compose file requires this value. Put credentials in a private `.env` on the host; they are excluded from the image. See [TTD deployment record](ttd_deployment_report.md) for the current image, service checks, and rollback details. The older `docker-compose.preview.yml` is retained only as a rollback reference.

---

## Roadmap

- [x] AI-driven vocal + instrumental mixing
- [ ] Batch processing (master entire folders)
- [ ] Reference track matching
- [ ] Stems mastering
- [ ] MP3/AAC export
- [ ] Preset system
- [ ] Before/after A/B comparison in UI
- [x] Docker image (TTD release)

---

## Author

**Tanzil Ahmed**

- GitHub: [@Tanzil-Ahmed](https://github.com/Tanzil-Ahmed)

---

## License

Licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

---

## Acknowledgements

- [Anthropic](https://anthropic.com) for Claude AI
- [pedalboard](https://github.com/spotify/pedalboard) by Spotify for DSP primitives
- [librosa](https://librosa.org) for audio analysis
- [pyloudnorm](https://github.com/csteinmetz1/pyloudnorm) for LUFS metering
