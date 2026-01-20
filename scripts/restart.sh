#!/bin/bash
# voicebox-tts System - Restart Script
# 再起動スクリプト

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
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

log_info "voicebox-tts システム再起動中..."

# 停止
log_info "1/2 システム停止..."
"$SCRIPT_DIR/stop.sh"

# 待機
sleep 2

# 起動
log_info "2/2 システム起動..."
"$SCRIPT_DIR/start.sh"

echo ""
log_success "🎉 voicebox-tts システム再起動完了！"
echo ""
