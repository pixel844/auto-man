from pathlib import Path
import subprocess
from loguru import logger
from llmware.library import Library
from llmware.retrieval import Query
from llmware.configs import LLMWareConfig
from config import CACHE_DIR

class Rag:
    def __init__(self):
        from config import BASE_DIR
        LLMWareConfig().set_home(str(BASE_DIR / "models"))
        self.library_name = "auto_man_lib"
        self.library = None

    def index_repo(self, repo_path_or_url: str):
        # 1. Resolve path
        is_remote = "http" in repo_path_or_url or repo_path_or_url.endswith(".git")
        root = Path(repo_path_or_url)
        
        if is_remote:
            root = CACHE_DIR / "current_repo"
            if root.exists():
                import shutil
                def rm_ro(f, p, e): Path(p).chmod(0o777); f(p)
                shutil.rmtree(root, onerror=rm_ro)
            logger.info(f"Cloning {repo_path_or_url}...")
            subprocess.run(["git", "clone", "--depth", "1", repo_path_or_url, str(root)], check=True)

        # 2. Index via llmware with custom splitting/chunking
        logger.info("Indexing context with optimized chunking...")
        try:
            Library().delete_library(self.library_name)
        except: pass
        
        self.library = Library().create_new_library(self.library_name)
        
        # Applying custom chunking parameters for RAG splitting
        self.library.add_files(
            input_folder_path=str(root),
            chunk_size=400,         # Target size in characters
            max_chunk_size=600,     # Absolute maximum size
            smart_chunking=1        # Natural boundary splitting (paragraphs/sentences)
        )
        return True

    def get_context(self):
        logger.info("Retrieving project context...")
        if not self.library:
            self.library = Library().load_library(self.library_name)
            
        results = Query(self.library).get_whole_library()
        results.sort(key=lambda x: (x.get("file_source", ""), x.get("block_ID", 0)))
        
        # Max context window for the model is 4096, so we'll cap retrieval to leave room for generation
        context, total = "", 0
        MAX_CONTEXT_CHARS = 12000 # ~3000-4000 tokens depending on density
        
        for r in results:
            text = (r.get("text_search") or r.get("text") or "").strip()
            if not text: continue
            chunk = f"\nFILE: {r.get('file_source')}\n{text}\n"
            if total + len(chunk) > MAX_CONTEXT_CHARS: break
            context += chunk; total += len(chunk)
        return context

    def cleanup(self):
        self.library = None
        logger.debug("RAG reference cleared.")
