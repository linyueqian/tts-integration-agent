---
name: tts-integrate
description: Integrate a new TTS model into vLLM-Omni. Use when given a HuggingFace TTS model ID and asked to add support for it. This skill runs a self-verifying loop: analyze, generate code, test, verify with ASR, and iterate on failures.
---

# TTS Model Integration Agent

You are a TTS integration agent. Your job is to take a HuggingFace TTS model and integrate it into vLLM-Omni, verifying your work with ASR at each step.

## Reference Implementations

vLLM-Omni has two fully working TTS integrations to learn from:

### Qwen3-TTS (single-AR, 12Hz codec)
- **Architecture**: Single AR talker + code predictor -> Code2Wav decoder
- **Stage 0**: `qwen3_tts` (worker_type: ar) -- generates codec codes
- **Stage 1**: `code2wav` (worker_type: generation) -- decodes to 24kHz audio
- **Files**:
  - `~/proj/vllm-omni/vllm_omni/model_executor/stage_configs/qwen3_tts.yaml`
  - `~/proj/vllm-omni/vllm_omni/model_executor/models/qwen3_tts/`
  - `~/proj/vllm-omni/vllm_omni/model_executor/stage_input_processors/qwen3_tts.py`

### Fish Speech S2 Pro (dual-AR, DAC codec, 44.1kHz)
- **Architecture**: Slow AR (4B, semantic tokens) + Fast AR (residual codebooks) -> DAC decoder
- **Stage 0**: `fish_speech_slow_ar` (worker_type: ar) -- dual-AR with embedded fast AR loop
- **Stage 1**: `dac_decoder` (worker_type: generation) -- DAC codec -> 44.1kHz audio
- **Key differences from Qwen3-TTS**:
  - Dual-AR: Slow AR generates semantic tokens, Fast AR fills 9 residual codebooks per frame
  - Uses interleaved (GPT-J) RoPE, NOT NeoX style
  - Codebook embedding normalization: `sum / sqrt(num_codebooks + 1)`
  - DAC codec with 10 codebooks (1 semantic + 9 residual)
  - Chat template prompt with `<|voice|>` modality marker
  - Voice cloning via DAC-encoded reference audio as system message
- **Files**:
  - `~/proj/vllm-omni/vllm_omni/model_executor/stage_configs/fish_speech_s2_pro.yaml`
  - `~/proj/vllm-omni/vllm_omni/model_executor/models/fish_speech/`
  - `~/proj/vllm-omni/vllm_omni/model_executor/stage_input_processors/fish_speech.py`
  - `~/proj/vllm-omni/vllm_omni/model_executor/models/fish_speech/dac_encoder.py` (voice cloning)

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
   - What are the main components? (AR model, decoder, vocoder, flow model, dual-AR, etc.)
   - What is the input format? (text tokens, phonemes, chat template, etc.)
   - What is the intermediate representation? (codec codes, mel spectrograms, etc.)
   - What is the output? (waveform, codec codes, etc.)
   - What is the codec frame rate and sample rate?
   - How many codebooks? (single codebook, multi-codebook, RVQ, etc.)

4. **Check for reference implementations** -- search GitHub for existing integrations:
   - sglang-omni, original model repo, other inference frameworks
   - These reveal critical details: RoPE style, normalization, token mappings

5. Determine stage boundaries:
   - Stage 0: AR model (text -> codec codes) - worker_type: ar
   - Stage 1: Decoder (codec codes -> waveform) - worker_type: generation

6. Identify the architecture pattern:
   - **Single-AR** (like Qwen3-TTS): One AR model generates all codebooks
   - **Dual-AR** (like Fish Speech): Slow AR for semantic + Fast AR for residual codebooks
   - **Flow/DiT**: Non-autoregressive decoder

### Phase 2: Generate Integration Code

Read BOTH reference implementations first:
- `~/proj/vllm-omni/vllm_omni/model_executor/stage_configs/qwen3_tts.yaml`
- `~/proj/vllm-omni/vllm_omni/model_executor/stage_configs/fish_speech_s2_pro.yaml`
- `~/proj/vllm-omni/vllm_omni/model_executor/stage_input_processors/qwen3_tts.py`
- `~/proj/vllm-omni/vllm_omni/model_executor/stage_input_processors/fish_speech.py`
- `~/proj/vllm-omni/vllm_omni/model_executor/models/qwen3_tts/` (all files)
- `~/proj/vllm-omni/vllm_omni/model_executor/models/fish_speech/` (all files)
- `~/proj/vllm-omni/vllm_omni/entrypoints/openai/serving_speech.py` (online serving)
- `~/proj/vllm-omni/docs/models/tts_developer_guide.md` (if exists)

Generate these files for the new model:

1. **Stage config YAML** at `stage_configs/<model_name>.yaml`:
   - Follow the pattern closest to your model (Qwen3-TTS or Fish Speech)
   - Set correct model_stage names, model_arch, worker_type
   - Configure default_sampling_params (temperature, top_k, max_tokens, stop_token_ids)
   - Set async_chunk and connector config for streaming

2. **Stage input processor** at `stage_input_processors/<model_name>.py`:
   - Implement async chunk function for streaming
   - Buffer codec codes in connector, emit at configured chunk_size
   - Handle codebook-major vs frame-major layout

3. **Model wrapper** at `models/<model_name>/`:
   - AR model wrapper with proper RoPE style and embedding handling
   - Decoder wrapper with `forward()` returning `OmniOutput`
   - Configuration class (if custom config needed)
   - Register in model registry

4. **Online serving** -- update `serving_speech.py`:
   - Add model_stage to `_TTS_MODEL_STAGES`
   - Add model-specific prompt builder if needed (like `_build_fish_speech_prompt`)
   - Handle voice cloning if the model supports it

