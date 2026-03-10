# TTS Integration Agent

A Claude Code plugin for onboarding new TTS models into vLLM-Omni.
Self-verifying (ASR round-trip) and self-iterating (diagnose + fix loop).

## Commands

- `/integrate <model_id>` - Full loop: analyze, generate, build, test, ASR verify, iterate
- `/analyze <model_id>` - Analyze model architecture only (no code generation)
- `/verify <audio_path> <expected_text>` - ASR-verify a single TTS audio output

## Hooks

- **guard-existing-models** - Blocks edits to existing model code (qwen3_tts, cosyvoice3, etc.)
- **log-iteration** - Logs all bash outputs to workspace/bash_log.txt

## Key Paths

- vLLM-Omni: `~/proj/vllm-omni`
- Workspace: `~/proj/tts-integration-agent/workspace/`
- Reference impl: `~/proj/vllm-omni/vllm_omni/model_executor/models/qwen3_tts/`
- Stage configs: `~/proj/vllm-omni/vllm_omni/model_executor/stage_configs/`
- Stage processors: `~/proj/vllm-omni/vllm_omni/model_executor/stage_input_processors/`

## Conda

```bash
eval "$(~/anaconda3/bin/conda shell.bash hook)"
conda activate vllm-omni
```
