# Testing standards

## Framework
pytest only. No unittest.

## Location
All tests in tests/ folder.
One test file per module: test_mixer.py, test_processor.py, test_analyzer.py.

## Synthetic audio only
Never use real audio files in tests.
Generate with numpy sine waves — see qa-engineer.md for helpers.

## Required assertions for every DSP test
- output.shape == input.shape
- output.dtype == np.float32
- np.max(np.abs(output)) <= 1.0
- np.all(np.isfinite(output))

## Required edge cases for every function
- Silent input
- Mono input
- Very short audio (0.1 seconds)
- Full amplitude input (0.99)

## Naming convention
test_[function_name]_[scenario]
Examples:
- test_apply_noise_gate_silence
- test_apply_reverb_mono_input
- test_mix_tracks_returns_stereo

## No external dependencies in tests
No API calls in tests. No Claude API. No file I/O.
Tests must run fully offline and complete in under 30 seconds total.