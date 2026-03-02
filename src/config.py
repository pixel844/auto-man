import sys
from pathlib import Path
from loguru import logger

# Signal-focused logging
logger.remove()
logger.add(sys.stderr, level="INFO", format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")

def get_base_dir() -> Path:
    return Path.cwd()

BASE_DIR = get_base_dir()
MODELS_DIR = BASE_DIR / "models"
CACHE_DIR = BASE_DIR / ".cache"

# Initialize env
MODELS_DIR.mkdir(exist_ok=True)
CACHE_DIR.mkdir(exist_ok=True)
