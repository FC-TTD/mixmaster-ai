# MixMaster AI Preview Deployment Report

## Target

- Host: `ttd-stage`
- Runtime: CPU
- Project path on host: `/opt/mixmaster-ai`
- Container: `mixmaster-ai-preview`
- URL: `http://ttd-stage:17862/`

## Runtime

- Image: `mixmaster-ai:preview`
- Compose file: `/opt/mixmaster-ai/docker-compose.preview.yml`
- Host port: `17862`
- Container port: `7860`
- GPU: not requested.
- LLM provider: `openai`
- OpenAI-compatible endpoint: `http://aiproxy/v1`
- Model: `gpt-6-luna`
- Reasoning effort: `low`
- Speed profile: fast model variant (`luna`)
- OpenAI-compatible request uses explicit JSON mode for reliable DSP decision validation.
- Required secret for Anthropic mode only: `ANTHROPIC_API_KEY`.

## Service

Useful commands:

```bash
ssh ttd-stage 'cd /opt/mixmaster-ai && docker compose -f docker-compose.preview.yml ps'
ssh ttd-stage 'docker logs -f mixmaster-ai-preview'
ssh ttd-stage 'cd /opt/mixmaster-ai && docker compose -f docker-compose.preview.yml restart'
```

To switch back to Anthropic without putting the key in git:

```bash
ssh ttd-stage 'cd /opt/mixmaster-ai && printf "LLM_PROVIDER=anthropic\\nANTHROPIC_API_KEY=sk-ant-...\\n" > .env && docker compose -f docker-compose.preview.yml up -d'
```

## Verification Plan

## Verified

- Docker image built successfully on `ttd-stage`.
- Container is running with `0.0.0.0:17862->7860/tcp`.
- Page check returned `HTTP/1.1 200 OK` from `http://ttd-stage:17862/`.
- Internal page fetch returned 33,885 bytes.
- Docker inspect shows no GPU device request: `DeviceRequests=null`.
- The container is configured to use the LAN `aiproxy` service through OpenAI-compatible chat completions.
- The service was initially verified with `gpt-5.6-luna`. On 2026-09-27 the requested model was changed to `gpt-6-luna` for client-brief analysis. The running container reports `OPENAI_MODEL=gpt-6-luna`, and a direct chat completion from the container returned model `gpt-6-luna`. The `/v1/models` listing returned HTTP 401, so model discovery could not be used for this check.
- On 2026-09-27 the mastering decision prompt was revised against the upstream MixMaster AI README, its 13 measured features, six-stage mastering chain, and DSPDecisions schema. The prompt now separates measured evidence from claims that require listening, treats the upstream loudness values as starting points, and preserves dynamics when requested. A live synthetic WAV request to `/master` returned HTTP 200 and a 24-bit stereo WAV; the page returned HTTP 200. The Gradio UI and mixing prompt were not changed.
- Real API smoke test uploaded a generated WAV to `POST /master`; it returned `HTTP 200` with a 24-bit WAV response.
- 2026-08-06 real smoke after switching: `POST /master` returned `HTTP 200`, 24-bit mono WAV, 198,494 bytes.
- The first post-switch request exposed a schema-compliance issue; adding `response_format={"type": "json_object"}` resolved it while keeping reasoning effort at `low`.
- Gradio copy was updated to Chinese mode descriptions and control explanations.
- Gradio result text was verified in Chinese, including loudness, true peak, bit depth, and model reasoning.
