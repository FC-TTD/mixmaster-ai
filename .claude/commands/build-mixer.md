# Build mixer.py

## What this command does
Implements core/mixer.py from scratch — the mixing DSP chain.

## Steps to execute
1. Read core/schemas.py first — understand existing DSP models
2. Read core/processor.py — understand the coding patterns used
3. Read core/job.py — understand the Job dataclass
4. Add MixSettings and MixDecisions schemas to core/schemas.py
5. Implement core/mixer.py with the full mixing chain
6. Create tests/test_mixer.py with full test coverage

## Mixing chain to implement (in order)
1. _apply_noise_gate(vocal, sample_rate, settings)
2. _apply_transient_shaper(vocal, sample_rate, settings)
3. _apply_channel_eq(vocal, sample_rate, settings)
4. _apply_channel_compression(vocal, sample_rate, settings)
5. _apply_reverb(vocal, sample_rate, settings)
6. _apply_delay(vocal, sample_rate, settings)
7. _apply_panning(audio, pan)
8. mix_tracks(vocal, instrumental, sample_rate, decisions) — main entry point

## Rules
- Follow all rules in .claude/rules/audio-conventions.md
- Follow all rules in .claude/rules/testing.md
- Use dsp-engineer agent for implementation
- Use qa-engineer agent to review before finishing
- Never modify any existing file except schemas.py