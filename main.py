import argparse
import sys
from pathlib import Path

# Configuration
from llmware.configs import LLMWareConfig

from llm_engine import LlmEngine
from mcp_server import McpServer
from rag import Rag


def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent


BASE_DIR = get_base_dir()
# Set llmware home to models/
LLMWareConfig().set_home(str(BASE_DIR / "models"))


class PromptHandler:
    def __init__(self, model_name: str = ""):
        if "qwen" in model_name.lower():
            self.user_tag = "<|im_start|>user\n"
            self.assistant_tag = "<|im_end|>\n<|im_start|>assistant\n"
        else:
            self.user_tag = "<|user|>\n"
            self.assistant_tag = "<|assistant|>\n"

    def get_prompt_with_tag(self, prompt: str) -> str:
        return f"{self.user_tag}{prompt}{self.assistant_tag}"


def get_available_models(models_dir: Path):
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


def main():
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

    models_dir = BASE_DIR / "models"

    if args.reset:
        print("--- Resetting Auto-Man Environment ---")
        # 1. Clear .cache
        rag = Rag(BASE_DIR)
        rag.cleanup()

        # 2. Uninstall non-default models
        if models_dir.exists():
            print(f"Cleaning models in {models_dir} (preserving model_repo)...")
            import shutil

            for item in models_dir.iterdir():
                if item.is_dir() and item.name != "model_repo":
                    print(f"Removing custom model: {item.name}")
                    try:
                        shutil.rmtree(item)
                    except Exception as e:
                        print(f"Warning: Could not remove {item.name}: {e}")
        print("Reset complete.")
        sys.exit(0)

    # Model Selection

    model_dir = Path(args.model_path) if args.model_path else select_model(models_dir)

    if args.gui:
        from PyQt6.QtWidgets import QApplication

        import gui

        app = QApplication(sys.argv)
        window = gui.MainWindow(model_dir=model_dir, repo_url=args.repo)
        window.show()
        sys.exit(app.exec())

    print("--- Auto-Man Starting ---")
    run(args, model_dir)


def run(args, model_dir):
    # Initialize Engines
    model = LlmEngine()
    rag = Rag(BASE_DIR)

    try:
        if args.mcp:
            server = McpServer(model, rag)
            import json

            for line in sys.stdin:
                line = line.strip()
                if not line:
                    continue
                try:
                    request = json.loads(line)
                    response = server.handle_request(request)
                    print(json.dumps(response))
                    sys.stdout.flush()
                except (json.JSONDecodeError, Exception):
                    pass
        elif args.prompt:
            handler = PromptHandler(model.model_name)
            tagged_prompt = handler.get_prompt_with_tag(args.prompt)
            model.generate(tagged_prompt, lambda t: print(t, end="", flush=True))
            print()
        else:
            # Default CLI Flow
            repo_url = args.repo or input("Repo link: ").strip()
            if not repo_url:
                return

            server = McpServer(model, rag)

            # Confirmation step
            tree_resp = server.handle_request(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "fetch_tree",
                    "params": {"url": repo_url},
                }
            )
            print(
                "\n--- Repository Structure ---\n"
                + tree_resp["result"]["content"][0]["text"]
                + "\n----------------------------"
            )
            if input("\nGenerate manual? (y/n): ").lower() != "y":
                return

            # Indexing
            print("\n[1/2] Indexing context...")
            is_remote = repo_url.startswith("http") or repo_url.endswith(".git")
            add_resp = server.handle_request(
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "add_repo",
                    "params": {"url": repo_url, "is_remote": is_remote},
                }
            )
            repo_id = add_resp["result"]["content"][0]["text"].split(": ")[1]
            server.handle_request(
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "index_repo",
                    "params": {"id": repo_id},
                }
            )

            # Generation
            print("[2/2] Generating .man page...\n")
            repo_name = repo_url.rstrip("/").split("/")[-1].replace(".git", "")
            output_path = Path.cwd() / f"{repo_name}.man"

            full_context = rag.retrieve_context("Full project source code")
            handler = PromptHandler(model.model_name)
            prompt = handler.get_prompt_with_tag(
                "You are a technical writer. Generate a ROFF .man page for 'Auto-Man'.\n"
                "Identify and describe these flags from the code: --repo, --gui, --mcp, --reset, --prompt, --model_path.\n\n"
                "--- ROFF TEMPLATE ---\n"
                ".TH AUTO-MAN 1\n"
                ".SH NAME\n"
                "auto-man \\- NPU manual generator\n"
                ".SH SYNOPSIS\n"
                "python main.py [options]\n"
                ".SH DESCRIPTION\n"
                "[Summarize tool]\n"
                ".SH OPTIONS\n"
                "[Describe flags]\n"
                ".SH EXAMPLES\n"
                "[Usage example]\n"
                "--- END TEMPLATE ---\n\n"
                f"--- CODE ---\n{full_context}"
            )

            content = []
            model.generate(
                prompt, lambda t: (print(t, end="", flush=True), content.append(t))
            )

            # Clean the final content
            final_content = "".join(content)
            import re

            final_content = re.sub(r".\x08", "", final_content)
            final_content = final_content.replace("\x08", "").replace("\\b", "")

            output_path.write_text(final_content, encoding="utf-8")
            print(f"\n\nSaved to: {output_path}")

    finally:
        rag.cleanup()


if __name__ == "__main__":
    main()
