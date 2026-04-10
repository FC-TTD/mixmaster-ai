# Add effect

## What this command does
Adds a single new DSP effect to mixer.py or processor.py safely.

## Steps to execute
1. Read the existing file where the effect will be added
2. Read core/schemas.py — check if a schema already exists for this effect
3. If no schema exists — add it to schemas.py first
4. Implement the effect function following audio-conventions.md
5. Add the effect to the chain in the correct position
6. Write tests for the new effect in the corresponding test file
7. Run tests to verify nothing broke

## Rules
- One effect at a time — never add multiple effects in one command
- Schema must exist before implementation — no exceptions
- Always run tests after adding — report results before finishing
- Never remove or reorder existing effects in the chain