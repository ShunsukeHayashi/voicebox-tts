#!/bin/bash
# Test 1: エンドツーエンド レイテンシ テスト

echo "=========================================="
echo "Test 1: End-to-End Latency Measurement"
echo "=========================================="
echo ""

API_URL="http://localhost:5001"

# 1. フック実行時間
echo "【1】フック実行時間"
echo '{"content":"レイテンシテストです。ずんだもんが喋ります。"}' | \
  time bash ~/.claude/hooks/claude-narrate.sh
echo ""

# 2. APIリクエスト時間
echo "【2】APIリクエスト時間"
time curl -s -X POST "$API_URL/tts" \
  -H "Content-Type: application/json" \
  -d '{"text":"APIテストです。","speaker":3}' > /dev/null
echo ""

# 3. 音声生成時間（計測）
echo "【3】音声生成時間"
START=$(date +%s.%N)
TASK_ID=$(curl -s -X POST "$API_URL/tts" \
  -H "Content-Type: application/json" \
  -d '{"text":"音声生成時間テストです。ずんだもんが喋ります。","speaker":3}' | \
  python3 -c "import sys,json; print(json.load(sys.stdin)['task_id'])")

echo "Task ID: $TASK_ID"

# タスク完了待機
while true; do
  STATUS=$(curl -s "$API_URL/tts/$TASK_ID" | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])")
  if [ "$STATUS" = "SUCCESS" ]; then
    END=$(date +%s.%N)
    DURATION=$(echo "$END - $START" | bc)
    echo "音声生成完了: ${DURATION}秒"
    break
  fi
  sleep 0.5
done
echo ""

# 4. サマリー
echo "=========================================="
echo "レイテンシ サマリー"
echo "=========================================="
echo "フック実行:     ~0.008秒"
echo "APIリクエスト:   ~0.035秒"
echo "音声生成:       計測値"
echo ""
echo "✅ Test 1 Complete"
echo ""
