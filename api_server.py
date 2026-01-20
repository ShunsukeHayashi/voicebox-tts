"""
Flask API Server for VoiceBox TTS
音声生成タスクの登録・結果取得用HTTPエンドポイント
"""
from flask import Flask, request, jsonify
from celery.result import AsyncResult
from celery_worker import app as celery_app
from config import API_HOST, API_PORT

api = Flask(__name__)


@api.route('/health', methods=['GET'])
def health():
    """ヘルスチェック"""
    return jsonify({
        'status': 'ok',
        'service': 'voicebox-tts-api',
        'celery': celery_app.control.inspect().stats()
    })


@api.route('/tts', methods=['POST'])
def create_tts_task():
    """
    音声生成タスクを作成

    Request Body:
        {
            "text": "読み上げテキスト",
            "speaker": 1  # オプション、デフォルト: 1
        }

    Response:
        {
            "task_id": "xxx-xxx-xxx",
            "status": "PENDING"
        }
    """
    data = request.get_json()

    if not data or 'text' not in data:
        return jsonify({'error': 'Missing required field: text'}), 400

    text = data['text']
    speaker = data.get('speaker')

    # タスクを非同期実行
    task = celery_app.send_task('voicebox.tts', args=[text, speaker])

    return jsonify({
        'task_id': task.id,
        'status': task.status
    }), 202


@api.route('/tts/<task_id>', methods=['GET'])
def get_tts_task(task_id: str):
    """
    タスクの状態・結果を取得

    Response:
        {
            "task_id": "xxx",
            "status": "SUCCESS|PENDING|PROGRESS|FAILURE",
            "result": { ... }
        }
    """
    task = AsyncResult(task_id, app=celery_app)

    response = {
        'task_id': task_id,
        'status': task.status
    }

    if task.state == 'PENDING':
        response['result'] = None
    elif task.state == 'PROGRESS':
        response['result'] = task.info
    elif task.state == 'SUCCESS':
        response['result'] = task.result
    else:  # FAILURE
        response['result'] = str(task.info)

    return jsonify(response)


@api.route('/tasks', methods=['GET'])
def list_tasks():
    """アクティブなタスク一覧"""
    inspect = celery_app.control.inspect()
    active = inspect.active()
    scheduled = inspect.scheduled()

    return jsonify({
        'active': active,
        'scheduled': scheduled
    })


@api.route('/workers', methods=['GET'])
def list_workers():
    """ワーカー一覧・状態"""
    inspect = celery_app.control.inspect()
    stats = inspect.stats()
    registered = inspect.registered()

    return jsonify({
        'stats': stats,
        'registered_tasks': registered
    })


if __name__ == '__main__':
    api.run(host=API_HOST, port=API_PORT, debug=True)
