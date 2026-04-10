# API and schema conventions

## Pydantic schemas
All DSP parameter models live in core/schemas.py only.
Every parameter needs a Field() with ge/le bounds.
Use Literal types for string enums — never plain str.
Every model needs a label or reasoning field for Claude's explanation.

## FastAPI
All endpoints in api.py only.
Request validation via Pydantic models — never raw dicts.
Always return structured JSON responses with status field.

## Claude API calls
All Claude API calls live in core/agent.py only.
Always use tool_choice forced — never let Claude respond in free text for DSP decisions.
Always include reasoning field in every tool schema.
Model selection:
  - mix + master mode: claude-opus-4-5
  - master only mode: claude-sonnet-4-5
Temperature: 0.2 for mastering, 0.3 for mixing. Never above 0.4.

## Job object
core/job.py is the single source of truth for job state.
Never pass raw audio arrays between modules — always via job.audio or job.processed_audio.
Always update job.status at the start and end of every processing step.
Valid statuses: pending, analyzing, processing, mixing, mastering, done, error.

## Environment variables
API keys come from os.environ only.
Never hardcode API keys.
Never read .env directly in module code — use python-dotenv in entry points only (api.py, cli.py).