"""
Flask API Server for VoiceBox TTS
音声生成タスクの登録・結果取得用HTTPエンドポイント
"""
import os
import time
from flask import Flask, request, jsonify, g, send_from_directory
from celery.result import AsyncResult
from celery_worker import app as celery_app
from config import API_HOST, API_PORT
from flasgger import Swagger
import yaml

# Import monitoring modules
from logger import get_api_logger
from metrics import get_metrics_collector, get_performance_monitor

# Initialize logger and metrics
api_logger = get_api_logger()
metrics = get_metrics_collector()
perf_monitor = get_performance_monitor()

api = Flask(__name__, static_folder='static')

# Load OpenAPI spec
with open('openapi.yaml', 'r', encoding='utf-8') as f:
    openapi_spec = yaml.safe_load(f)

# Configure Swagger
swagger_config = {
    "headers": [],
    "specs": [
        {
            "endpoint": 'spec',
            "route": '/spec.json',
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/docs"
}

swagger = Swagger(api, config=swagger_config, template=openapi_spec)


@api.before_request
def before_request():
    """リクエスト前処理"""
    g.start_time = time.time()


@api.after_request
def after_request(response):
    """レスポンス後処理"""
    if hasattr(g, 'start_time'):
        duration_ms = (time.time() - g.start_time) * 1000
        api_logger.log_response(request.path, response.status_code, duration_ms)
        perf_monitor.record_api_request(request.path, duration_ms)
    return response


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
    api_logger.log_request('/tts', 'POST')

    data = request.get_json()

    if not data or 'text' not in data:
        api_logger.log_error('/tts', 'Missing required field: text')
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
    api_logger.log_request(f'/tts/{task_id}', 'GET')

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
        api_logger.log_error(f'/tts/{task_id}', f'Task failed: {task.info}')

    return jsonify(response)


@api.route('/tasks', methods=['GET'])
def list_tasks():
    """アクティブなタスク一覧"""
    api_logger.log_request('/tasks', 'GET')

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
    api_logger.log_request('/workers', 'GET')

    inspect = celery_app.control.inspect()
    stats = inspect.stats()
    registered = inspect.registered()

    return jsonify({
        'stats': stats,
        'registered_tasks': registered
    })


@api.route('/metrics', methods=['GET'])
def get_metrics():
    """メトリクス取得"""
    api_logger.log_request('/metrics', 'GET')

    return jsonify({
        'stats': metrics.get_stats(),
        'recent_tasks': metrics.get_recent_tasks(limit=10)
    })


@api.route('/errors', methods=['GET'])
def get_errors():
    """エラーログ取得"""
    api_logger.log_request('/errors', 'GET')

    limit = request.args.get('limit', 10, type=int)
    return jsonify({
        'errors': perf_monitor.get_recent_errors(limit)
    })


if __name__ == '__main__':
    api.run(host=API_HOST, port=API_PORT, debug=True)
