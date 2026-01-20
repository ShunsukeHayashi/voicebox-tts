#!/bin/bash
# voicebox-tts System - Status Script
# 状態確認スクリプト

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[!]${NC} $1"; }
log_error() { echo -e "${RED}[✗]${NC} $1"; }

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_DIR="$PROJECT_ROOT/tmp"

API_PORT=5001
FLOWER_PORT=5555

echo ""
echo "============================================================"
echo "          voicebox-tts System Status"
echo "============================================================"
echo ""

# Redis
log_info "Redis:"
if brew services list | grep -q "redis.*started"; then
    log_success "Running"
    redis-cli ping > /dev/null 2>&1 && echo "   - Ping: PONG" || echo "   - Ping: Connection error"
else
    log_error "Stopped"
fi

echo ""

# Celery Worker
log_info "Celery Worker:"
if [ -f "$PID_DIR/celery.pid" ]; then
    pid=$(cat "$PID_DIR/celery.pid")
    if kill -0 "$pid" 2>/dev/null; then
        log_success "Running (PID: $pid)"
        count=$(ps aux | grep -c "$pid" || echo "0")
        echo "   - Processes: $count"
    else
        log_error "PID file exists but process not found"
        rm -f "$PID_DIR/celery.pid"
    fi
else
    log_error "Stopped (no PID file)"
fi

celery_pids=$(pgrep -f "celery.*worker.*celery_worker" 2>/dev/null || true)
if [ -n "$celery_pids" ]; then
    count=$(echo "$celery_pids" | wc -w | tr -d ' ')
    log_warn "Orphaned processes: $count"
fi

echo ""

# API Server
log_info "API Server:"
if [ -f "$PID_DIR/api.pid" ]; then
    pid=$(cat "$PID_DIR/api.pid")
    if kill -0 "$pid" 2>/dev/null; then
        if curl -s "http://localhost:$API_PORT/health" > /dev/null 2>&1; then
            log_success "Running (PID: $pid, Port: $API_PORT)"
        else
            log_warn "Running but health check failed"
        fi
    else
        log_error "PID file exists but process not found"
        rm -f "$PID_DIR/api.pid"
    fi
else
    log_error "Stopped (no PID file)"
fi

echo ""

# Flower
log_info "Flower:"
if [ -f "$PID_DIR/flower.pid" ]; then
    pid=$(cat "$PID_DIR/flower.pid")
    if kill -0 "$pid" 2>/dev/null; then
        if curl -s "http://localhost:$FLOWER_PORT" > /dev/null 2>&1; then
            log_success "Running (PID: $pid, Port: $FLOWER_PORT)"
        else
            log_warn "Running but health check failed"
        fi
    else
        log_error "PID file exists but process not found"
        rm -f "$PID_DIR/flower.pid"
    fi
else
    log_error "Stopped (no PID file)"
fi

echo ""
echo "============================================================"

# Summary
total=0
if [ -f "$PID_DIR/celery.pid" ] && kill -0 "$(cat "$PID_DIR/celery.pid")" 2>/dev/null; then
    total=$((total + 1))
fi
if [ -f "$PID_DIR/api.pid" ] && kill -0 "$(cat "$PID_DIR/api.pid")" 2>/dev/null; then
    total=$((total + 1))
fi
if [ -f "$PID_DIR/flower.pid" ] && kill -0 "$(cat "$PID_DIR/flower.pid")" 2>/dev/null; then
    total=$((total + 1))
fi

log_info "Services Running: $total/3"
echo ""
echo "Access URLs:"
echo "  - API Server:  http://localhost:$API_PORT/health"
echo "  - Flower:       http://localhost:$FLOWER_PORT"
echo ""
