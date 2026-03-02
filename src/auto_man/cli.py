import json
import shutil
import sys
from pathlib import Path
from typing import Callable

from auto_man.config import BASE_DIR, get_models_dir
from auto_man.llm_engine import LlmEngine
from auto_man.manual_generation import generate_manual
from auto_man.mcp_server import McpServer
from auto_man.prompting import PromptHandler
from auto_man.rag import Rag


def run_reset_mode():
    """Reset Auto-Man environment: clear cache and uninstall custom models."""
    print("--- Resetting Auto-Man Environment ---")

    # 1. Clear .cache
    rag = Rag(BASE_DIR)
    rag.cleanup()

    # 2. Uninstall non-default models
    models_dir = get_models_dir()
    if models_dir.exists():
        print(f"Cleaning models in {models_dir} (preserving model_repo)...")

        for item in models_dir.iterdir():
            if item.is_dir() and item.name != "model_repo":
                print(f"Removing custom model: {item.name}")
                try:
                    shutil.rmtree(item)
                except Exception as e:
                    print(f"Warning: Could not remove {item.name}: {e}")
    print("Reset complete.")
    sys.exit(0)


def run_mcp_mode(model: LlmEngine, rag: Rag):
    """Run MCP server mode, processing JSON-RPC requests from stdin."""
    server = McpServer(model, rag)

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


def run_single_prompt(model: LlmEngine, prompt: str):
    """Run single prompt generation."""
    handler = PromptHandler(model.model_name)
    tagged_prompt = handler.get_prompt_with_tag(prompt)
    model.generate(tagged_prompt, lambda t: print(t, end="", flush=True))
    print()


def run_repo_manual_flow(
    model: LlmEngine,
    rag: Rag,
    repo_url: str,
    confirm_fn: Callable[[], bool] = None,
    output_fn: Callable[[str], None] = None,
):
    """
    Run the default CLI flow: fetch tree, confirm, index, and generate manual.

    Args:
        model: The LLM engine
        rag: The RAG system
        repo_url: Repository URL or path
        confirm_fn: Function to get user confirmation (defaults to input)
        output_fn: Function for output (defaults to print)
    """
    if confirm_fn is None:

        def confirm_fn():
            return input("\nGenerate manual? (y/n): ").lower() == "y"

    if output_fn is None:
        output_fn = print

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
    output_fn(
        "\n--- Repository Structure ---\n"
        + tree_resp["result"]["content"][0]["text"]
        + "\n----------------------------"
    )
    if not confirm_fn():
        return

    # Indexing
    output_fn("\n[1/2] Indexing context...")
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
    output_fn("[2/2] Generating .man page...\n")
    repo_name = repo_url.rstrip("/").split("/")[-1].replace(".git", "")
    output_path = Path.cwd() / f"{repo_name}.man"

    generate_manual(model, rag, repo_url, output_path)
    output_fn(f"\n\nSaved to: {output_path}")
