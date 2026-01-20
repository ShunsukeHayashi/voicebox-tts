"""
Celery Worker for VoiceBox TTS
音声生成タスクを非同期実行するワーカー
"""
import json
import urllib.parse
import urllib.request
from celery import Celery
from config import (
    CELERY_BROKER_URL,
    CELERY_RESULT_BACKEND,
    VOICEVOX_API_URL,
    DEFAULT_SPEAKER,
    OUTPUT_DIR
)

# Celery app initialization
app = Celery(
    'voicebox_tts',
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND
)

app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Tokyo',
    enable_utc=True,
    # Task settings
    task_track_started=True,
    task_time_limit=300,  # 5 minutes
    task_soft_time_limit=240,  # 4 minutes
)


@app.task(bind=True, name='voicebox.tts')
def tts_task(self, text: str, speaker: int = None):
    """
    VOICEVOX APIで音声生成を行うタスク

    Args:
        text: 読み上げテキスト
        speaker: 話者ID (デフォルト: DEFAULT_SPEAKER)

    Returns:
        dict: {
            'success': bool,
            'audio_path': str,
            'speaker': int,
            'text': str,
            'duration': float  # seconds
        }
    """
    if speaker is None:
        speaker = DEFAULT_SPEAKER

    self.update_state(state='PROGRESS', meta={'status': 'Initializing'})

    try:
        # Update task status
        self.update_state(state='PROGRESS', meta={'status': 'Querying audio parameters'})

        # audio_query API call
        query_url = f'{VOICEVOX_API_URL}/audio_query?speaker={speaker}&text=' + urllib.parse.quote(text)
        query_req = urllib.request.Request(query_url, method='POST')

        with urllib.request.urlopen(query_req, timeout=30) as r:
            query = json.load(r)

        # Update task status
        self.update_state(state='PROGRESS', meta={'status': 'Synthesizing audio'})

        # synthesis API call
        synth_url = f'{VOICEVOX_API_URL}/synthesis?speaker={speaker}'
        synth_req = urllib.request.Request(
            synth_url,
            data=json.dumps(query).encode(),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )

        output_path = f'{OUTPUT_DIR}/task_{self.request.id}.wav'

        with urllib.request.urlopen(synth_req, timeout=60) as r:
            with open(output_path, 'wb') as f:
                f.write(r.read())

        # Get file size
        import os
        file_size = os.path.getsize(output_path)

        return {
            'success': True,
            'audio_path': output_path,
            'speaker': speaker,
            'text': text,
            'file_size': file_size,
            'task_id': self.request.id
        }

    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'speaker': speaker,
            'text': text,
            'task_id': self.request.id
        }


@app.task(name='voicebox.health')
def health_check():
    """ヘルスチェックタスク"""
    return {'status': 'ok', 'message': 'VoiceBox TTS worker is running'}


if __name__ == '__main__':
    # Start Celery worker
    app.start()
