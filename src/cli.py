from pathlib import Path
from loguru import logger
from llm_engine import LlmEngine
from rag import Rag

def run_workflow(repo_path: str, prompt_override: str = None):
    # 1. Setup
    model = LlmEngine()
    rag = Rag()
    
    try:
        # 2. Index
        rag.index_repo(repo_path)
        context = rag.get_context()
        
        # 3. Specific, Simplified Prompt
        prompt = prompt_override or (
            "Task: Generate an extremely concise ROFF .man page.\n"
            "Required Sections:\n"
            "1. NAME: Short one-sentence summary of the project.\n"
            "2. OPTIONS: List and describe only the command line arguments found in the code.\n"
            "Constraints: Do not include installation, setup, or long descriptions. Be brief.\n\n"
            f"CODE CONTEXT:\n{context}"
        )
        
        # 4. Generate
        print("\n--- GENERATING CONCISE MANUAL ---\n")
        content = []
        def collect(t): print(t, end="", flush=True); content.append(t)
        model.generate(prompt, collect)
        
        # 5. Save
        repo_name = repo_path.rstrip("/").split("/")[-1].replace(".git", "")
        out_path = Path.cwd() / f"{repo_name}.man"
        out_path.write_text("".join(content), encoding="utf-8")
        logger.success(f"\n\nSaved to: {out_path}")
        
    finally:
        logger.info("Cleaning up session...")
        model.cleanup()
        rag.cleanup()
