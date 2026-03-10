---
name: integrate
description: Integrate a new TTS model into vLLM-Omni. Self-verifying loop that analyzes, generates code, tests, and verifies with ASR.
arguments:
  - name: model_id
    description: HuggingFace model ID (e.g., zai-org/GLM-TTS)
    required: true
  - name: max_iterations
    description: Maximum self-correction iterations (default 5)
    required: false
---

# /integrate - TTS Model Integration

You are running the TTS integration loop for model: `$ARGUMENTS`

## Setup

```bash
eval "$(~/anaconda3/bin/conda shell.bash hook)"
conda activate vllm-omni
```

Set these variables for the session:
- `MODEL_ID`: first argument
- `MAX_ITER`: second argument or 5
- `VLLM_DIR`: ~/proj/vllm-omni
- `WORK_DIR`: ~/proj/tts-integration-agent/workspace
- `ITER_LOG`: $WORK_DIR/iteration_log.md

Create workspace and iteration log:
```bash
mkdir -p $WORK_DIR
```

## Phase 1: Analyze

1. Fetch `config.json`:
```bash
python -c "from huggingface_hub import hf_hub_download; import json; path = hf_hub_download('$MODEL_ID', 'config.json'); print(json.dumps(json.load(open(path)), indent=2))"
```

2. List repo files:
```bash
python -c "from huggingface_hub import list_repo_files; [print(f) for f in list_repo_files('$MODEL_ID')]"
```

3. If the model has modeling code on HuggingFace, fetch and read it to understand:
   - Main components (AR model, decoder, vocoder, flow, etc.)
   - Input format (text tokens, phonemes, etc.)
   - Intermediate representation (codec codes, mel, etc.)
   - Output format (waveform)
   - Codec frame rate

4. Write analysis to `$WORK_DIR/analysis.md`

5. Determine stages:
   - Stage 0: AR model (text -> codec) with worker_type: ar
   - Stage 1: Decoder (codec -> waveform) with worker_type: generation

## Phase 2: Generate Code

**FIRST** read these reference files:
- `$VLLM_DIR/vllm_omni/model_executor/stage_configs/qwen3_tts.yaml`
- `$VLLM_DIR/vllm_omni/model_executor/stage_configs/qwen3_tts_async_chunk.yaml`
- `$VLLM_DIR/vllm_omni/model_executor/stage_input_processors/qwen3_tts.py`
- `$VLLM_DIR/vllm_omni/model_executor/models/qwen3_tts/` (all files)
- `$VLLM_DIR/docs/models/tts_developer_guide.md` (if exists)

Then generate:

1. **Stage config YAML**: `$VLLM_DIR/vllm_omni/model_executor/stage_configs/<model>.yaml`
2. **Async chunk config**: `$VLLM_DIR/vllm_omni/model_executor/stage_configs/<model>_async_chunk.yaml`
3. **Stage input processor**: `$VLLM_DIR/vllm_omni/model_executor/stage_input_processors/<model>.py`
4. **Model wrapper**: `$VLLM_DIR/vllm_omni/model_executor/models/<model>/`
5. **Model registration**: Update `$VLLM_DIR/vllm_omni/model_executor/models/__init__.py`

## Phase 3: Build Check

```bash
cd $VLLM_DIR
python -m py_compile vllm_omni/model_executor/stage_input_processors/<model>.py
python -m py_compile vllm_omni/model_executor/models/<model>/__init__.py
ruff check vllm_omni/model_executor/models/<model>/ vllm_omni/model_executor/stage_input_processors/<model>.py
python -c "import vllm_omni; print('import OK')"
```

If any check fails, fix the code and re-run. Do NOT proceed to Phase 4 until all checks pass.

## Phase 4: Offline Inference Test

Write and run a test script:

```python
import sys
sys.path.insert(0, "$VLLM_DIR")
from vllm_omni.entrypoints.omni import Omni

omni = Omni(model="$MODEL_ID")
outputs = omni.generate("Hello, this is a test of the new TTS model.")
audio = outputs[0].request_output[0].audio
audio.save("$WORK_DIR/test_output.wav")
print(f"Duration: {audio.duration:.2f}s")
```

If this fails, read the full traceback, diagnose, fix, and retry from Phase 3.

## Phase 5: ASR Verification (Self-Check)

Uses OpenAI `gpt-4o-mini-transcribe` API. Reads key from `~/proj/tts-integration-agent/.env`.

```bash
python ~/proj/tts-integration-agent/scripts/verify_tts.py \
  --audio $WORK_DIR/test_output.wav \
  --expected-text "Hello, this is a test of the new TTS model."
```

Result interpretation:
- **PASS (WER < 0.3)**: Move to Phase 6
- **MARGINAL (WER 0.3-0.5)**: Investigate decoder quality, try different test sentence
- **FAIL (WER > 0.5)**: Major issue. Check AR stage output, codec mapping, decoder

If FAIL, log the error to `$ITER_LOG` and go back to Phase 2 with the diagnosis.

## Phase 6: Full Validation

Run 3 test sentences to confirm consistency:

```
"The quick brown fox jumps over the lazy dog."
"Welcome to the text to speech integration test."
"Today is a beautiful day for natural language processing."
```

For each, run Phase 4 + Phase 5. All must pass.

Then run ruff format:
```bash
cd $VLLM_DIR
ruff format vllm_omni/model_executor/models/<model>/ vllm_omni/model_executor/stage_input_processors/<model>.py
```

## Iteration Protocol

On ANY failure:
1. Log to `$ITER_LOG`: iteration number, failed phase, error message, diagnosis
2. Increment iteration counter
3. If iteration > $MAX_ITER: STOP and report. Ask human for help.
4. Fix the code based on diagnosis
5. Go back to the failed phase

## Completion

When all 3 test sentences pass ASR verification:
1. Write a summary to `$WORK_DIR/report.md`
2. List all files created/modified
3. Show the verification results
4. Suggest next steps (e2e tests, online serving test, PR)

## Rules

- NEVER modify existing Qwen3-TTS files
- ALWAYS read reference code before generating new code
- Follow ruff style (120 char line limit)
- Log every iteration
- Stop after $MAX_ITER failures
