# Audio conventions

## Array shape
Always (channels, samples). Never (samples, channels).
Mono: (1, samples). Stereo: (2, samples).

## Dtype
float32 for all I/O and storage.
float64 for all internal DSP math.
Convert at every boundary — never assume dtype is correct.

## Amplitude
All audio must stay within [-1.0, 1.0].
Clip before every pedalboard plugin, no exceptions.
After blending two signals, check peak and normalize if above 0.99.

## Sample rates
Always pass sample_rate explicitly to every function.
Never hardcode 44100 anywhere.

## Silence detection
Before processing, check: if np.max(np.abs(audio)) < 1e-6 — return audio unchanged.
Never run DSP on silence — it wastes compute and can produce NaN.

## Mono to stereo
If input is mono (1, samples) and stereo output is needed:
np.stack([audio[0], audio[0]]) — duplicate the channel.
Never use np.repeat or np.tile for this.

## Blending two signals
When summing vocal + instrumental:
1. Normalize each individually first
2. Apply gain weights (e.g. vocal 0.8, instrumental 1.0)
3. Sum
4. Peak-normalize the result if max abs > 0.99
Never hard clip a blend — always normalize.