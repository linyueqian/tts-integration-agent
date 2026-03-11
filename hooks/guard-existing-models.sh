#!/bin/bash
# Prevent the agent from modifying existing model implementations.
# Only new model directories should be created/edited.

PROTECTED_MODELS=(
    "qwen3_tts"
    "qwen3_omni"
    "cosyvoice3"
    "stable_audio"
    "mimo_audio"
    "fish_speech"
)

# Read the file path from the tool input (passed via stdin as JSON)
FILE_PATH=$(cat | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('file_path',''))" 2>/dev/null)

if [ -z "$FILE_PATH" ]; then
    exit 0  # No file path, allow
fi

for model in "${PROTECTED_MODELS[@]}"; do
    if echo "$FILE_PATH" | grep -q "models/${model}/"; then
        echo "BLOCKED: Cannot modify existing model '${model}'. Only create new model directories."
        exit 1
    fi
done

exit 0
