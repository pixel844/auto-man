import argparse
import sys
from pathlib import Path
from loguru import logger

from auto_man.cli import run_cli_workflow, select_model
from auto_man.config import BASE_DIR, MODELS_DIR
from auto_man.rag import Rag


def main():
    """Main entry point for Auto-Man CLI and GUI."""
    parser = argparse.ArgumentParser(
        description="Auto-Man: NPU-Accelerated Manual Generator"
    )
    parser.add_argument("-m", "--model_path", help="Path to model directory")
    parser.add_argument("-r", "--repo", help="Repository URL or local path")
    parser.add_argument("-p", "--prompt", help="Run single generation")
    parser.add_argument("--mcp", action="store_true", help="Start MCP server")
    parser.add_argument("--gui", action="store_true", help="Start PyQt6 GUI")
    parser.add_argument(
        "--reset", action="store_true", help="Uninstall custom models and clear cache"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose output"
    )
    args = parser.parse_args()

    # Set log level based on verbose flag
    if not args.verbose:
        logger.remove()
        logger.add(sys.stderr, level="INFO")

    models_dir = MODELS_DIR

    if args.reset:
        logger.info("Resetting Auto-Man Environment...")
        # 1. Clear .cache
        rag = Rag(BASE_DIR)
        rag.cleanup()

        # 2. Uninstall non-default models
        if models_dir.exists():
            logger.info(f"Cleaning models in {models_dir} (preserving model_repo)...")
            import shutil

            for item in models_dir.iterdir():
                if item.is_dir() and item.name != "model_repo":
                    logger.info(f"Removing custom model: {item.name}")
                    try:
                        shutil.rmtree(item)
                    except Exception as e:
                        logger.warning(f"Could not remove {item.name}: {e}")
        logger.success("Reset complete.")
        sys.exit(0)

    # Model Selection
    model_dir = Path(args.model_path) if args.model_path else select_model(models_dir)

    if args.gui:
        from PyQt6.QtWidgets import QApplication
        from auto_man.gui import MainWindow

        app = QApplication(sys.argv)
        window = MainWindow(model_dir=model_dir, repo_url=args.repo)
        window.show()
        sys.exit(app.exec())

    logger.info("Auto-Man Starting...")
    run_cli_workflow(args, model_dir)


if __name__ == "__main__":
    main()
