from llmware.library import Library
from llmware.prompts import Prompt
from llmware.configs import LLMWareConfig
from pathlib import Path
import json
import uuid
from datetime import datetime
from typing import List, Optional

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
        
        self.library_name = "auto_man_library"
        
        try:
            self.library = Library().get_library(self.library_name)
        except:
            self.library = Library().create_new_library(self.library_name)

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

        self.library.add_files(input_folder_path=str(root))
        
        entry.status = "indexed"
        entry.last_indexed = datetime.utcnow().isoformat()
        self._save_registry(registry)
        return True

    def retrieve_context(self, query_str: str) -> str:
        prompter = Prompt()
        # add_source_new_query adds materials to prompter.source_materials
        prompter.add_source_new_query(library=self.library, query=query_str, result_count=5)
        
        context_parts = []
        # prompter.source_materials is a list of batches
        # Each batch is a dict: {'batch_id', 'text', 'metadata', 'biblio', ...}
        for batch in prompter.source_materials:
            text = batch.get("text", "")
            # metadata in batch is a list of metadata for each entry in the batch
            metadata_list = batch.get("metadata", [])
            file_source = "unknown"
            if metadata_list:
                file_source = metadata_list[0].get("source_name", "unknown")
            
            context_parts.append(f"[{file_source}]\n{text}")
            
        return "\n\n---\n\n".join(context_parts)
