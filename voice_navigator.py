"""
Voice Navigator - 音声ナビゲーションシステム
エージェントの実行状態をリアルタイムでVOICEVOX読み上げ
"""
import json
import time
import threading
import urllib.parse
import urllib.request
from collections import deque
from typing import Optional

import redis
from celery.events import EventReceiver
from celery import Celery

from config import VOICEVOX_API_URL, DEFAULT_SPEAKER, CELERY_BROKER_URL, OUTPUT_DIR


class VoiceNavigator:
    """音声ナビゲーションシステム

    Celeryイベントを監視し、状態変化をVOICEVOXで読み上げる。
    """

    def __init__(
        self,
        speaker: int = None,
        voicevox_url: str = None,
        enable_audio: bool = True,
        verbose: bool = True
    ):
        self.speaker = speaker or DEFAULT_SPEAKER
        self.voicevox_url = voicevox_url or VOICEVOX_API_URL
        self.enable_audio = enable_audio
        self.verbose = verbose
        self.running = False

        # 音声キュー（重複防止）
        self.speech_queue = deque(maxlen=100)
        self.speech_lock = threading.Lock()

        # Redis接続（状態追跡用）
        self.redis_client = redis.from_url(CELERY_BROKER_URL)

        # Celery app（イベント取得用）
        self.celery_app = Celery('voicebox_tts', broker=CELERY_BROKER_URL)

    def log(self, message: str):
        """ログ出力"""
        if self.verbose:
            print(f"[VoiceNavigator] {message}")

    def speak(self, text: str) -> bool:
        """VOICEVOXで読み上げ

        Args:
            text: 読み上げテキスト

        Returns:
            成功時True
        """
        if not self.enable_audio:
            self.log(f"[音声スキップ] {text}")
            return True

        # 重複チェック
        with self.speech_lock:
            if text in self.speech_queue:
                self.log(f"[重複スキップ] {text}")
                return False
            self.speech_queue.append(text)

        try:
            self.log(f"🎙️ {text}")

            # audio_query
            query_url = f'{self.voicevox_url}/audio_query?speaker={self.speaker}&text=' + urllib.parse.quote(text)
            query_req = urllib.request.Request(query_url, method='POST')

            with urllib.request.urlopen(query_req, timeout=5) as r:
                query = json.load(r)

            # synthesis
            synth_url = f'{self.voicevox_url}/synthesis?speaker={self.speaker}'
            synth_req = urllib.request.Request(
                synth_url,
                data=json.dumps(query).encode(),
                headers={'Content-Type': 'application/json'},
                method='POST'
            )

            output_path = f'{OUTPUT_DIR}/navi_{int(time.time())}.wav'

            with urllib.request.urlopen(synth_req, timeout=10) as r:
                with open(output_path, 'wb') as f:
                    f.write(r.read())

            # 音声再生（非同期）
            self._play_audio_async(output_path)
            return True

        except Exception as e:
            self.log(f"❌ 音声生成エラー: {e}")
            return False

    def _play_audio_async(self, audio_path: str):
        """非同期で音声再生"""
        def play():
            try:
                import subprocess
                subprocess.run(['afplay', audio_path], check=False, capture_output=True)
            except Exception as e:
                self.log(f"⚠️ 音声再生エラー: {e}")

        threading.Thread(target=play, daemon=True).start()

    def describe_task_event(self, event: dict) -> str:
        """Celeryタスクイベントを説明文に変換

        Args:
            event: Celeryイベント辞書

        Returns:
            説明文
        """
        event_type = event.get('type')
        uuid = event.get('uuid', '')[:8]

        # タスク受信
        if event_type == 'task-received':
            name = event.get('name', 'unknown')
            args = event.get('args', [])
            text = args[0] if args else 'empty'
            return f"タスク受信。{name} テキストは「{text[:30]}...」"

        # タスク開始
        elif event_type == 'task-started':
            return f"タスク{uuid}、開始しました"

        # タスク成功
        elif event_type == 'task-succeeded':
            result = event.get('result', {})
            if result.get('success'):
                size = result.get('file_size', 0) // 1024
                return f"タスク{uuid}、完了しました。ファイルサイズ{size}キロバイト"
            return f"タスク{uuid}、完了しました"

        # タスク失敗
        elif event_type == 'task-failed':
            exception = event.get('exception', 'Unknown error')
            return f"タスク{uuid}、エラーが発生しました。{exception}"

        # 進捗更新
        elif event_type == 'task-progress':
            return None  # 進捗は読み上げすぎ防止のためスキップ

        return None

    def handle_celery_event(self, event: dict):
        """Celeryイベントを処理

        Args:
            event: Celeryイベント辞書
        """
        description = self.describe_task_event(event)
        if description:
            self.speak(description)

    def start_celery_monitor(self):
        """Celeryイベント監視を開始"""
        self.log("🔍 Celeryイベント監視開始...")

        try:
            # Redis接続からイベント受信
            with self.celery_app.connection() as conn:
                recv = EventReceiver(
                    conn,
                    handlers={'*': self.handle_celery_event}
                )
                self.speak("エージェント監視、開始します")
                recv.capture(limit=None, timeout=None)
        except KeyboardInterrupt:
            self.log("監視停止")
        except Exception as e:
            self.log(f"❌ 監視エラー: {e}")

    def start_api_monitor(self):
        """API監視を開始（Redis Pub/Sub使用）"""
        self.log("🔍 API監視開始...")

        pubsub = self.redis_client.pubsub()
        pubsub.subscribe('voicebox_api_events')

        self.speak("API監視、開始します")

        while self.running:
            message = pubsub.get_message(timeout=1)
            if message and message.get('type') == 'message':
                data = json.loads(message.get('data', '{}'))
                event_type = data.get('type')

                if event_type == 'request':
                    endpoint = data.get('endpoint', 'unknown')
                    method = data.get('method', 'GET')
                    self.speak(f"APIリクエスト受信。{method} {endpoint}")

                elif event_type == 'response':
                    status = data.get('status', 200)
                    self.speak(f"APIレスポンス送信。ステータスコード{status}")

    def start(self):
        """音声ナビゲーション開始"""
        self.running = True

        # Celery監視スレッド
        celery_thread = threading.Thread(
            target=self.start_celery_monitor,
            daemon=True
        )

        # API監視スレッド
        api_thread = threading.Thread(
            target=self.start_api_monitor,
            daemon=True
        )

        celery_thread.start()
        api_thread.start()

        self.speak("音声ナビゲーション、起動しました")

        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        """音声ナビゲーション停止"""
        self.running = False
        self.speak("音声ナビゲーション、停止します")
        time.sleep(2)  # 読み上げ完了待機


if __name__ == '__main__':
    import sys

    # スピーカー指定（オプション）
    speaker = int(sys.argv[1]) if len(sys.argv) > 1 else None

    navigator = VoiceNavigator(
        speaker=speaker,
        enable_audio=True,
        verbose=True
    )

    navigator.start()
