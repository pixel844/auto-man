import sys
from pathlib import Path
from loguru import logger
import orjson

from auto_man.config import BASE_DIR, MODELS_DIR
from auto_man.llm_engine import LlmEngine
from auto_man.manual_generation import clean_roff_content, format_man_filename
from auto_man.mcp_server import McpServer
from auto_man.prompting import ROFF_TEMPLATE, PromptHandler
from auto_man.rag import Rag


def get_available_models(models_dir: Path):
    """Retrieve available ONNX-QNN models in the model directory."""
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
    """Prompt user to select a model or return default if only one is available."""
    available = get_available_models(models_dir)
    if not available:
        catalog_name = "qwen2.5-7b-instruct-onnx-qnn"
        return Path(models_dir / "model_repo" / catalog_name)

    if len(available) == 1:
        return Path(available[0])

    print("\nAvailable models:")
    for i, m in enumerate(available):
        print(f"[{i}] {m.name}")

    while True:
        try:
            choice = input(f"Select a model (0-{len(available)-1}): ").strip()
            idx = int(choice)
            if 0 <= idx < len(available):
                return Path(available[idx])
        except (ValueError, EOFError, KeyboardInterrupt):
            pass
        print("Invalid selection.")


def run_cli_workflow(args, model_dir):
    """Execution logic for CLI generation and prompts."""
    model = LlmEngine()
    rag = Rag(BASE_DIR)

    try:
        if args.mcp:
            server = McpServer(model, rag)
            logger.info("Starting MCP server loop (reading from stdin)")
            for line in sys.stdin:
                line = line.strip()
                if not line:
                    continue
                try:
                    request = orjson.loads(line)
                    response = server.handle_request(request)
                    sys.stdout.write(orjson.dumps(response).decode() + "\n")
                    sys.stdout.flush()
                except Exception as e:
                    logger.error(f"MCP loop error: {e}")
        elif args.prompt:
            handler = PromptHandler(model.model_name)
            tagged_prompt = handler.get_prompt_with_tag(args.prompt)

            def print_token(t):
                print(t, end="", flush=True)

            model.generate(tagged_prompt, print_token)
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
            logger.info("Starting indexing process...")
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
            logger.info("Generating manual page...")
            output_filename = format_man_filename(repo_url)
            output_path = Path.cwd() / output_filename

            full_context = rag.retrieve_context("Full project source code")
            handler = PromptHandler(model.model_name)

            prompt = handler.get_prompt_with_tag(
                ROFF_TEMPLATE.format(
                    project_name="Auto-Man",
                    project_name_upper="AUTO-MAN",
                    full_context=full_context,
                )
            )

            content = []

            def collect_token(t):
                print(t, end="", flush=True)
                content.append(t)

            model.generate(prompt, collect_token)

            # Clean and save the final content
            final_content = clean_roff_content("".join(content))
            output_path.write_text(final_content, encoding="utf-8")
            logger.success(f"Manual saved to: {output_path}")

    finally:
        rag.cleanup()
