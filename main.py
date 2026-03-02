import os
import sys
import argparse
from pathlib import Path
from typing import Optional

# Set up llmware config
from llmware.configs import LLMWareConfig

from llm_engine import LlmEngine
from rag import Rag
from mcp_server import McpServer
import setup_npu

def get_base_dir() -> Path:
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).parent

# Foundation: Set the llmware home to project-local models folder
BASE_DIR = get_base_dir()
MODELS_HOME = BASE_DIR / "models"
MODELS_HOME.mkdir(parents=True, exist_ok=True)
LLMWareConfig().set_home(str(MODELS_HOME))

# llmware creates 'model_repo' inside the home path
DEFAULT_MODELS_DIR = MODELS_HOME / "model_repo"

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

def chat_split(end_line: bool):
    split_line = "-" * 80
    print(f"\n{split_line}", end="")
    if end_line:
        print()

def get_available_models(models_dir: Path):
    available = []
    # Check models/ and models/model_repo/ (where llmware downloads)
    search_paths = [models_dir, models_dir / "model_repo"]
    
    for path in search_paths:
        if not path.exists(): continue
        for d in path.iterdir():
            if d.is_dir() and (d / "model.onnx").exists() and (d / "tokenizer.json").exists():
                if d not in available:
                    available.append(d)
    return available

def select_model(models_dir: Path) -> Path:
    available = get_available_models(models_dir)
    
    if not available:
        catalog_name = "qwen2.5-7b-instruct-onnx-qnn"
        print(f"No local models found. Defaulting to '{catalog_name}' in models/model_repo.")
        return models_dir / "model_repo" / catalog_name
    
    if len(available) == 1:
        print(f"Using only available model: {available[0].name}")
        return available[0]
    
    print("\nAvailable models:")
    for i, m in enumerate(available):
        print(f"[{i}] {m.name} ({m.parent.name})")
    
    while True:
        try:
            choice = input(f"Select a model (0-{len(available)-1}): ").strip()
            idx = int(choice)
            if 0 <= idx < len(available):
                return available[idx]
        except (ValueError, IndexError, EOFError, KeyboardInterrupt):
            pass
        print("Invalid selection. Please try again.")

def main():
    parser = argparse.ArgumentParser(
        description="Auto-Man: A local universal (.man) generator using Qualcomm NPU acceleration (LLMWare Edition)."
    )
    parser.add_argument("-m", "--model_path", help="Path to the model directory")
    parser.add_argument("-r", "--repo", help="Repository URL or local path")
    parser.add_argument("-p", "--prompt", help="Run a single generation and exit")
    parser.add_argument("--mcp", action="store_true", help="Start the MCP server loop")
    parser.add_argument("--gui", action="store_true", help="Start the PyQt6 GUI")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    
    args = parser.parse_args()

    base_dir = BASE_DIR # Use the globally resolved BASE_DIR
    lib_dir = base_dir / "lib"
    
    # Bundle OS-specific binaries if QAIRT is found
    setup_npu.ensure_npu_env(lib_dir)

    models_dir = base_dir / "models"
    
    try:
        model_dir = Path(args.model_path) if args.model_path else select_model(models_dir)
    except Exception as e:
        print(f"Error selecting model: {e}")
        sys.exit(1)

    if args.gui:
        import gui
        from PyQt6.QtWidgets import QApplication
        app = QApplication(sys.argv)
        window = gui.MainWindow(model_dir=model_dir, repo_url=args.repo)
        window.show()
        sys.exit(app.exec())

    print("--- Auto-Man Starting (LLMWare + Qwen Edition) ---")
    
    try:
        run(args, model_dir)
    except Exception as e:
        print(f"\n[FATAL ERROR] Application failed to start:\n  {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

def run(args, model_dir):
    model_path = model_dir / "model.onnx" if model_dir.exists() and model_dir.is_dir() else model_dir
    tokenizer_path = model_dir / "tokenizer.json" if model_dir.exists() and model_dir.is_dir() else model_dir
    
    model = LlmEngine(model_path, tokenizer_path)
    rag = Rag(BASE_DIR)
    
    print(f"Model and RAG engine loaded successfully.")

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
            except Exception as e:
                err_resp = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": { "code": -32700, "message": f"Parse error: {e}" }
                }
                print(json.dumps(err_resp))
                sys.stdout.flush()
    elif args.prompt:
        handler = PromptHandler(model.model_name)
        tagged_prompt = handler.get_prompt_with_tag(args.prompt)
        print(f"Prompt: {args.prompt}")
        print("Output: ", end="", flush=True)
        model.generate(tagged_prompt, lambda token: print(token, end="", flush=True))
        print()
    else:
        repo_url = args.repo
        if not repo_url:
            try:
                repo_url = input("Repo link: ").strip()
            except (EOFError, KeyboardInterrupt):
                return

        if not repo_url:
            print("No repository provided. Exiting.")
            return

        server = McpServer(model, rag)
        
        print(f"\nScanning {repo_url}...")
        tree_resp = server.handle_request({
            "jsonrpc": "2.0", "id": 1, "method": "fetch_tree", "params": {"url": repo_url}
        })
        
        if "error" in tree_resp:
            print(f"Error: {tree_resp['error']['message']}")
            return
            
        print("\n--- Repository Structure ---")
        print(tree_resp["result"]["content"][0]["text"])
        print("----------------------------")
        
        try:
            confirm = input("\nDo you want to generate a manual for this repository? (y/n): ").lower()
        except (EOFError, KeyboardInterrupt):
            return
            
        if confirm != 'y':
            print("Operation cancelled.")
            return

        print("\n[1/2] Indexing repository context...")
        add_resp = server.handle_request({
            "jsonrpc": "2.0", "id": 2, "method": "add_repo", "params": {"url": repo_url, "is_remote": False}
        })
        repo_id = add_resp["result"]["content"][0]["text"].split(": ")[1]
        server.handle_request({
            "jsonrpc": "2.0", "id": 3, "method": "index_repo", "params": {"id": repo_id}
        })

        print("[2/2] Generating .man page (Streaming)...\n")
        
        repo_name = repo_url.rstrip('/').split('/')[-1].replace('.git', '')
        output_filename = f"{repo_name}.man"
        output_path = Path.cwd() / output_filename

        summary_context = rag.retrieve_context(f"General purpose and summary of repo {repo_id}")
        commands_context = rag.retrieve_context(f"Command line arguments, CLI flags, and main entry points in repo {repo_id}")
        examples_context = rag.retrieve_context(f"Usage examples and typical command lines in repo {repo_id}")
        
        full_context = f"--- SUMMARY ---\n{summary_context}\n\n--- COMMANDS & ARGS ---\n{commands_context}\n\n--- EXAMPLES ---\n{examples_context}"
        
        handler = PromptHandler(model.model_name)
        prompt = handler.get_prompt_with_tag(
            "Generate a comprehensive technical manual page (.man) in standard ROFF format. "
            "The output MUST include: NAME, SYNOPSIS, DESCRIPTION, COMMANDS, OPTIONS/ARGUMENTS, and EXAMPLES.\n\n"
            f"Use the following RAG context:\n\n{full_context}"
        )

        output_content = []
        def cli_callback(token):
            print(token, end="", flush=True)
            output_content.append(token)

        model.generate(prompt, cli_callback)
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("".join(output_content))
            
        print(f"\n\nSuccess! Technical manual saved to: {output_path}")

if __name__ == "__main__":
    main()
