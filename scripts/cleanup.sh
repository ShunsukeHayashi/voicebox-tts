#!/bin/bash
# VoiceBox Auto-Cleanup Script
# 古い音声ファイルとRedisキャッシュを自動クリーンアップ

set -e

VOICEBOX_DIR="${HOME}/voicebox"
DAYS_TO_KEEP=7  # 7日以内のファイルは保持
MAX_FILES=100   # 最大100ファイルまで保持

echo "[$(date '+%Y-%m-%d %H:%M:%S')] VoiceBox cleanup started"

# 1. 古い音声ファイルの削除
echo "Cleaning audio files older than ${DAYS_TO_KEEP} days..."
find "$VOICEBOX_DIR" -name "task_*.wav" -mtime +$DAYS_TO_KEEP -delete 2>/dev/null || true

# 2. ファイル数制限（古い順に削除）
FILE_COUNT=$(ls "$VOICEBOX_DIR"/task_*.wav 2>/dev/null | wc -l)
if [ $FILE_COUNT -gt $MAX_FILES ]; then
    echo "Too many files ($FILE_COUNT). Keeping latest $MAX_FILES..."
    ls -t "$VOICEBOX_DIR"/task_*.wav | tail -n +$(($MAX_FILES + 1)) | xargs rm -f 2>/dev/null || true
fi

# 3. Redisキャッシュのクリア（古いタスク結果）
echo "Cleaning Redis cache..."
redis-cli --scan --pattern "celery-task-meta-*" | head -n 1000 | xargs redis-cli DEL > /dev/null 2>&1 || true

# 4. ディスク容量レポート
FINAL_SIZE=$(du -sh "$VOICEBOX_DIR" 2>/dev/null | cut -f1)
FINAL_COUNT=$(ls "$VOICEBOX_DIR"/task_*.wav 2>/dev/null | wc -l)

echo "Cleanup completed: $FINAL_COUNT files, $FINAL_SIZE"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] VoiceBox cleanup finished"
echo ""
