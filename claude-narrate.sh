#!/bin/bash
# Claude Code Narration Hook - PostToolUse
# Narrates Claude responses using VOICEVOX

SAY_SCRIPT="$HOME/.claude/skills/voicebox-narrator/say.sh"
SPEAKER=${SPEAKER:-1}  # Default: ずんだもん (あまあま)
LOG_FILE="/tmp/claude-narrate.log"

# Logging for debug
log() {
    echo "[$(date '+%H:%M:%S')] $1" >> "$LOG_FILE"
}

# Ensure worker is running
if ! pgrep -f "voicebox-narrator/worker.sh" > /dev/null; then
    log "Starting voicebox worker..."
    "$HOME/.claude/skills/voicebox-narrator/worker.sh" > /dev/null 2>&1 &
    sleep 0.3
fi

# Read input from stdin (Claude Code hook system)
INPUT=$(cat)

log "Hook input received"

# Extract message content from JSON
MESSAGE=$(echo "$INPUT" | python3 -c "
import sys
import json

try:
    data = json.load(sys.stdin)

    # Try different fields for message content
    content = (
        data.get('content', '') or
        data.get('message', '') or
        data.get('response', '') or
        data.get('result', '') or
        ''
    )

    # Handle result object
    if not content and isinstance(data.get('result'), dict):
        content = data['result'].get('content', '')

    # Handle output field
    if not content:
        content = data.get('output', '')

    print(content)
except Exception as e:
    sys.stderr.write(str(e))
    print('')
" 2<<< "$INPUT")

# Log for debug
log "Message length: ${#MESSAGE}"

# Skip if no content or too short
if [ -z "$MESSAGE" ]; then
    log "No content to narrate"
    exit 0
fi

# Clean control characters and truncate
CLEANED=$(echo "$MESSAGE" | sed 's/[[:cntrl:]]/ /g' | sed 's/  */ /g' | sed 's/^ *//;s/ *$//' | head -c 200)

if [ ${#CLEANED} -lt 10 ]; then
    log "Message too short: ${#CLEANED} chars"
    exit 0
fi

# Send to voicebox for narration
log "Narrating: ${CLEANED:0:50}..."
"$SAY_SCRIPT" "$CLEANED" "$SPEAKER" 2>/dev/null &

exit 0
