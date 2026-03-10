#!/bin/bash
# Log bash command outputs during the integration loop.
# Appends to workspace/bash_log.txt for post-mortem debugging.

LOG_DIR="$HOME/proj/tts-integration-agent/workspace"
LOG_FILE="$LOG_DIR/bash_log.txt"

mkdir -p "$LOG_DIR"

# Read tool result from stdin
INPUT=$(cat)

# Append timestamp and output
echo "--- $(date -Iseconds) ---" >> "$LOG_FILE"
echo "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    cmd = d.get('command', 'unknown')
    stdout = d.get('stdout', '')
    stderr = d.get('stderr', '')
    print(f'CMD: {cmd}')
    if stdout:
        print(f'OUT: {stdout[:500]}')
    if stderr:
        print(f'ERR: {stderr[:500]}')
except:
    pass
" >> "$LOG_FILE" 2>/dev/null

exit 0
