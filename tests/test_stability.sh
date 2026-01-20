#!/bin/bash
# Test 5: 長時間安定性テスト

echo "=========================================="
echo "Test 5: Long-Running Stability Test"
echo "=========================================="
echo ""

API_URL="http://localhost:5001"
TASK_COUNT=100

# 開始時刻記録
TEST_START=$(date +%s)
echo "テスト開始: $(date '+%Y-%m-%d %H:%M:%S')"
echo "タスク数: $TASK_COUNT"
echo ""

# タスク送信
echo "【タスク送信中】"
SEND_START=$(date +%s.%N)

for i in $(seq 1 $TASK_COUNT); do
  voicebox "安定性テスト${i}番目です。" 3 > /dev/null 2>&1

  # 進捗表示
  if [ $((i % 20)) -eq 0 ]; then
    echo "  $i / $TASK_COUNT 送信完了"
  fi
done

SEND_END=$(date +%s.%N)
SEND_DURATION=$(echo "$SEND_END - $SEND_START" | bc)

echo ""
echo "送信完了: ${SEND_DURATION}秒"
echo ""

# バックグラウンド処理待機
echo "【バックグラウンド処理待機】"
echo "※タスクが順次処理されます..."

# 処理完了待機
sleep 60

# 進捗確認
for i in {1..10}; do
  ACTIVE=$(celery -A celery_worker inspect active 2>/dev/null | grep -c "pending" || echo "0")
  if [ "$ACTIVE" -eq 0 ]; then
    echo "全タスク処理完了"
    break
  fi
  echo "  残り: $ACTIVE タスク処理中..."
  sleep 10
done

# 結果確認
echo ""
echo "【結果確認】"
TEST_END=$(date +%s)
TEST_DURATION=$((TEST_END - TEST_START))

echo "テスト終了: $(date '+%Y-%m-%d %H:%M:%S')"
echo "総所要時間: ${TEST_DURATION}秒"

# 成功タスク数
SUCCESS_COUNT=$(ls ~/voicebox/task_*.wav 2>/dev/null | wc -l)
echo "成功タスク数: $SUCCESS_COUNT / $TASK_COUNT"

# エラーチェック
ERROR_LOG="$HOME/dev/voicebox-tts/logs/errors.log"
if [ -f "$ERROR_LOG" ]; then
  ERROR_COUNT=$(grep -c "ERROR" "$ERROR_LOG" 2>/dev/null || echo "0")
else
  ERROR_COUNT=0
fi
echo "エラー件数: $ERROR_COUNT"

# メモリ使用量
REDIS_MEM=$(redis-cli INFO memory | grep used_memory_human)
echo "Redis使用量: $REDIS_MEM"

echo ""

# 判定
echo "=========================================="
echo "安定性判定"
echo "=========================================="

if [ $SUCCESS_COUNT -eq $TASK_COUNT ] && [ $ERROR_COUNT -eq 0 ]; then
  echo "✅ 全タスク成功、エラーなし"
else
  echo "⚠️  一部タスク失敗またはエラーあり"
fi

if [[ "$REDIS_MEM" == *"M"* ]]; then
  MEM_VALUE=$(echo "$REDIS_MEM" | sed 's/M//')
  if (( $(echo "$MEM_VALUE < 20" | bc -l) )); then
    echo "✅ メモリ正常"
  else
    echo "⚠️  メモリ増加あり"
  fi
fi

echo ""
echo "✅ Test 5 Complete"
echo ""
