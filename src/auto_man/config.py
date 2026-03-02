import sys
from pathlib import Path

from llmware.configs import LLMWareConfig


def get_base_dir() -> Path:
    """Get the base directory for the application."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent


# Global configuration
BASE_DIR = get_base_dir()
# Set llmware home to models/
LLMWareConfig().set_home(str(BASE_DIR / "models"))


def get_models_dir() -> Path:
    """Get the models directory."""
    return BASE_DIR / "models"


def get_available_models(models_dir: Path):
    """Get list of available models in the models directory."""
    available = []
    search_paths = [models_dir, models_dir / "model_repo"]
    for path in search_paths:
        if not path.exists():
            continue
        for d in path.iterdir():
            if d.is_dir() and (d / "model.onnx").exists():
                if d not in available:
                    available.append(d)
    return available


def select_model(models_dir: Path) -> Path:
    """Select a model from available models, with fallback to default."""
    available = get_available_models(models_dir)
    if not available:
        catalog_name = "qwen2.5-7b-instruct-onnx-qnn"
        return models_dir / "model_repo" / catalog_name

    if len(available) == 1:
        return available[0]

    print("\nAvailable models:")
    for i, m in enumerate(available):
        print(f"[{i}] {m.name}")

    while True:
        try:
            choice = input(f"Select a model (0-{len(available)-1}): ").strip()
            idx = int(choice)
            if 0 <= idx < len(available):
                return available[idx]
        except (ValueError, IndexError):
            pass
        print("Invalid selection.")
