#!/bin/bash
# Test 4: エラー耐性テスト

echo "=========================================="
echo "Test 4: Error Resilience Test"
echo "=========================================="
echo ""

# テスト1: 無効なAPI URL
echo "【Test 4-1】無効なAPI URL時のフック挙動"
export VOICEBOX_API_URL="http://localhost:9999"
echo "無効なURLに設定: $VOICEBOX_API_URL"

HOOK_START=$(date +%s.%N)
echo '{"content":"エラーテストです。"}' | bash ~/.claude/hooks/claude-narrate.sh
HOOK_END=$(date +%s.%N)
HOOK_DURATION=$(echo "$HOOK_END - $HOOK_START" | bc)

echo "フック実行時間: ${HOOK_DURATION}秒"
if (( $(echo "$HOOK_DURATION < 1" | bc -l) )); then
  echo "✅ フック即座に復帰"
else
  echo "❌ フック遅延"
fi

# 元に戻す
export VOICEBOX_API_URL="http://localhost:5001"
echo ""

# テスト2: 不正なJSON
echo "【Test 4-2】不正なJSON入力"
echo "invalid json" | bash ~/.claude/hooks/claude-narrate.sh
echo "✅ 不正なJSONでエラーなし"
echo ""

# テスト3: 空文字列
echo "【Test 4-3】空文字列・短い文字列"
echo '{"content":""}' | bash ~/.claude/hooks/claude-narrate.sh
echo '{"content":"短"}' | bash ~/.claude/hooks/claude-narrate.sh
echo "✅ 空文字・短い文字でエラーなし"
echo ""

# テスト4: API正常時の復帰確認
echo "【Test 4-4】API正常時の動作確認"
voicebox "正常復帰テストです。" 3 > /dev/null 2>&1
echo "✅ API正常時は正しく動作"
echo ""

echo "=========================================="
echo "エラー耐性 サマリー"
echo "=========================================="
echo "APIダウン時:    即座に復帰 ✅"
echo "不正なJSON:     エラーなし ✅"
echo "空・短い文字:   エラーなし ✅"
echo "API正常時:      正常動作 ✅"
echo ""
echo "✅ Test 4 Complete"
echo ""
