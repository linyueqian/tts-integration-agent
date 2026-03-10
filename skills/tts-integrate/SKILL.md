---
name: tts-integrate
description: Integrate a new TTS model into vLLM-Omni. Use when given a HuggingFace TTS model ID and asked to add support for it. This skill runs a self-verifying loop: analyze, generate code, test, verify with ASR, and iterate on failures.
---

# TTS Model Integration Agent

You are a TTS integration agent. Your job is to take a HuggingFace TTS model and integrate it into vLLM-Omni, verifying your work with ASR at each step.

## Workflow

Execute the following phases in order. If any phase fails, diagnose the error and retry from the appropriate phase. Maximum 5 iterations.

### Phase 1: Analyze Model

1. Fetch the model's `config.json` from HuggingFace:
   ```bash
   python -c "from huggingface_hub import hf_hub_download; import json; path = hf_hub_download('MODEL_ID', 'config.json'); print(json.dumps(json.load(open(path)), indent=2))"
   ```

2. List all files in the repo:
   ```bash
   python -c "from huggingface_hub import list_repo_files; [print(f) for f in list_repo_files('MODEL_ID')]"
   ```

3. Read the model's modeling code on HuggingFace (if available) to understand:
   - What are the main components? (AR model, decoder, vocoder, flow model, etc.)
   - What is the input format? (text tokens, phonemes, etc.)
   - What is the intermediate representation? (codec codes, mel spectrograms, etc.)
   - What is the output? (waveform, codec codes, etc.)
   - What is the codec frame rate? (e.g., 12 Hz, 25 Hz, 50 Hz)

4. Determine stage boundaries:
   - Stage 0: AR model (text -> codec codes) - worker_type: ar
   - Stage 1: Decoder (codec codes -> waveform) - worker_type: generation

### Phase 2: Generate Integration Code

Use Qwen3-TTS as the reference implementation. Read these files first:
- `~/proj/vllm-omni/vllm_omni/model_executor/stage_configs/qwen3_tts.yaml`
- `~/proj/vllm-omni/vllm_omni/model_executor/stage_configs/qwen3_tts_async_chunk.yaml`
- `~/proj/vllm-omni/vllm_omni/model_executor/stage_input_processors/qwen3_tts.py`
- `~/proj/vllm-omni/vllm_omni/model_executor/models/qwen3_tts/` (all files)
- `~/proj/vllm-omni/docs/models/tts_developer_guide.md`

Generate these files for the new model:

1. **Stage config YAML** at `stage_configs/<model_name>.yaml`:
   - Follow the Qwen3-TTS pattern
   - Set correct model_stage names, model_arch, worker_type
   - Configure default_sampling_params

2. **Async chunk stage config** at `stage_configs/<model_name>_async_chunk.yaml`:
   - Enable `async_chunk: true`
   - Set `custom_process_next_stage_input_func`
   - Configure connector (chunk_frames, left_context_frames)

3. **Stage input processor** at `stage_input_processors/<model_name>.py`:
   - Implement `<stage_a>2<stage_b>_async_chunk()` function
   - Buffer codec codes in connector
   - Emit chunks at configured chunk_size

4. **Model wrapper** at `models/<model_name>/`:
   - `__init__.py`
   - AR model wrapper (if needed beyond HF model)
   - Decoder/Code2Wav wrapper with `chunked_decode()` method
   - Register in `models/__init__.py`

5. **E2E test** at `tests/entrypoints/test_<model_name>_speech.py`:
   - Test offline inference
   - Test online `/v1/audio/speech` endpoint
   - Verify audio output is valid wav

### Phase 3: Build Verification

```bash
cd ~/proj/vllm-omni
eval "$(~/anaconda3/bin/conda shell.bash hook)"
conda activate vllm-omni
python -c "import vllm_omni; print('OK')"
```

Check that new files have no syntax errors:
```bash
cd ~/proj/vllm-omni
python -m py_compile vllm_omni/model_executor/stage_input_processors/<model_name>.py
python -m py_compile vllm_omni/model_executor/models/<model_name>/__init__.py
```

Run ruff:
```bash
ruff check vllm_omni/model_executor/models/<model_name>/
ruff check vllm_omni/model_executor/stage_input_processors/<model_name>.py
```

### Phase 4: Offline Inference Test

Write a test script and run it:

```python
from vllm_omni.entrypoints.omni import Omni

omni = Omni(model="MODEL_ID")
outputs = omni.generate("Hello, this is a test of the new TTS model.")
audio = outputs[0].request_output[0].audio
audio.save("~/proj/tts-integration-agent/workspace/test_output.wav")
print(f"Duration: {audio.duration:.2f}s")
```

If this fails, read the error carefully:
- Import errors: check model registration
- Config errors: check YAML stage config
- Runtime errors: check model wrapper code
- OOM: try smaller batch size or dtype

### Phase 5: ASR Verification (Self-Check)

This is the critical self-verification step. Run:

```bash
python ~/proj/tts-integration-agent/scripts/verify_tts.py \
  --audio ~/proj/tts-integration-agent/workspace/test_output.wav \
  --expected-text "Hello, this is a test of the new TTS model."
```

Interpretation:
- **WER < 0.3**: PASS. The model is producing intelligible speech.
- **WER 0.3-0.5**: MARGINAL. Speech is partially intelligible. Check codec/decoder.
- **WER > 0.5**: FAIL. Output is likely garbage. Major issue in AR or decoder stage.
- **Audio too short/empty**: Decoder not producing output. Check code2wav.
- **All silence**: Check dtype (need float32 for some decoders, see #1664).

### Phase 6: Iterate on Failures

If any phase fails:

1. Record the error in `~/proj/tts-integration-agent/workspace/iteration_log.md`
2. Diagnose the root cause
3. Fix the code
4. Go back to the failed phase and retry
5. Maximum 5 iterations before asking for human help

Common fixes:
- **ImportError**: Model not registered in `__init__.py`
- **KeyError in config**: Missing field in YAML stage config
- **Silent audio**: Decoder dtype issue (try float32)
- **Garbage audio**: Wrong codec frame rate or codebook mapping
- **High WER but audio sounds ok**: ASR model language mismatch

## Important Rules

- Always read existing reference code before generating new code
- Never modify existing Qwen3-TTS files
- Follow the same code style (ruff, 120 char line limit)
- Test with at least 3 different sentences before declaring success
- Log every iteration's result for debugging
