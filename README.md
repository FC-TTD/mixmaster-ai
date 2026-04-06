# MixMaster AI 🎚️

> Give it a raw audio file and a plain-English prompt. Get back a professionally mastered track.

![MixMaster AI UI](docs/demo.png)

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Powered by Claude](https://img.shields.io/badge/Powered%20by-Claude%20AI-orange.svg)](https://anthropic.com)

---

## What is this?

Professional audio mastering costs hundreds of dollars per track and requires years of trained ears.

**MixMaster AI eliminates that barrier.**

You describe what you want in plain English. Claude AI analyzes your audio, makes precise DSP decisions, and runs a full mastering chain — EQ, compression, saturation, stereo imaging, and limiting — all calibrated to your creative brief.

Built for producers, bedroom musicians, indie artists, and anyone who wants professional-sounding masters without the price tag.

---

## Features

- **AI-driven DSP decisions** — Claude analyzes 13 acoustic measurements and sets every parameter
- **Full mastering chain** — Corrective EQ → Compressor → Tonal EQ → Saturator → Stereo Imager → Limiter
- **Plain-English prompts** — "warm vintage master for vinyl" or "loud club master with tight low end"
- **Streaming-ready output** — targets -14 LUFS (Spotify/Apple Music), -9 LUFS (club), -23 LUFS (broadcast)
- **True peak control** — guaranteed no inter-sample clipping
- **Gradio UI** — drag, drop, master, download
- **REST API** — integrate into any workflow via `/master` endpoint
- **CLI** — scriptable, batch-friendly
- **Multiple output formats** — 16-bit, 24-bit, 32-bit float WAV

---

## Demo

> 📸 Add your own screenshot after first run

![UI Screenshot](docs/demo.png)

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| AI / LLM | Anthropic Claude |
| DSP | pedalboard, scipy, numpy |
| Audio Analysis | librosa, pyloudnorm |
| Audio I/O | soundfile |
| API | FastAPI |
| UI | Gradio |
| Schemas | Pydantic v2 |

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

1. Upload your audio file (WAV, FLAC, AIFF, MP3, OGG)
2. Describe what you want: *"warm master for streaming"*
3. Choose bit depth (24-bit recommended)
4. Click **Master**
5. Download your mastered track

---

### CLI

```bash
python cli.py input.wav output.wav "warm master for streaming"
```

With options:

```bash
python cli.py input.wav output.wav "loud club master" --bit-depth 16
python cli.py input.wav output.wav "broadcast master" --api-key sk-ant-xxx
```

---

### REST API

Start the server:

```bash
python api.py
```

Send a request:

```bash
curl -X POST http://localhost:7860/master \
  -F "file=@your_track.wav" \
  -F "prompt=warm master for streaming" \
  -F "bit_depth=24" \
  --output mastered.wav
```

---

## How It Works

```
Input Audio
    │
    ▼
┌─────────────┐
│  Analyzer   │  ← measures 13 acoustic properties
└─────────────┘
    │
    ▼
┌─────────────┐
│  Claude AI  │  ← reads analysis + your prompt → sets all DSP params
└─────────────┘
    │
    ▼
┌──────────────────────────────────────────────┐
│              Processing Chain                │
│  Corrective EQ → Compressor → Tonal EQ      │
│  → Saturator → Stereo Imager → Limiter      │
└──────────────────────────────────────────────┘
    │
    ▼
┌─────────────┐
│   Writer    │  ← loudness normalize + dither + export
└─────────────┘
    │
    ▼
Mastered WAV
```

### What Claude measures

| Metric | What it tells us |
|--------|-----------------|
| RMS dB | Overall loudness |
| Crest factor | Dynamic range |
| Integrated LUFS | Perceived loudness |
| True peak dBTP | Peak level |
| RMS sub/low/mid/high | Frequency balance |
| Spectral centroid | Brightness |
| Spectral flatness | Tonal vs noisy |
| Stereo width | Stereo spread |
| Low-end mono compatibility | Bass phase issues |

---

## Prompt Examples

```
"warm vintage master for vinyl"
"loud and punchy club master, tight low end"
"clean streaming master, -14 LUFS"
"broadcast master for podcast, -23 LUFS"
"aggressive metal master, maximum loudness"
"cinematic master, wide stereo, lots of air"
"lo-fi master with tape saturation"
```

---

## Project Structure

```
mixmaster-ai/
├── cli.py              # Command-line interface
├── api.py              # FastAPI + Gradio server
├── requirements.txt
├── .env.example
│
└── core/
    ├── job.py          # Job dataclass + audio loader
    ├── analyzer.py     # 13-metric audio analysis
    ├── agent.py        # Claude AI DSP decision engine
    ├── processor.py    # DSP chain implementation
    ├── writer.py       # Output normalization + export
    └── schemas.py      # Pydantic DSP parameter models
```

---

## Cost Guide

Each mastering job makes one Claude API call.

| Model | Cost per master |
|-------|----------------|
| Claude Opus | ~$0.05–$0.15 |
| Claude Sonnet | ~$0.01–$0.03 |

To use a cheaper model, change `claude-opus-4-5` to `claude-sonnet-4-5` in `core/agent.py`.

---

## Roadmap

- [ ] Batch processing (master entire folders)
- [ ] Reference track matching
- [ ] Stems mastering
- [ ] MP3/AAC export
- [ ] Preset system
- [ ] Before/after A/B comparison in UI
- [ ] Docker image

---

## Contributing

Contributions welcome. Open an issue first for major changes.

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes
4. Push and open a Pull Request

---

## Author

**Tanzil Ahmed**
- GitHub: [@Tanzil-Ahmed](https://github.com/Tanzil-Ahmed)

---

## License

Licensed under the Apache License 2.0 — see the [LICENSE](LICENSE) file for details.

---

## Acknowledgements

- [Anthropic](https://anthropic.com) for Claude AI
- [pedalboard](https://github.com/spotify/pedalboard) by Spotify for DSP primitives
- [librosa](https://librosa.org) for audio analysis
- [pyloudnorm](https://github.com/csteinmetz1/pyloudnorm) for LUFS metering

---

> Built for musicians who deserve professional sound without professional prices.
