# VoiceBox TTS System Specification

## 概要 (Overview)

VOICEVOX Text-to-Speech API と Celery + Redis を使用した非同期音声生成システム。

## システム構成 (Architecture)

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│ Claude Code │ ───▶ │   API Server│ ───▶ │Celery Worker│
│   (MCP)     │      │  (Flask)    │      │  (Python)   │
└─────────────┘      └─────────────┘      └─────────────┘
                            │                     │
                            ▼                     ▼
                      ┌─────────────┐      ┌─────────────┐
                      │   Redis     │      │  VOICEVOX   │
                      │  (Broker)   │      │   (Port)    │
                      └─────────────┘      └─────────────┘
                                                    │
                                                    ▼
                                              ┌─────────────┐
                                              │  Audio File │
                                              │ + Auto Play │
                                              └─────────────┘
```

## コンポーネント (Components)

### 1. API Server (`api_server.py`)
- **Port**: 5001
- **Framework**: Flask
- **Endpoints**:
  - `POST /tts` - 音声生成タスク作成（ノンブロッキング）
  - `GET /tts/<task_id>` - タスク状態確認
  - `GET /health` - ヘルスチェック
  - `GET /metrics` - システムメトリクス

### 2. Celery Worker (`celery_worker.py`)
- **Concurrency**: 10 workers
- **Broker**: Redis (localhost:6379/0)
- **Backend**: Redis (localhost:6379/0)
- **Tasks**:
  - `voicebox.tts` - 音声生成タスク
  - `voicebox.health` - ヘルスチェック
  - `voicebox.get_metrics` - メトリクス取得

### 3. Monitoring
- **Flower**: Port 5555 - Celery監視ダッシュボード
- **Structured Logging**: JSON形式ログ
- **Metrics**: タスク完了数、失敗数、成功率

## 設定 (Configuration)

| 環境変数 | デフォルト | 説明 |
|---------|----------|------|
| `VOICEVOX_API_URL` | `http://localhost:50021` | VOICEVOX API URL |
| `DEFAULT_SPEAKER` | `1` | デフォルト話者ID |
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` | Celery broker |
| `OUTPUT_DIR` | `~/voicebox` | 音声出力ディレクトリ |
| `AUTO_PLAY` | `true` | 音声自動再生 |
| `AUTO_PLAY_COMMAND` | `afplay` | 再生コマンド |

## 話者一覧 (Speakers)

| ID | 名前 |
|----|------|
| 0 | 四国めたん (あまあま) |
| 1 | 四国めたん (ノーマル) |
| 2 | 四国めたん (セクシー) |
| 3 | ずんだもん (ノーマル) |
| 4 | ずんだもん (あまあま) |
| 5 | ずんだもん (悲嘆) |
| 6 | 春日部つむぎ (ノーマル) |
| 7 | 春日部つむぎ (あまあま) |
| 8 | 春日部つむぎ (ツンデレ) |

## タスクフロー (Task Flow)

```
1. API ServerへPOST /tts リクエスト
   ├─ text: 読み上げテキスト
   └─ speaker: 話者ID (省略可)

2. API Server → Celery Workerへタスク送信
   └─ 即座に task_id を返却（ノンブロッキング）

3. Celery Workerがバックグラウンドで処理
   ├─ VOICEVOX APIで音声生成
   ├─ ファイル保存: ~/voicebox/task_{id}.wav
   └─ AUTO_PLAY=true なら afplay で自動再生

4. クライアントが GET /tts/{task_id} で状態確認
```

## MCP Server Integration (`voicebox-mcp`)

### MCP Tools

| Tool | 説明 |
|------|------|
| `voicebox_speak` | テキストを音声に変換（ノンブロッキング） |
| `voicebox_status` | タスク状態確認 |
| `voicebox_speakers` | 話者一覧取得 |
| `voicebox_health` | ヘルスチェック |
| `voicebox_metrics` | メトリクス取得 |

### PATH Skill (`voicebox`)

```bash
voicebox "テキスト" [speaker_id]
voicebox-status <task_id>
voicebox-speakers
```

## ノンブロッキング仕様 (Non-blocking Specification)

### 原則
- API/MCP はタスク作成後、**即座に復帰**する
- 音声生成は Celery Worker でバックグラウンド実行
- メインスレッド（チャット）は待機しない

### 実装
```python
# api_server.py
@app.route('/tts', methods=['POST'])
def create_tts_task():
    task = tts_task.delay(text, speaker)  # 非同期実行
    return jsonify({'task_id': task.id, 'status': 'PENDING'}), 202
```

```typescript
// voicebox-mcp/src/index.ts
const task = await client.createTTSTask(text, speaker);
return { content: [{ type: 'text', text: `✅ TTS task queued!\nTask ID: ${task.task_id}` }] };
```

## 音声自動再生 (Auto-play)

### 仕様
- 音声生成完了後、自動的に音声を再生
- macOS: `afplay` コマンド使用
- 環境変数 `AUTO_PLAY=false` で無効化可能

### 実装
```python
# celery_worker.py
if AUTO_PLAY:
    subprocess.run([AUTO_PLAY_COMMAND, output_path], check=True, capture_output=True)
```

## 監視・ログ (Monitoring & Logging)

### Structured Logging
```json
{"timestamp": "2026-01-20T13:52:00", "level": "INFO", "event": "task_start", "task_id": "..."}
```

### Metrics
- タスク完了数 (`tasks_completed`)
- タスク失敗数 (`tasks_failed`)
- 成功率 (`success_rate`)
- アクティブタスク数 (`active_tasks`)
- 過去1時間のタスク数 (`tasks_last_hour`)

## 依存関係 (Dependencies)

```
Flask >= 2.0
Celery >= 5.2
redis >= 4.0
requests >= 2.28
```

## 管理スクリプト (Management Scripts)

| スクリプト | 説明 |
|----------|------|
| `scripts/start.sh` | システム起動 |
| `scripts/stop.sh` | システム停止 |
| `scripts/restart.sh` | 再起動 |
| `scripts/status.sh` | 状態確認 |

## API例 (API Examples)

### 音声生成リクエスト
```bash
curl -X POST http://localhost:5001/tts \
  -H "Content-Type: application/json" \
  -d '{"text":"こんにちは","speaker":3}'
```

### レスポンス
```json
{
  "status": "PENDING",
  "task_id": "e692af19-3f33-4787-aff0-ea4b6458d081"
}
```

### ステータス確認
```bash
curl http://localhost:5001/tts/e692af19-3f33-4787-aff0-ea4b6458d081
```

### レスポンス (成功時)
```json
{
  "status": "SUCCESS",
  "result": {
    "success": true,
    "audio_path": "/Users/shunsukehayashi/voicebox/task_e692af19-3f33-4787-aff0-ea4b6458d081.wav",
    "file_size": 171052,
    "speaker": 3,
    "text": "こんにちは",
    "task_id": "e692af19-3f33-4787-aff0-ea4b6458d081"
  }
}
```

## OpenAPIドキュメント
- `openapi.yaml` - OpenAPI 3.0.3 仕様
- Swagger UI: 利用可能 (api_server.py 参照)

---

**Version**: 1.0.0
**Last Updated**: 2026-01-20
