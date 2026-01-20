#!/bin/bash
# voicebox-tts System - Start Script
# 一括起動スクリプト

set -e

# 色付きログ
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# プロジェクトルート
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_DIR="$PROJECT_ROOT/tmp"
VOICEBOX_DIR="$HOME/voicebox"

# ポート設定
API_PORT=5001
FLOWER_PORT=5555
CELERY_CONCURRENCY=10

log_info "voicebox-tts システム起動中..."

# PIDディレクトリ作成
mkdir -p "$PID_DIR"
mkdir -p "$VOICEBOX_DIR"

# Redis起動確認
log_info "Redis起動確認..."
if brew services list | grep -q "redis.*started"; then
    log_success "Redis起動済み"
else
    log_info "Redisを起動します..."
    brew services start redis
    sleep 2
fi

# Redis接続確認
if ! redis-cli ping > /dev/null 2>&1; then
    log_error "Redis起動に失敗しました"
    exit 1
fi

# 既存プロセスチェック
check_existing() {
    local service=$1
    local pid_file="$PID_DIR/$service.pid"

    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            log_warn "$service は既に起動しています (PID: $pid)"
            return 0
        else
            rm -f "$pid_file"
        fi
    fi
    return 1
}

# Celery Worker起動
log_info "Celery Worker起動中..."
check_existing "celery" || {
    cd "$PROJECT_ROOT"
    celery -A celery_worker worker \
        --loglevel=info \
        --pidfile="$PID_DIR/celery.pid" \
        --logfile="$PID_DIR/celery.log" \
        --concurrency=$CELERY_CONCURRENCY \
        > "$PID_DIR/celery.out" 2>&1 &

    CELERY_PID=$!
    echo $CELERY_PID > "$PID_DIR/celery.pid"

    sleep 3

    if kill -0 $CELERY_PID 2>/dev/null; then
        log_success "Celery Worker起動完了 (Concurrency: $CELERY_CONCURRENCY, PID: $CELERY_PID)"
    else
        log_error "Celery Worker起動に失敗しました"
        cat "$PID_DIR/celery.out" 2>/dev/null || cat "$PID_DIR/celery.log" 2>/dev/null
        exit 1
    fi
}

# API Server起動
log_info "API Server起動中..."
check_existing "api" || {
    cd "$PROJECT_ROOT"
    API_PORT=$API_PORT python3 api_server.py \
        > "$PID_DIR/api.log" 2>&1 &

    API_PID=$!
    echo $API_PID > "$PID_DIR/api.pid"

    sleep 2

    if kill -0 $API_PID 2>/dev/null; then
        log_success "API Server起動完了 (Port: $API_PORT, PID: $API_PID)"
    else
        log_error "API Server起動に失敗しました"
        cat "$PID_DIR/api.log"
        exit 1
    fi
}

# Flower起動
log_info "Flower起動中..."
check_existing "flower" || {
    cd "$PROJECT_ROOT"
    celery -A celery_worker --broker=redis://localhost:6379/0 flower \
        --port=$FLOWER_PORT \
        > "$PID_DIR/flower.log" 2>&1 &

    FLOWER_PID=$!
    echo $FLOWER_PID > "$PID_DIR/flower.pid"

    sleep 3

    if kill -0 $FLOWER_PID 2>/dev/null; then
        log_success "Flower起動完了 (Port: $FLOWER_PORT, PID: $FLOWER_PID)"
    else
        log_error "Flower起動に失敗しました"
        cat "$PID_DIR/flower.log"
        exit 1
    fi
}

# ヘルスチェック
log_info "ヘルスチェック中..."
sleep 2

# API Server
if curl -s http://localhost:$API_PORT/health > /dev/null 2>&1; then
    log_success "✓ API Server (http://localhost:$API_PORT)"
else
    log_error "✗ API Server ヘルスチェック失敗"
fi

# Redis
if redis-cli ping > /dev/null 2>&1; then
    log_success "✓ Redis"
else
    log_error "✗ Redis ヘルスチェック失敗"
fi

# Celery Worker
if [ -f "$PID_DIR/celery.pid" ] && kill -0 "$(cat "$PID_DIR/celery.pid")" 2>/dev/null; then
    log_success "✓ Celery Worker (PID: $(cat $PID_DIR/celery.pid))"
else
    log_error "✗ Celery Worker ヘルスチェック失敗"
fi

# Flower
if [ -f "$PID_DIR/flower.pid" ] && kill -0 "$(cat "$PID_DIR/flower.pid")" 2>/dev/null; then
    log_success "✓ Flower (http://localhost:$FLOWER_PORT)"
else
    log_error "✗ Flower ヘルスチェック失敗"
fi

echo ""
log_success "🎉 voicebox-tts システム起動完了！"
echo ""
echo "📍 アクセス先:"
echo "   - API Server:  http://localhost:$API_PORT"
echo "   - Flower:       http://localhost:$FLOWER_PORT"
echo ""
echo "📋 コマンド:"
echo "   ./scripts/stop.sh    - システム停止"
echo "   ./scripts/status.sh  - 状態確認"
echo "   ./scripts/restart.sh - 再起動"
echo ""
