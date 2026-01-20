"""
Structured Logging Module for VoiceBox TTS
構造化ロギングモジュール
"""
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


class StructuredLogger:
    """構造化ロガー - JSON形式でログ出力"""

    def __init__(self, name: str, log_dir: str = "logs"):
        self.name = name
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)

        # ファイルハンドラー
        log_file = self.log_dir / f"{name}.jsonl"
        self.file_handler = logging.FileHandler(log_file, encoding='utf-8')
        self.file_handler.setFormatter(JsonFormatter())

        # コンソールハンドラー
        self.console_handler = logging.StreamHandler()
        self.console_handler.setFormatter(ColoredFormatter())

        # ロガー設定
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(self.file_handler)
        self.logger.addHandler(self.console_handler)

    def _log(self, level: str, message: str, **kwargs):
        """ログ出力"""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': level,
            'logger': self.name,
            'message': message,
            **kwargs
        }

        if level == 'ERROR':
            self.logger.error(json.dumps(log_entry, ensure_ascii=False))
        elif level == 'WARNING':
            self.logger.warning(json.dumps(log_entry, ensure_ascii=False))
        elif level == 'INFO':
            self.logger.info(json.dumps(log_entry, ensure_ascii=False))
        else:  # DEBUG
            self.logger.debug(json.dumps(log_entry, ensure_ascii=False))

    def info(self, message: str, **kwargs):
        self._log('INFO', message, **kwargs)

    def warning(self, message: str, **kwargs):
        self._log('WARNING', message, **kwargs)

    def error(self, message: str, **kwargs):
        self._log('ERROR', message, **kwargs)

    def debug(self, message: str, **kwargs):
        self._log('DEBUG', message, **kwargs)


class JsonFormatter(logging.Formatter):
    """JSONフォーマッター"""

    def format(self, record):
        try:
            return record.getMessage()
        except Exception:
            return str(record)


class ColoredFormatter(logging.Formatter):
    """カラーコンソールフォーマッター"""

    COLORS = {
        'INFO': '\033[0;32m',     # Green
        'WARNING': '\033[1;33m',  # Yellow
        'ERROR': '\033[0;31m',    # Red
        'DEBUG': '\033[0;36m',    # Cyan
    }
    RESET = '\033[0m'

    def format(self, record):
        try:
            data = json.loads(record.getMessage())
            level = data.get('level', 'INFO')
            color = self.COLORS.get(level, '')
            message = data.get('message', '')

            # 追加フィールドを表示
            extras = []
            for key, value in data.items():
                if key not in ('timestamp', 'level', 'logger', 'message'):
                    extras.append(f"{key}={value}")

            extra_str = ' | '.join(extras) if extras else ''

            return f"{color}[{level}]{self.RESET} {message}{' | ' + extra_str if extra_str else ''}"
        except Exception:
            return str(record)


class TaskLogger:
    """タスク専用ロガー"""

    def __init__(self, base_logger: StructuredLogger):
        self.base_logger = base_logger

    def log_task_start(self, task_id: str, text: str, speaker: int):
        self.base_logger.info(
            "Task started",
            task_id=task_id,
            text_length=len(text),
            speaker=speaker,
            event="task_start"
        )

    def log_task_progress(self, task_id: str, status: str):
        self.base_logger.info(
            "Task progress",
            task_id=task_id,
            status=status,
            event="task_progress"
        )

    def log_task_success(self, task_id: str, file_size: int, duration: float):
        self.base_logger.info(
            "Task completed",
            task_id=task_id,
            file_size=file_size,
            duration_seconds=duration,
            event="task_success"
        )

    def log_task_failure(self, task_id: str, error: str):
        self.base_logger.error(
            "Task failed",
            task_id=task_id,
            error=error,
            event="task_failure"
        )


class APILogger:
    """API専用ロガー"""

    def __init__(self, base_logger: StructuredLogger):
        self.base_logger = base_logger

    def log_request(self, endpoint: str, method: str, **kwargs):
        self.base_logger.info(
            f"{method} {endpoint}",
            endpoint=endpoint,
            method=method,
            event="api_request",
            **kwargs
        )

    def log_response(self, endpoint: str, status_code: int, duration_ms: float):
        self.base_logger.info(
            f"Response {status_code}",
            endpoint=endpoint,
            status_code=status_code,
            duration_ms=duration_ms,
            event="api_response"
        )

    def log_error(self, endpoint: str, error: str):
        self.base_logger.error(
            f"API Error: {error}",
            endpoint=endpoint,
            error=error,
            event="api_error"
        )


# ロガーインスタンス作成
def get_logger(name: str) -> StructuredLogger:
    return StructuredLogger(name)


def get_task_logger() -> TaskLogger:
    return TaskLogger(get_logger('tasks'))


def get_api_logger() -> APILogger:
    return APILogger(get_logger('api'))
