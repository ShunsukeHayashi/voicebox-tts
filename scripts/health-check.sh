#!/bin/bash
# VoiceBox Health Check & Auto-Recovery Script
# システム健全性をチェックし、問題があれば自動復旧

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

API_URL="${VOICEBOX_API_URL:-http://localhost:5001}"
VOICEVOX_URL="${VOICEVOX_API_URL:-http://localhost:50021}"
LOG_FILE="$HOME/dev/voicebox-tts/tmp/health-check.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# チェック関数
check_api() {
    if curl -s -f "$API_URL/health" > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} API Server"
        return 0
    else
        echo -e "${RED}✗${NC} API Server"
        return 1
    fi
}

check_voicovox() {
    if curl -s -f "$VOICEVOX_URL/version" > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} VOICEVOX"
        return 0
    else
        echo -e "${RED}✗${NC} VOICEVOX"
        return 1
    fi
}

check_redis() {
    if redis-cli ping > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Redis"
        return 0
    else
        echo -e "${RED}✗${NC} Redis"
        return 1
    fi
}

check_celery() {
    if pgrep -f "celery.*worker" > /dev/null; then
        echo -e "${GREEN}✓${NC} Celery Worker"
        return 0
    else
        echo -e "${RED}✗${NC} Celery Worker"
        return 1
    fi
}

# メイン処理
log "Health check started"

echo "=== VoiceBox Health Check ==="

FAILED=0

check_api || FAILED=$((FAILED + 1))
check_voicovox || FAILED=$((FAILED + 1))
check_redis || FAILED=$((FAILED + 1))
check_celery || FAILED=$((FAILED + 1))

if [ $FAILED -eq 0 ]; then
    log "All systems healthy"
    exit 0
else
    log "Health check failed: $FAILED system(s) down"

    # 自動復旧試行
    log "Attempting auto-recovery..."
    cd "$HOME/dev/voicebox-tts"
    ./scripts/restart.sh > /dev/null 2>&1

    if [ $? -eq 0 ]; then
        log "Auto-recovery successful"
        exit 0
    else
        log "Auto-recovery failed"
        exit 1
    fi
fi
