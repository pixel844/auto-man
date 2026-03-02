import os
import sys
import argparse
from pathlib import Path
from typing import Optional

# Configuration
from llmware.configs import LLMWareConfig

from llm_engine import LlmEngine
from rag import Rag
from mcp_server import McpServer
import setup_npu

def get_base_dir() -> Path:
    if getattr(sys, 'frozen', False):
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
        if not path.exists(): continue
        for d in path.iterdir():
            if d.is_dir() and (d / "model.onnx").exists():
                if d not in available: available.append(d)
    return available

def select_model(models_dir: Path) -> Path:
    available = get_available_models(models_dir)
    if not available:
        catalog_name = "qwen2.5-7b-instruct-onnx-qnn"
        return models_dir / "model_repo" / catalog_name
    
    if len(available) == 1: return available[0]
    
    print("\nAvailable models:")
    for i, m in enumerate(available):
        print(f"[{i}] {m.name}")
    
    while True:
        try:
            choice = input(f"Select a model (0-{len(available)-1}): ").strip()
            idx = int(choice)
            if 0 <= idx < len(available): return available[idx]
        except: pass
        print("Invalid selection.")

def main():
    parser = argparse.ArgumentParser(description="Auto-Man: NPU-Accelerated Manual Generator")
    parser.add_argument("-m", "--model_path", help="Path to model directory")
    parser.add_argument("-r", "--repo", help="Repository URL or local path")
    parser.add_argument("-p", "--prompt", help="Run single generation")
    parser.add_argument("--mcp", action="store_true", help="Start MCP server")
    parser.add_argument("--gui", action="store_true", help="Start PyQt6 GUI")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    args = parser.parse_args()

    # 1. Setup NPU Binaries
    setup_npu.ensure_npu_env(BASE_DIR / "lib")

    # 2. Select Model
    models_dir = BASE_DIR / "models"
    model_dir = Path(args.model_path) if args.model_path else select_model(models_dir)

    if args.gui:
        import gui
        from PyQt6.QtWidgets import QApplication
        app = QApplication(sys.argv)
        window = gui.MainWindow(model_dir=model_dir, repo_url=args.repo)
        window.show()
        sys.exit(app.exec())

    print("--- Auto-Man Starting ---")
    run(args, model_dir)

def run(args, model_dir):
    # 1. Initialize Engines
    model = LlmEngine()
    rag = Rag(BASE_DIR)
    
    if args.mcp:
        server = McpServer(model, rag)
        import json
        for line in sys.stdin:
            line = line.strip()
            if not line: continue
            try:
                request = json.loads(line)
                response = server.handle_request(request)
                print(json.dumps(response))
                sys.stdout.flush()
            except: pass
    elif args.prompt:
        handler = PromptHandler(model.model_name)
        tagged_prompt = handler.get_prompt_with_tag(args.prompt)
        model.generate(tagged_prompt, lambda t: print(t, end="", flush=True))
        print()
    else:
        # Default CLI Flow
        repo_url = args.repo or input("Repo link: ").strip()
        if not repo_url: return

        server = McpServer(model, rag)
        
        # Confirmation step
        tree_resp = server.handle_request({"jsonrpc":"2.0","id":1,"method":"fetch_tree","params":{"url":repo_url}})
        print("\n--- Repository Structure ---\n" + tree_resp["result"]["content"][0]["text"] + "\n----------------------------")
        if input("\nGenerate manual? (y/n): ").lower() != 'y': return

        # Indexing
        print("\n[1/2] Indexing context...")
        is_remote = repo_url.startswith("http") or repo_url.endswith(".git")
        add_resp = server.handle_request({"jsonrpc":"2.0","id":2,"method":"add_repo","params":{"url":repo_url,"is_remote":is_remote}})
        repo_id = add_resp["result"]["content"][0]["text"].split(": ")[1]
        server.handle_request({"jsonrpc":"2.0","id":3,"method":"index_repo","params":{"id":repo_id}})

        # Generation
        print("[2/2] Generating .man page...\n")
        repo_name = repo_url.rstrip('/').split('/')[-1].replace('.git', '')
        output_path = Path.cwd() / f"{repo_name}.man"
        
        full_context = rag.retrieve_context("Full project source code")
        handler = PromptHandler(model.model_name)
        prompt = handler.get_prompt_with_tag(
            f"Extract CLI flags and logic from this source code to fill the template for 'Auto-Man'.\n"
            "Template: .TH AUTO-MAN 1, .SH NAME, .SH SYNOPSIS, .SH DESCRIPTION, .SH OPTIONS, .SH EXAMPLES.\n"
            f"SOURCE:\n{full_context}"
        )

        content = []
        model.generate(prompt, lambda t: (print(t, end="", flush=True), content.append(t)))
        output_path.write_text("".join(content), encoding="utf-8")
        print(f"\n\nSaved to: {output_path}")

if __name__ == "__main__":
    main()
