"""
VoiceBox TTS Configuration
"""
import os

# VOICEVOX API settings
VOICEVOX_API_URL = os.getenv("VOICEVOX_API_URL", "http://localhost:50021")
DEFAULT_SPEAKER = int(os.getenv("DEFAULT_SPEAKER", "1"))

# Celery settings
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

# Output settings
OUTPUT_DIR = os.getenv("OUTPUT_DIR", os.path.expanduser("~/voicebox"))
os.makedirs(OUTPUT_DIR, exist_ok=True)

# API Server settings
API_HOST = os.getenv("API_HOST", "localhost")
API_PORT = int(os.getenv("API_PORT", "5000"))

# Flower settings
FLOWER_PORT = int(os.getenv("FLOWER_PORT", "5555"))
