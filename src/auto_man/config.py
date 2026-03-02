import sys
from pathlib import Path
from loguru import logger

# Configure loguru
logger.remove()
logger.add(sys.stderr, level="INFO", format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")

def get_base_dir() -> Path:
    """Resolve the base directory, handling PyInstaller frozen state."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent.parent.parent


BASE_DIR = get_base_dir()
MODELS_DIR = BASE_DIR / "models"
CACHE_DIR = BASE_DIR / ".cache"
REGISTRY_PATH = CACHE_DIR / "repos.json"
