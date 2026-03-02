import argparse
import sys
from pathlib import Path

from auto_man.cli import (
    run_mcp_mode,
    run_repo_manual_flow,
    run_reset_mode,
    run_single_prompt,
)
from auto_man.config import get_models_dir, select_model
from auto_man.llm_engine import LlmEngine
from auto_man.rag import Rag


def main():
    """Main entry point for Auto-Man CLI."""
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

    # Handle reset mode first (doesn't need model initialization)
    if args.reset:
        run_reset_mode()

    # Model Selection
    models_dir = get_models_dir()
    model_dir = Path(args.model_path) if args.model_path else select_model(models_dir)

    # Handle GUI mode
    if args.gui:
        from PyQt6.QtWidgets import QApplication

        from auto_man import gui

        app = QApplication(sys.argv)
        window = gui.MainWindow(model_dir=model_dir, repo_url=args.repo)
        window.show()
        sys.exit(app.exec())

    # Initialize engines for other modes
    print("--- Auto-Man Starting ---")
    model = LlmEngine()
    rag = Rag(Path(__file__).parent.parent)  # Point to project root

    try:
        if args.mcp:
            run_mcp_mode(model, rag)
        elif args.prompt:
            run_single_prompt(model, args.prompt)
        else:
            # Default CLI Flow
            repo_url = args.repo or input("Repo link: ").strip()
            if not repo_url:
                return
            run_repo_manual_flow(model, rag, repo_url)
    finally:
        rag.cleanup()


if __name__ == "__main__":
    main()
