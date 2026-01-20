#!/bin/bash
# Test 3: メモリ使用量テスト

echo "=========================================="
echo "Test 3: Memory Usage Test"
echo "=========================================="
echo ""

API_URL="http://localhost:5001"
TASK_COUNT=50

# 初期状態
echo "【初期状態】"
echo "Redisメモリ:"
redis-cli INFO memory | grep used_memory_human
echo "音声ファイル数:"
ls ~/voicebox/task_*.wav 2>/dev/null | wc -l
echo ""

# タスク送信
echo "【${TASK_COUNT}タスク送信中】"
for i in $(seq 1 $TASK_COUNT); do
  voicebox "メモリテスト${i}番目です。" 3 > /dev/null 2>&1
done
echo "送信完了"
echo ""

# 処理待機
echo "【バックグラウンド処理待機】"
sleep 30
echo ""

# 処理後の状態
echo "【処理後の状態】"
echo "Redisメモリ:"
redis-cli INFO memory | grep used_memory_human
echo "音声ファイル数:"
ls ~/voicebox/task_*.wav 2>/dev/null | wc -l
echo "ディスク容量:"
du -sh ~/voicebox
echo ""

# メモリリークチェック
echo "=========================================="
echo "メモリリーク判定"
echo "=========================================="
REDIS_MEM=$(redis-cli INFO memory | grep used_memory_human | awk '{print $2}')
echo "Redis使用量: $REDIS_MEM"

if [[ "$REDIS_MEM" == *"M"* ]]; then
  MEM_VALUE=$(echo "$REDIS_MEM" | sed 's/M//')
  if (( $(echo "$MEM_VALUE < 10" | bc -l) )); then
    echo "✅ メモリ使用量: 正常 (< 10MB)"
  else
    echo "⚠️  メモリ使用量: 要注意"
  fi
fi
echo ""

echo "✅ Test 3 Complete"
echo ""
