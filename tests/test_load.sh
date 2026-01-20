#!/bin/bash
# Test 2: 同時実行負荷テスト

echo "=========================================="
echo "Test 2: Concurrent Load Test"
echo "=========================================="
echo ""

API_URL="http://localhost:5001"
TASK_COUNT=10

echo "【シナリオ】${TASK_COUNT}タスクを連続送信"
echo "開始時刻: $(date '+%H:%M:%S.%N')"
echo ""

# タスク送信タイミング測定
START_TIME=$(date +%s.%N)

for i in $(seq 1 $TASK_COUNT); do
  TASK_START=$(date +%s.%N)
  voicebox "タスク${i}番目です。ずんだもんが順番に喋ります。" 3 > /dev/null 2>&1
  TASK_END=$(date +%s.%N)
  TASK_DURATION=$(echo "$TASK_END - $TASK_START" | bc)
  echo "[$i] 送信完了: ${TASK_DURATION}秒"
done

END_TIME=$(date +%s.%N)
TOTAL_DURATION=$(echo "$END_TIME - $START_TIME" | bc)

echo ""
echo "全送信完了時刻: $(date '+%H:%M:%S.%N')"
echo "総所要時間: ${TOTAL_DURATION}秒"
echo "平均: $(echo "scale=3; $TOTAL_DURATION / $TASK_COUNT" | bc)秒/タスク"
echo ""

# バックグラウンド処理確認
echo "【バックグラウンド処理中】"
echo "※音声が順番に再生されます"
echo ""

sleep 5
ACTIVE=$(celery -A celery_worker inspect active 2>/dev/null | grep -c "pending" || echo "0")
echo "アクティブタスク: $ACTIVE"
echo ""

echo "✅ Test 2 Complete"
echo ""