5. **E2E test script** at `examples/offline_inference/<model_name>/end2end.py`

### Phase 3: Build Verification

```bash
cd ~/proj/vllm-omni
python -m py_compile vllm_omni/model_executor/stage_input_processors/<model_name>.py
python -m py_compile vllm_omni/model_executor/models/<model_name>/__init__.py
ruff check vllm_omni/model_executor/models/<model_name>/
ruff check vllm_omni/model_executor/stage_input_processors/<model_name>.py
python -c "import vllm_omni; print('OK')"
```

### Phase 4: Offline Inference Test

Write and run a test script. If it fails, use the debugging checklist below.

### Phase 5: ASR Verification (Self-Check)

```bash
python ~/proj/tts-integration-agent/scripts/verify_tts.py \
  --audio ~/proj/tts-integration-agent/workspace/test_output.wav \
  --expected-text "Hello, this is a test of the new TTS model."
```

Interpretation:
- **WER < 0.3**: PASS
- **WER 0.3-0.5**: MARGINAL -- check decoder quality
- **WER > 0.5**: FAIL -- major issue, use debugging checklist

### Phase 6: Online Serving Test

After offline works, test online serving:
1. Start server with the new model's stage config
2. Test `/v1/audio/speech` endpoint
3. Test streaming if async_chunk is enabled
4. Test voice cloning if supported

### Phase 7: Iterate on Failures

Maximum 5 iterations. Log every attempt.

## Debugging Checklist (from real integration experience)

When audio output is noise, garbage, or unintelligible, check these IN ORDER:

### 1. RoPE Style (most common silent killer)
- **Symptom**: Audio has tonal patterns but no speech ("owl sounds"), or pure noise
- **Check**: Does the model use NeoX-style or interleaved (GPT-J) RoPE?
  - vLLM defaults to NeoX style (`is_neox_style=True`)
  - Many models (Fish Speech, LLaMA variants) use interleaved (`is_neox_style=False`)
- **How to verify**: Check the original model's RoPE implementation or reference inference code
- **Fix**: Override `is_neox_style=False` in attention layers

### 2. Embedding Normalization
- **Symptom**: Audio is noisy, model generates mostly the same tokens
- **Check**: Does the model normalize codebook embeddings?
  - Common pattern: `(text_embed + sum(codebook_embeds)) / sqrt(num_codebooks + 1)`
  - Without this, codebook embeddings dominate (~4x larger than text embeddings)
- **How to verify**: Check reference model's `embed_one_token()` or equivalent
- **Fix**: Add sqrt normalization in the embedding path

### 3. Codec Configuration
- **Symptom**: Audio too long/short, timing is wrong, context overlap creates artifacts
- **Check**: Is the hop length correct?
  - Hop length = product of decoder rates x product of quantizer downsample factors
  - Example: Fish Speech DAC: 512 (decoder) x 4 (quantizer) = 2048, NOT just 512
- **How to verify**: Read the codec model architecture, compute from rate products
- **Fix**: Set correct `_HOP_LENGTH` constant

### 4. Token ID Mapping
- **Symptom**: Model outputs seem random, logits don't match expected vocabulary
- **Check**: Are semantic/codec token IDs correct?
  - Verify token ID ranges match the tokenizer
  - Check masking: only allow valid token ranges during generation
- **How to verify**: `tokenizer.encode("<|semantic:0|>")` etc.

### 5. Sampling Parameters
- **Symptom**: Repetitive output, or doesn't stop generating
- **Check**:
  - `repetition_penalty`: vLLM applies globally (not windowed like some reference impls)
  - `stop_token_ids`: Model may never naturally emit EOS -- bound with `max_tokens`
  - `temperature`/`top_k`/`top_p`: Match reference implementation

### 6. Codebook Layout
- **Symptom**: Audio is garbled but has speech-like rhythm
- **Check**: Is the codebook layout codebook-major or frame-major?
  - Codebook-major: `[cb0_f0, cb0_f1, ..., cb1_f0, cb1_f1, ...]`
  - Frame-major: `[cb0_f0, cb1_f0, ..., cb0_f1, cb1_f1, ...]`
- **Fix**: Ensure stage input processor and decoder agree on layout

### 7. Dtype Issues
- **Symptom**: All silence, or NaN audio values
- **Check**: Some decoders require float32 (not float16/bfloat16)
- **Fix**: Use `torch.cuda.amp.autocast(dtype=torch.float32)` for decoder

## Voice Cloning Pattern

For models that support voice cloning (like Fish Speech S2 Pro):

1. **Encode reference audio** with the model's codec (e.g., DAC encode -> VQ codes)
2. **Convert to token IDs** (e.g., semantic codes -> `SEMANTIC_TOKEN_OFFSET + code_value`)
3. **Prepend as system message** in the prompt (with reference transcript)
4. **In serving_speech.py**: Load codec on CPU, encode lazily, cache the codec

Example prompt format (Fish Speech):
```
<|im_start|>system
<|speaker:0|>{ref_text}<|audio_start|>{semantic_tokens}<|audio_end|><|im_end|>
<|im_start|>user
<|speaker:0|>{text_to_synthesize}<|im_end|>
<|im_start|>assistant
<|voice|>
```

## Important Rules

- Always read existing reference code before generating new code
- Never modify existing model files (Qwen3-TTS, Fish Speech, etc.)
- Always compare with reference implementations (sglang, original repo)
- Follow the same code style (ruff, 120 char line limit)
- Test with at least 3 different sentences before declaring success
- Log every iteration's result for debugging
- Check RoPE style FIRST when debugging audio issues
