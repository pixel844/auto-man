import argparse
import sys
from pathlib import Path
from loguru import logger


def main():
    # Fix import path to include src directory directly
    p = Path(__file__).parent
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
    
    # Setup environment before any heavy imports
    from system_checks import run_all_checks

    parser = argparse.ArgumentParser(description="Auto-Man NPU")
    parser.add_argument("-r", "--repo", help="Repo Path or URL")
    parser.add_argument("-p", "--prompt", help="Custom prompt")
    parser.add_argument("--gui", action="store_true", help="Launch GUI")
    args = parser.parse_args()

    run_all_checks()

    if args.gui:
        from PyQt6.QtWidgets import QApplication
        from gui import MainWindow
        app = QApplication(sys.argv)
        w = MainWindow(); w.show(); sys.exit(app.exec())

    if args.repo:
        from cli import run_workflow
        run_workflow(args.repo, args.prompt)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
