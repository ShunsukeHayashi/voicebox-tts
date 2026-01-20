# VoiceBox TTS

VOICEVOX音声生成の非同期キューイングシステム (Celery + Redis)

## アーキテクチャ

```
Client → API Server → Celery → Redis → Worker → VOICEVOX API
                              ↓
                           Flower (Web UI)
```

## セットアップ

### 1. Redisの起動

```bash
brew services start redis
```

### 2. 依存ライブラリのインストール

```bash
pip install -r requirements.txt
```

### 3. VOICEVOXの起動

VOICEVOXアプリを起動してAPIサーバー（ポート50021）を有効化してください。

## 実行方法

### Celery Worker (音声生成ワーカー)

```bash
celery -A celery_worker worker --loglevel=info
```

### API Server (HTTP API)

```bash
python api_server.py
```

### Flower (監視ダッシュボード)

```bash
celery -A celery_worker flower --port=5555
```

## API使用例

### 音声生成タスク作成

```bash
curl -X POST http://localhost:5000/tts \
  -H "Content-Type: application/json" \
  -d '{"text": "テスト", "speaker": 1}'
```

Response:
```json
{
  "task_id": "xxx-xxx-xxx",
  "status": "PENDING"
}
```

### タスク状態確認

```bash
curl http://localhost:5000/tts/{task_id}
```

Response:
```json
{
  "task_id": "xxx-xxx-xxx",
  "status": "SUCCESS",
  "result": {
    "success": true,
    "audio_path": "/Users/shunsukehayashi/voicebox/task_xxx.wav",
    "speaker": 1,
    "text": "テスト",
    "file_size": 12345
  }
}
```

### ヘルスチェック

```bash
curl http://localhost:5000/health
```

## 話者一例

| ID | 名前 |
|----|------|
| 0 | 四国めたん (あまあま) |
| 1 | 四国めたん (ノーマル) |
| 2 | 四国めたん (セクシー) |
| 3 | ずんだもん (ノーマル) |
| 8 | 春日部つむぎ |

## 環境変数

| 変数 | デフォルト | 説明 |
|------|----------|------|
| `VOICEVOX_API_URL` | `http://localhost:50021` | VOICEVOX API URL |
| `DEFAULT_SPEAKER` | `1` | デフォルト話者ID |
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` | Celery broker |
| `API_HOST` | `localhost` | APIサーバーホスト |
| `API_PORT` | `5000` | APIサーバーポート |
| `FLOWER_PORT` | `5555` | Flowerポート |

## ライセンス

MIT
