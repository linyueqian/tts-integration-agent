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
4. **Search for reference implementations** on GitHub (sglang-omni, original repo, etc.)
   These reveal critical details like RoPE style, embedding normalization, token mappings.
5. Determine:
   - Architecture pattern: Single-AR (like Qwen3-TTS), Dual-AR (like Fish Speech), or Flow/DiT
   - Stage boundaries
   - Codec format (codebook count, frame rate, sample rate, hop length)
   - Input/output formats (chat template? special tokens?)
   - Dependencies (external codecs, vocoders, etc.)
   - RoPE style (NeoX vs interleaved/GPT-J)
   - Embedding normalization pattern
6. Compare with existing vLLM-Omni models (Qwen3-TTS, Fish Speech S2 Pro)
7. Write analysis to `~/proj/tts-integration-agent/workspace/analysis_<model>.md`
8. Report: estimated difficulty, closest reference impl, what can be reused, what needs new code
