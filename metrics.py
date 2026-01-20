"""
Metrics Collection Module for VoiceBox TTS
メトリクス収集モジュール
"""
import time
import threading
from collections import defaultdict, deque
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Deque


@dataclass
class TaskMetric:
    """タスクメトリクス"""
    task_id: str
    status: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    file_size: Optional[int] = None
    speaker: Optional[int] = None
    text_length: int = 0
    error: Optional[str] = None

    def to_dict(self):
        return {
            'task_id': self.task_id,
            'status': self.status,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_ms': self.duration_ms,
            'file_size': self.file_size,
            'speaker': self.speaker,
            'text_length': self.text_length,
            'error': self.error
        }


class MetricsCollector:
    """メトリクス収集クラス"""

    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self._lock = threading.Lock()

        # タスク履歴
        self._tasks: Dict[str, TaskMetric] = {}
        self._task_history: Deque[TaskMetric] = deque(maxlen=max_history)

        # 統計カウンター
        self._counters = defaultdict(int)

        # パフォーマンスメトリクス
        self._durations: List[float] = []
        self._max_duration_samples = 100

    def task_start(self, task_id: str, text: str, speaker: int):
        """タスク開始記録"""
        with self._lock:
            metric = TaskMetric(
                task_id=task_id,
                status='STARTED',
                start_time=datetime.utcnow(),
                speaker=speaker,
                text_length=len(text)
            )
            self._tasks[task_id] = metric
            self._counters['tasks_started'] += 1

    def task_complete(self, task_id: str, file_size: int):
        """タスク完了記録"""
        with self._lock:
            if task_id not in self._tasks:
                return

            metric = self._tasks[task_id]
            metric.status = 'SUCCESS'
            metric.end_time = datetime.utcnow()
            metric.duration_ms = (metric.end_time - metric.start_time).total_seconds() * 1000
            metric.file_size = file_size

            self._task_history.append(metric)
            self._durations.append(metric.duration_ms)
            if len(self._durations) > self._max_duration_samples:
                self._durations.pop(0)

            self._counters['tasks_completed'] += 1
            self._counters['total_audio_bytes'] += file_size

    def task_failure(self, task_id: str, error: str):
        """タスク失敗記録"""
        with self._lock:
            if task_id not in self._tasks:
                return

            metric = self._tasks[task_id]
            metric.status = 'FAILURE'
            metric.end_time = datetime.utcnow()
            metric.duration_ms = (metric.end_time - metric.start_time).total_seconds() * 1000
            metric.error = error

            self._task_history.append(metric)
            self._counters['tasks_failed'] += 1

    def get_stats(self) -> Dict:
        """統計情報取得"""
        with self._lock:
            completed = self._counters['tasks_completed']
            failed = self._counters['tasks_failed']
            total = completed + failed

            # パーセンタイル計算
            p50 = p95 = p99 = None
            if self._durations:
                sorted_durations = sorted(self._durations)
                n = len(sorted_durations)
                p50 = sorted_durations[int(n * 0.5)]
                p95 = sorted_durations[int(n * 0.95)]
                p99 = sorted_durations[int(n * 0.99)]

            # 直近1時間のタスク数
            hour_ago = datetime.utcnow() - timedelta(hours=1)
            recent_tasks = [
                m for m in self._task_history
                if m.start_time >= hour_ago
            ]

            return {
                'counters': dict(self._counters),
                'success_rate': completed / total if total > 0 else 0,
                'duration_ms': {
                    'p50': p50,
                    'p95': p95,
                    'p99': p99,
                },
                'tasks_last_hour': len(recent_tasks),
                'active_tasks': len([t for t in self._tasks.values() if t.status == 'STARTED'])
            }

    def get_recent_tasks(self, limit: int = 10) -> List[Dict]:
        """最近のタスク取得"""
        with self._lock:
            recent = list(self._task_history)[-limit:]
            return [m.to_dict() for m in reversed(recent)]

    def cleanup_old_tasks(self, hours: int = 24):
        """古いタスクをクリーンアップ"""
        with self._lock:
            cutoff = datetime.utcnow() - timedelta(hours=hours)
            to_remove = [
                task_id for task_id, metric in self._tasks.items()
                if metric.end_time and metric.end_time < cutoff
            ]
            for task_id in to_remove:
                del self._tasks[task_id]


class PerformanceMonitor:
    """パフォーマンス監視"""

    def __init__(self):
        self._lock = threading.Lock()
        self._api_requests: Dict[str, Deque[float]] = defaultdict(lambda: deque(maxlen=100))
        self._errors: Deque[Dict] = deque(maxlen=100)

    def record_api_request(self, endpoint: str, duration_ms: float):
        """APIリクエスト記録"""
        with self._lock:
            self._api_requests[endpoint].append(duration_ms)

    def record_error(self, error_type: str, message: str, context: Dict = None):
        """エラー記録"""
        with self._lock:
            self._errors.append({
                'timestamp': datetime.utcnow().isoformat(),
                'type': error_type,
                'message': message,
                'context': context or {}
            })

    def get_api_stats(self, endpoint: str) -> Dict:
        """API統計取得"""
        with self._lock:
            durations = list(self._api_requests.get(endpoint, []))
            if not durations:
                return {'count': 0, 'avg_ms': None}

            return {
                'count': len(durations),
                'avg_ms': sum(durations) / len(durations),
                'min_ms': min(durations),
                'max_ms': max(durations),
            }

    def get_recent_errors(self, limit: int = 10) -> List[Dict]:
        """最近のエラー取得"""
        with self._lock:
            errors = list(self._errors)[-limit:]
            return list(reversed(errors))


# グローバルインスタンス
_metrics_collector = MetricsCollector()
_performance_monitor = PerformanceMonitor()


def get_metrics_collector() -> MetricsCollector:
    return _metrics_collector


def get_performance_monitor() -> PerformanceMonitor:
    return _performance_monitor
