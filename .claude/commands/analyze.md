---
name: analyze
description: Analyze a HuggingFace TTS model architecture without generating code. Useful for planning.
arguments:
  - name: model_id
    description: HuggingFace model ID (e.g., zai-org/GLM-TTS)
    required: true
---

# /analyze - Model Architecture Analysis

Analyze the TTS model `$ARGUMENTS` without generating any code.

## Steps

1. Fetch `config.json` from HuggingFace
2. List all files in the repo
3. If modeling code exists, read it to understand the architecture
4. Determine:
   - Model type (AR, DiT, flow-matching, hybrid)
   - Stage boundaries
   - Codec format (codebook count, frame rate, sample rate)
   - Input/output formats
   - Dependencies (external codecs, vocoders, etc.)
5. Compare with existing vLLM-Omni models (Qwen3-TTS, CosyVoice3)
6. Write analysis to `~/proj/tts-integration-agent/workspace/analysis_<model>.md`
7. Report: estimated difficulty, what can be reused, what needs new code
