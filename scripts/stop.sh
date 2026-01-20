#!/bin/bash
# voicebox-tts System - Stop Script
# 一括停止スクリプト

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

log_info "voicebox-tts システム停止中..."

# PIDファイル読み込み
stop_service() {
    local service=$1
    local pid_file="$PID_DIR/$service.pid"

    if [ ! -f "$pid_file" ]; then
        log_warn "$service: PIDファイルが存在しません"
        return 1
    fi

    local pid=$(cat "$pid_file")

    if ! kill -0 "$pid" 2>/dev/null; then
        log_warn "$service: プロセスが存在しません (PID: $pid)"
        rm -f "$pid_file"
        return 1
    fi

    log_info "$service: 停止中... (PID: $pid)"

    # Graceful shutdown (SIGTERM)
    kill "$pid" 2>/dev/null || true

    # タイムアウト待機
    local count=0
    while kill -0 "$pid" 2>/dev/null && [ $count -lt 10 ]; do
        sleep 1
        count=$((count + 1))
    done

    # 強制終了 (SIGKILL)
    if kill -0 "$pid" 2>/dev/null; then
        log_warn "$service: 強制終了します..."
        kill -9 "$pid" 2>/dev/null || true
        sleep 1
    fi

    if kill -0 "$pid" 2>/dev/null; then
        log_error "$service: 停止に失敗しました"
        return 1
    fi

    rm -f "$pid_file"
    log_success "$service: 停止完了"
    return 0
}

# 各サービス停止
stop_service "flower"
stop_service "api"
stop_service "celery"

# 残存プロセスクリーンアップ
log_info "残存プロセス確認中..."
cleanup_pids=(
    $(pgrep -f "celery.*worker.*celery_worker" || true)
    $(pgrep -f "api_server.py" || true)
    $(pgrep -f "celery.*flower" || true)
)

if [ -n "${cleanup_pids[*]}" ]; then
    log_warn "残存プロセスを停止します"
    for pid in "${cleanup_pids[@]}"; do
        if kill -0 "$pid" 2>/dev/null; then
            kill -9 "$pid" 2>/dev/null || true
        fi
    done
    log_success "クリーンアップ完了"
fi

echo ""
log_success "🎉 voicebox-tts システム停止完了！"
echo ""
