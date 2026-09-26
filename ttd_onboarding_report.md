# MixMaster AI Onboarding Report

## Repository

- Source: https://github.com/Tanzil-Ahmed/mixmaster-ai
- Local path: `/Users/peidongfeng/Documents/模型测试/mixmaster-ai`
- Branch: `ttd`
- Upstream default branch: `main`

## Project Shape

- Type: FastAPI + Gradio audio mixing/mastering application.
- Primary runtime entry: `python api.py`.
- Internal service port: `7860`.
- REST endpoints:
  - `POST /master`
  - `POST /mix-and-master`
- UI: Gradio mounted at `/`.
- Model weights: none.
- GPU requirement: none; CPU deployment is appropriate.

## Runtime And Dependencies

- Python: 3.10+ upstream; preview container uses Python 3.11.
- System packages added for audio runtime: `ffmpeg`, `libsndfile1`.
- Python dependencies are installed from `requirements.txt`.
- External runtime dependency: an LLM endpoint is required for real processing.
- Supported decision providers:
  - `LLM_PROVIDER=anthropic` with `ANTHROPIC_API_KEY`
  - `LLM_PROVIDER=openai` with an OpenAI-compatible endpoint such as vLLM

## Recommended Path

- Recommended path for the current request: Docker preview deployment.
- Reason: upstream has a simple Python entrypoint but no Dockerfile, and audio native dependencies are easier to stabilize in a container.

## Risks

- Real audio processing calls the configured LLM provider; if the provider is unavailable or returns invalid JSON, jobs fail.
- API responses for processing failures currently return `500` with the raw exception text.
- Temporary audio files are written under `/tmp`; preview compose keeps `/tmp` in a Docker volume.
