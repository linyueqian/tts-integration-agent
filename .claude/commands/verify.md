---
name: verify
description: Verify a TTS audio output using ASR (OpenAI gpt-4o-mini-transcribe). Quick self-check for any generated audio.
arguments:
  - name: audio_path
    description: Path to the audio file to verify
    required: true
  - name: expected_text
    description: The text that was used to generate the audio
    required: true
---

# /verify - ASR Verification

Run the ASR verification script on the given audio:

```bash
eval "$(~/anaconda3/bin/conda shell.bash hook)"
conda activate vllm-omni
python ~/proj/tts-integration-agent/scripts/verify_tts.py \
  --audio "$1" \
  --expected-text "$2"
```

Report the result:
- Audio validity (duration, sample rate, RMS energy)
- OpenAI transcription
- Word Error Rate
- PASS/FAIL verdict
