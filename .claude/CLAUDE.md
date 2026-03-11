# TTS Integration Agent

A Claude Code plugin for onboarding new TTS models into vLLM-Omni.
Self-verifying (ASR round-trip) and self-iterating (diagnose + fix loop).

## Commands

- `/integrate <model_id>` - Full loop: analyze, generate, build, test, ASR verify, iterate
- `/analyze <model_id>` - Analyze model architecture only (no code generation)
- `/verify <audio_path> <expected_text>` - ASR-verify a single TTS audio output

## Hooks

- **guard-existing-models** - Blocks edits to existing model code (qwen3_tts, fish_speech, cosyvoice3, etc.)
- **log-iteration** - Logs all bash outputs to workspace/bash_log.txt

## Key Paths

- vLLM-Omni: `~/proj/vllm-omni`
- Workspace: `~/proj/tts-integration-agent/workspace/`
- Reference implementations:
  - Qwen3-TTS: `~/proj/vllm-omni/vllm_omni/model_executor/models/qwen3_tts/`
  - Fish Speech S2 Pro: `~/proj/vllm-omni/vllm_omni/model_executor/models/fish_speech/`
- Stage configs: `~/proj/vllm-omni/vllm_omni/model_executor/stage_configs/`
- Stage processors: `~/proj/vllm-omni/vllm_omni/model_executor/stage_input_processors/`
- Online serving: `~/proj/vllm-omni/vllm_omni/entrypoints/openai/serving_speech.py`

## Architecture Patterns

Two proven patterns exist:

1. **Single-AR** (Qwen3-TTS): AR model -> Code2Wav decoder (24kHz)
2. **Dual-AR** (Fish Speech): Slow AR + Fast AR -> DAC decoder (44.1kHz)

When integrating a new model, identify which pattern it follows and use the matching reference.

## Debugging Priority (from real experience)

When audio is bad, check in this order:
1. **RoPE style** - interleaved vs NeoX (most common silent killer)
2. **Embedding normalization** - sqrt(num_codebooks + 1) scaling
3. **Codec hop length** - product of ALL rate factors
4. **Token ID mapping** - verify ranges with tokenizer
5. **Sampling params** - repetition_penalty, stop tokens, max_tokens
6. **Codebook layout** - codebook-major vs frame-major
7. **Dtype** - some decoders need float32

## Environment

```bash
source ~/proj/vllm-omni/.venv/bin/activate
```
