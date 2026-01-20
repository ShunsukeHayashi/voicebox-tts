"""
Celery Worker for VoiceBox TTS
音声生成タスクを非同期実行するワーカー
"""
import json
import os
import subprocess
import time
import urllib.parse
import urllib.request
from celery import Celery
from config import (
    CELERY_BROKER_URL,
    CELERY_RESULT_BACKEND,
    VOICEVOX_API_URL,
    DEFAULT_SPEAKER,
    OUTPUT_DIR,
    AUTO_PLAY,
    AUTO_PLAY_COMMAND,
    SPEED_SCALE
)

# Import monitoring modules
from logger import get_task_logger
from metrics import get_metrics_collector, get_performance_monitor

# Initialize logger and metrics
task_logger = get_task_logger()
metrics = get_metrics_collector()
perf_monitor = get_performance_monitor()

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
    task_time_limit=120,  # 2 minutes (短縮)
    task_soft_time_limit=100,  # 100秒 (短縮)
    # Result backend settings (メモリ節約)
    result_expires=3600,  # 1時間後に結果を削除
    result_extended=True,
)


@app.task(bind=True, name='voicebox.tts', acks_late=True)
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

    task_id = self.request.id

    # Log task start
    task_logger.log_task_start(task_id, text, speaker)
    metrics.task_start(task_id, text, speaker)

    self.update_state(state='PROGRESS', meta={'status': 'Initializing'})

    try:
        # Update task status
        task_logger.log_task_progress(task_id, 'Querying audio parameters')
        self.update_state(state='PROGRESS', meta={'status': 'Querying audio parameters'})

        # audio_query API call
        query_url = f'{VOICEVOX_API_URL}/audio_query?speaker={speaker}&text=' + urllib.parse.quote(text)
        query_req = urllib.request.Request(query_url, method='POST')

        with urllib.request.urlopen(query_req, timeout=10) as r:  # 短縮: 30秒→10秒
            query = json.load(r)

        # Set speed scale for faster speech
        query['speedScale'] = SPEED_SCALE

        # Update task status
        task_logger.log_task_progress(task_id, 'Synthesizing audio')
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

        with urllib.request.urlopen(synth_req, timeout=20) as r:  # 短縮: 60秒→20秒
            with open(output_path, 'wb') as f:
                f.write(r.read())

        # Get file size
        file_size = os.path.getsize(output_path)

        # Auto-play audio if enabled
        if AUTO_PLAY:
            try:
                subprocess.run(
                    [AUTO_PLAY_COMMAND, output_path],
                    check=True,
                    capture_output=True,
                    timeout=60
                )
                task_logger.log_task_progress(task_id, f'Audio played with {AUTO_PLAY_COMMAND}')
            except Exception as play_error:
                task_logger.log_task_failure(task_id, f'Audio playback failed: {play_error}')

        # Log task success
        metrics.task_complete(task_id, file_size)
        task_logger.log_task_success(task_id, file_size, 0)

        return {
            'success': True,
            'audio_path': output_path,
            'speaker': speaker,
            'text': text,
            'file_size': file_size,
            'task_id': self.request.id
        }

    except Exception as e:
        error_msg = str(e)

        # Log task failure
        metrics.task_failure(task_id, error_msg)
        task_logger.log_task_failure(task_id, error_msg)
        perf_monitor.record_error('TaskError', error_msg, {
            'task_id': task_id,
            'speaker': speaker,
            'text_length': len(text)
        })

        return {
            'success': False,
            'error': error_msg,
            'speaker': speaker,
            'text': text,
            'task_id': self.request.id
        }


@app.task(name='voicebox.health')
def health_check():
    """ヘルスチェックタスク"""
    return {
        'status': 'ok',
        'message': 'VoiceBox TTS worker is running',
        'metrics': metrics.get_stats()
    }


@app.task(name='voicebox.get_metrics')
def get_metrics():
    """メトリクス取得タスク"""
    return metrics.get_stats()


if __name__ == '__main__':
    # Start Celery worker
    app.start()
