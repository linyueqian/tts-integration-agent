# TTS Integration Agent

Claude Code plugin for onboarding new TTS models into vLLM-Omni. Self-verifying and self-iterating.

## Architecture

This is a **Claude Code plugin** (similar to [humanize](https://github.com/humania-org/humanize)). Claude Code IS the agent, guided by commands and protected by hooks.

```
/integrate <hf_model_id>
        |
  [1. Analyze]    Fetch HF config, read modeling code, identify stages
        |
  [2. Generate]   Write YAML, stage processor, model wrapper (reference: existing TTS models)
        |
  [3. Build]      Syntax check, ruff, import test
        |
  [4. Test]       Offline inference -> audio file
        |
  [5. Verify]     OpenAI ASR (gpt-4o-mini-transcribe) -> transcribe -> compute WER
        |
   pass / fail
        |
  [6. Iterate]    Diagnose, fix code, loop back (max 5 iterations)
```

## Setup

1. Clone next to vllm-omni:
   ```bash
   cd ~/proj
   git clone <this-repo> tts-integration-agent
   ```

2. Create `.env` with your OpenAI API key (for ASR verification):
   ```bash
   echo "OPENAI_API_KEY=sk-..." > ~/proj/tts-integration-agent/.env
   ```

3. Start Claude Code and invoke:
   ```
   cd ~/proj/tts-integration-agent
   claude
   /integrate <hf_model_id>
   ```

## Commands

| Command | Description |
|---------|-------------|
| `/integrate <model_id>` | Full integration loop with self-verification |
| `/analyze <model_id>` | Architecture analysis only (no code gen) |
| `/verify <audio> <text>` | ASR-verify a single audio file |

## Hooks

| Hook | Trigger | Purpose |
|------|---------|---------|
| guard-existing-models | PreToolUse (Edit/Write) | Prevent modifying existing model code |
| log-iteration | PostToolUse (Bash) | Log all bash outputs for debugging |

## Self-Verification

After generating speech, the agent sends the output to OpenAI's `gpt-4o-mini-transcribe` and computes Word Error Rate against the input text:

- **WER < 0.3**: PASS
- **WER 0.3-0.5**: MARGINAL
- **WER > 0.5**: FAIL (auto-iterate)

No local ASR model needed. Just an OpenAI API key.

## Project Structure

```
tts-integration-agent/
  .claude/CLAUDE.md              # Plugin instructions
  .env                           # OPENAI_API_KEY (gitignored)
  commands/
    integrate.md                 # /integrate command (main loop)
    analyze.md                   # /analyze command
    verify.md                    # /verify command
  hooks/
    hooks.json                   # Hook configuration
    guard-existing-models.sh     # Prevent modifying existing models
    log-iteration.sh             # Log bash outputs
  skills/
    tts-integrate/SKILL.md       # Domain knowledge skill
  scripts/
    verify_tts.py                # Standalone ASR verification (OpenAI API)
  workspace/                     # Test artifacts (gitignored)
```
