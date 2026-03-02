import shutil
import tempfile
from pathlib import Path
import json
import uuid
from datetime import datetime
from typing import List, Optional
import os

from llmware.library import Library
from llmware.retrieval import Query

class RepoEntry:
    def __init__(self, id: str, type: str, url_or_path: str, last_indexed: Optional[str] = None, status: str = "pending"):
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
            "status": self.status
        }

    @classmethod
    def from_dict(cls, data):
        return cls(**data)

class Rag:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.easydocz_dir = project_root / ".easydocz"
        self.easydocz_dir.mkdir(exist_ok=True)
        self.registry_path = self.easydocz_dir / "repos.json"
        
        self.library_name = "auto_man_temp_lib"
        self.library = None

    def _load_registry(self) -> List[RepoEntry]:
        if not self.registry_path.exists():
            return []
        with open(self.registry_path, 'r') as f:
            try:
                data = json.load(f)
                return [RepoEntry.from_dict(d) for d in data]
            except:
                return []

    def _save_registry(self, registry: List[RepoEntry]):
        with open(self.registry_path, 'w') as f:
            json.dump([e.to_dict() for e in registry], f, indent=4)

    def add_repo(self, url_or_path: str, is_remote: bool) -> str:
        registry = self._load_registry()
        repo_id = str(uuid.uuid4())[:8]
        entry = RepoEntry(
            id=repo_id,
            type="remote" if is_remote else "local",
            url_or_path=url_or_path,
            status="pending"
        )
        registry.append(entry)
        self._save_registry(registry)
        return repo_id

    def index_repo(self, repo_id: str) -> bool:
        registry = self._load_registry()
        entry = next((e for e in registry if e.id == repo_id), None)
        if not entry:
            raise ValueError(f"Repo ID {repo_id} not found")

        if entry.type == "remote":
            root = self.easydocz_dir / "repos" / repo_id
            if not root.exists():
                root.mkdir(parents=True, exist_ok=True)
                import subprocess
                subprocess.run(["git", "clone", "--depth", "1", entry.url_or_path, str(root)])
        else:
            root = Path(entry.url_or_path)

        self.library_name = f"lib_{repo_id}_{datetime.now().strftime('%H%M%S')}"
        self.library = Library().create_new_library(self.library_name)

        with tempfile.TemporaryDirectory() as tmp_scan_dir:
            scan_path = Path(tmp_scan_dir)
            extensions = [".py", ".md", ".txt", ".sh", ".js", ".ts", ".rs", ".c", ".cpp"]
            indexed_count = 0
            
            for file_path in root.rglob("*"):
                if any(part in [".venv", "venv", ".git", "__pycache__", "target", "build"] for part in file_path.parts):
                    continue
                    
                if file_path.is_file() and file_path.suffix.lower() in extensions:
                    rel_name = str(file_path.relative_to(root)).replace(os.sep, "_")
                    safe_name = f"{rel_name}.txt"
                    shutil.copy2(file_path, scan_path / safe_name)
                    indexed_count += 1

            if indexed_count > 0:
                self.library.add_files(input_folder_path=str(scan_path))

        self.library = Library().load_library(self.library_name)
        
        entry.status = "indexed"
        entry.last_indexed = datetime.utcnow().isoformat()
        self._save_registry(registry)
        return True

    def retrieve_context(self, query_str: str) -> str:
        lib = Library().load_library(self.library_name)
        results = Query(lib).get_whole_library()
        
        results.sort(key=lambda x: (x.get("file_source", ""), x.get("block_ID", 0)))
        
        context_parts = []
        current_file = ""
        current_length = 0
        MAX_CHARS = 5000 

        priority_files = ["main.py", "requirements.txt", "README.md"]
        
        for res in results:
            file_source = res.get("file_source", "unknown")
            is_priority = any(p in file_source for p in priority_files)
            if not is_priority: continue
            
            text = (res.get("text_search") or res.get("text") or res.get("content") or "").strip()
            if not text: continue

            block_text = ""
            if file_source != current_file:
                block_text += f"\n=== FILE: {file_source} ===\n"
                current_file = file_source
            block_text += text + "\n"
            
            if current_length + len(block_text) > MAX_CHARS:
                break
            context_parts.append(block_text)
            current_length += len(block_text)

        for res in results:
            if current_length >= MAX_CHARS: break
            
            file_source = res.get("file_source", "unknown")
            is_priority = any(p in file_source for p in priority_files)
            if is_priority: continue
            
            text = (res.get("text_search") or res.get("text") or res.get("content") or "").strip()
            if not text: continue

            block_text = ""
            if file_source != current_file:
                block_text += f"\n=== FILE: {file_source} ===\n"
                current_file = file_source
            block_text += text + "\n"
            
            if current_length + len(block_text) > MAX_CHARS:
                break
            context_parts.append(block_text)
            current_length += len(block_text)

        return "".join(context_parts)
