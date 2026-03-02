import json
import shutil
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
import subprocess
import stat
from loguru import logger

from auto_man.config import CACHE_DIR, REGISTRY_PATH
from llmware.library import Library
from llmware.retrieval import Query


class RepoEntry:
    def __init__(
        self,
        id: str,
        type: str,
        url_or_path: str,
        last_indexed: Optional[str] = None,
        status: str = "pending",
    ):
        self.id = id
        self.type = type
        self.url_or_path = url_or_path
        self.last_indexed = last_indexed
        self.status = status

    def to_dict(self):
        return {
            "id": self.id,
            "type": self.type,
            "url_or_path": self.url_or_path,
            "last_indexed": self.last_indexed,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(**data)


class Rag:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.cache_dir = CACHE_DIR
        self.cache_dir.mkdir(exist_ok=True)
        self.registry_path = REGISTRY_PATH
        self.library_name = "auto_man_temp_lib"
        self.library = None

    def _load_registry(self) -> List[RepoEntry]:
        if not self.registry_path.exists():
            return []
        try:
            with open(self.registry_path, "rb") as f:
                import orjson
                data = orjson.loads(f.read())
                return [RepoEntry.from_dict(d) for d in data]
        except Exception as e:
            logger.warning(f"Failed to load registry: {e}")
            return []

    def _save_registry(self, registry: List[RepoEntry]):
        try:
            import orjson
            with open(self.registry_path, "wb") as f:
                f.write(orjson.dumps([e.to_dict() for e in registry], option=orjson.OPT_INDENT_2))
        except Exception as e:
            logger.error(f"Failed to save registry: {e}")

    def add_repo(self, url_or_path: str, is_remote: bool) -> str:
        registry = self._load_registry()
        repo_id = str(uuid.uuid4())[:8]
        entry = RepoEntry(
            id=repo_id,
            type="remote" if is_remote else "local",
            url_or_path=url_or_path,
        )
        registry.append(entry)
        self._save_registry(registry)
        logger.info(f"Added repository: {url_or_path} (id: {repo_id})")
        return repo_id

    def index_repo(self, repo_id: str) -> bool:
        registry = self._load_registry()
        entry = next((e for e in registry if e.id == repo_id), None)
        if not entry:
            raise ValueError(f"Repo ID {repo_id} not found")

        if entry.type == "remote":
            root = self.cache_dir / "repos" / repo_id
            if not root.exists():
                root.mkdir(parents=True, exist_ok=True)
                logger.info(f"Cloning remote repository {entry.url_or_path} to {root}")
                subprocess.run(
                    ["git", "clone", "--depth", "1", entry.url_or_path, str(root)],
                    check=True
                )
        else:
            root = Path(entry.url_or_path)

        self.library_name = f"lib_{repo_id}_{datetime.now().strftime('%H%M%S')}"
        logger.info(f"Creating LLMWare library: {self.library_name}")
        self.library = Library().create_new_library(self.library_name)

        with tempfile.TemporaryDirectory() as tmp_scan_dir:
            scan_path = Path(tmp_scan_dir)
            extensions = {
                ".py", ".md", ".txt", ".sh", ".js", ".ts", ".rs", ".c", ".cpp", ".toml",
            }

            for file_path in root.rglob("*"):
                if any(
                    part in {".venv", "venv", ".git", "__pycache__", "target", "build"}
                    for part in file_path.parts
                ):
                    continue
                if file_path.is_file() and file_path.suffix.lower() in extensions:
                    try:
                        content = file_path.read_text(encoding="utf-8", errors="ignore")
                        if not content.strip():
                            continue

                        chunks = self._chunk_text(content)
                        # Sanitize relative name for filesystem compatibility
                        rel_name = str(file_path.relative_to(root)).replace("/", "_").replace("\\", "_")

                        for i, chunk in enumerate(chunks):
                            chunk_file = scan_path / f"{rel_name}_chunk{i}.txt"
                            chunk_file.write_text(chunk, encoding="utf-8")
                    except Exception as e:
                        logger.warning(f"Could not process {file_path}: {e}")

            if any(scan_path.iterdir()) and self.library:
                logger.info(f"Adding files to library from {scan_path}")
                self.library.add_files(input_folder_path=str(scan_path))

        self.library = Library().load_library(self.library_name)
        entry.status = "indexed"
        entry.last_indexed = datetime.now(timezone.utc).isoformat()
        self._save_registry(registry)
        logger.info(f"Successfully indexed repository: {repo_id}")
        return True

    def _chunk_text(
        self, text: str, max_chars: int = 2000, overlap: int = 200
    ) -> List[str]:
        chunks = []
        start = 0
        while start < len(text):
            end = start + max_chars
            if end >= len(text):
                chunks.append(text[start:])
                break
            last_newline = text.rfind("\n", start, end)
            if last_newline != -1 and last_newline > start + max_chars // 2:
                end = last_newline
            chunks.append(text[start:end])
            start = end - overlap
        return chunks

    def retrieve_context(self, query_str: str) -> str:
        if not self.library:
            if not self.library_name:
                return ""
            self.library = Library().load_library(self.library_name)

        logger.debug(f"Retrieving context for query: {query_str}")
        results = Query(self.library).get_whole_library()
        results.sort(key=lambda x: (x.get("file_source", ""), x.get("block_ID", 0)))

        context_parts = []
        current_length = 0
        MAX_CHARS = 4000  # Further reduced for stability

        # PRIORITY: include these files fully
        priority_files = {"main.py", "mcp_server.py", "requirements.txt", "README.md"}

        # Pass 1: Core application logic
        for res in results:
            file_src = res.get("file_source", "")
            if not any(p in file_src for p in priority_files):
                continue
            text = (res.get("text_search") or res.get("text") or "").strip()
            if not text:
                continue
            chunk = f"\n=== FILE: {file_src} ===\n{text}\n"
            if current_length + len(chunk) > MAX_CHARS:
                break
            context_parts.append(chunk)
            current_length += len(chunk)

        # Pass 2: Other details
        for res in results:
            if current_length >= MAX_CHARS:
                break
            file_src = res.get("file_source", "")
            if any(p in file_src for p in priority_files):
                continue
            text = (res.get("text_search") or res.get("text") or "").strip()
            if not text:
                continue
            chunk = f"\n=== FILE: {file_src} ===\n{text}\n"
            if current_length + len(chunk) > MAX_CHARS:
                break
            context_parts.append(chunk)
            current_length += len(chunk)

        return "".join(context_parts)

    def cleanup(self):
        if self.library:
            try:
                logger.info(f"Deleting RAG library: {self.library_name}")
                self.library.delete_library()
                self.library = None
                self.library_name = None
            except Exception as e:
                logger.debug(f"Error deleting library: {e}")

        if self.cache_dir.exists():
            try:
                logger.info("Purging local cache directory")
                def remove_readonly(func, path, _):
                    Path(path).chmod(stat.S_IWRITE)
                    func(path)

                shutil.rmtree(self.cache_dir, onerror=remove_readonly)
                self.cache_dir.mkdir(exist_ok=True)
            except Exception as e:
                logger.warning(f"Warning during cache purge: {e}")
