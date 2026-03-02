import json
import threading
from typing import Dict, Any, Optional

class McpServer:
    def __init__(self, model, rag):
        self.model = model
        self.rag = rag
        self.lock = threading.Lock()

    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        req_id = request.get("id")
        method = request.get("method")
        params = request.get("params")

        try:
            if method == "initialize":
                result = self.handle_initialize(params)
            elif method == "tools/list":
                result = self.handle_list_tools(params)
            elif method == "fetch_tree":
                result = self.fetch_tree(params)
            elif method == "add_repo":
                result = self.add_repo(params)
            elif method == "index_repo":
                result = self.index_repo(params)
            elif method == "tools/call":
                result = self.handle_call_tool(params)
            else:
                raise ValueError(f"Method not found: {method}")

            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": result
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {
                    "code": -32601,
                    "message": str(e)
                }
            }

    def handle_initialize(self, params: Optional[Dict]) -> Dict:
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {}
            },
            "serverInfo": {
                "name": "auto-man-python",
                "version": "0.1.0"
            }
        }

    def handle_list_tools(self, params: Optional[Dict]) -> Dict:
        return {
            "tools": [
                {
                    "name": "fetch_tree",
                    "description": "Get the file tree of a repository for confirmation.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "url": { "type": "string" }
                        },
                        "required": ["url"]
                    }
                },
                {
                    "name": "complete",
                    "description": "Run LLM completion with Phi-3.5 ONNX. Returns the full response text.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "prompt": { "type": "string" }
                        },
                        "required": ["prompt"]
                    }
                },
                {
                    "name": "query_rag",
                    "description": "Answer a question using RAG context from indexed repos.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "query": { "type": "string" }
                        },
                        "required": ["query"]
                    }
                },
                {
                    "name": "add_repo",
                    "description": "Add a repository to the registry.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "url": { "type": "string" },
                            "is_remote": { "type": "boolean" }
                        },
                        "required": ["url"]
                    }
                },
                {
                    "name": "index_repo",
                    "description": "Index a repository for retrieval.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "id": { "type": "string" }
                        },
                        "required": ["id"]
                    }
                },
                {
                    "name": "generate_man",
                    "description": "Generate a technical manual page (.man) for a repository.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "repo_id": { "type": "string" },
                            "output_path": { "type": "string" }
                        },
                        "required": ["repo_id"]
                    }
                },
                {
                    "name": "reset_conversation",
                    "description": "Reset the conversation history.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {}
                    }
                }
            ]
        }

    def handle_call_tool(self, params: Dict) -> Dict:
        name = params.get("name")
        arguments = params.get("arguments", {})

        if name == "fetch_tree":
            return self.fetch_tree(arguments)
        elif name == "complete":
            return self.complete(arguments)
        elif name == "query_rag":
            return self.query_rag(arguments)
        elif name == "add_repo":
            return self.add_repo(arguments)
        elif name == "index_repo":
            return self.index_repo(arguments)
        elif name == "generate_man":
            return self.generate_man(arguments)
        elif name == "reset_conversation":
            return self.reset_conversation(arguments)
        else:
            raise ValueError(f"Unknown tool: {name}")

    def complete(self, args: Dict) -> Dict:
        prompt = args.get("prompt")
        if not prompt: raise ValueError("Missing prompt")
        
        response_parts = []
        with self.lock:
            stats = self.model.generate(prompt, lambda t: response_parts.append(t))
        
        final_response = "".join(response_parts)
        return {
            "content": [{ "type": "text", "text": final_response }],
            "metadata": {
                "ttft_ms": int(stats.ttft * 1000),
                "tps": stats.tps(),
                "total_tokens": stats.total_tokens
            }
        }

    def query_rag(self, args: Dict) -> Dict:
        query = args.get("query")
        if not query: raise ValueError("Missing query")
        
        context = self.rag.retrieve_context(query)
        prompt = f"Use the following context:\n\n{context}\n\nQuestion: {query}" if context else query

        response_parts = []
        with self.lock:
            stats = self.model.generate(prompt, lambda t: response_parts.append(t))
        
        final_response = "".join(response_parts)
        return {
            "content": [{ "type": "text", "text": final_response }],
            "metadata": {
                "ttft_ms": int(stats.ttft * 1000),
                "tps": stats.tps(),
                "total_tokens": stats.total_tokens
            }
        }

    def add_repo(self, args: Dict) -> Dict:
        url = args.get("url")
        is_remote = args.get("is_remote", True)
        if not url: raise ValueError("Missing url")
        
        repo_id = self.rag.add_repo(url, is_remote)
        return { "content": [{ "type": "text", "text": f"Added repo with ID: {repo_id}" }] }

    def index_repo(self, args: Dict) -> Dict:
        repo_id = args.get("id")
        if not repo_id: raise ValueError("Missing id")
        
        success = self.rag.index_repo(repo_id)
        return { "content": [{ "type": "text", "text": f"Index success: {success}" }] }

    def fetch_tree(self, args: Dict) -> Dict:
        url = args.get("url")
        if not url: raise ValueError("Missing url")
        
        from pathlib import Path
        is_remote = url.startswith("http") or url.endswith(".git")
        path = Path(url)
        
        if is_remote:
            import tempfile
            import subprocess
            import shutil
            import stat
            
            temp_dir = Path(tempfile.gettempdir()) / "auto_man_preview"
            
            def remove_readonly(func, path, _):
                import os
                os.chmod(path, stat.S_IWRITE)
                func(path)

            if temp_dir.exists():
                shutil.rmtree(temp_dir, onerror=remove_readonly)
            
            print(f"[Preview] Cloning {url} for tree view...")
            res = subprocess.run(["git", "clone", "--depth", "1", url, str(temp_dir)], 
                                 capture_output=True, text=True)
            if res.returncode != 0:
                return { "content": [{ "type": "text", "text": f"Error cloning repo: {res.stderr}" }] }
            path = temp_dir

        if not path.exists():
            return { "content": [{ "type": "text", "text": f"Error: Path {url} not found." }] }
        
        import os
        tree = []
        for root, dirs, files in os.walk(path):
            level = root.replace(str(path), '').count(os.sep)
            indent = ' ' * 4 * (level)
            tree.append(f"{indent}{os.path.basename(root)}/")
            sub_indent = ' ' * 4 * (level + 1)
            for f in files:
                tree.append(f"{sub_indent}{f}")
            if level > 2: break # Limit depth for preview
            
        return { "content": [{ "type": "text", "text": "\n".join(tree) }] }

    def _clean_roff(self, text: str) -> str:
        # Remove literal \b and actual backspace characters
        import re
        # Remove character followed by backspace (bold/underline simulation)
        text = re.sub(r'.\x08', '', text)
        # Remove remaining backspaces
        text = text.replace('\x08', '')
        # Remove literal \b that some models output
        text = text.replace('\\b', '')
        return text

    def generate_man(self, args: Dict) -> Dict:
        repo_id = args.get("repo_id")
        if not repo_id: raise ValueError("Missing repo_id")
        
        # Try to find the original repo name for the filename
        repo_name = "output"
        registry = self.rag._load_registry()
        entry = next((e for e in registry if e.id == repo_id), None)
        if entry:
            repo_name = entry.url_or_path.rstrip('/').split('/')[-1].replace('.git', '')
        
        output_filename = f"{repo_name}.man"
        from pathlib import Path
        output_path = Path.cwd() / output_filename
        
        # Multiple RAG queries for better context
        summary_context = self.rag.retrieve_context("General purpose and summary of the project")
        commands_context = self.rag.retrieve_context("Command line arguments, CLI flags, and main entry points")
        examples_context = self.rag.retrieve_context("Usage examples and typical command lines")
        
        full_context = f"--- SUMMARY ---\n{summary_context}\n\n--- COMMANDS & ARGS ---\n{commands_context}\n\n--- EXAMPLES ---\n{examples_context}"
        
        prompt = (
            "Generate a comprehensive technical manual page (.man) in standard ROFF format. "
            "The output MUST include the following sections:\n"
            "1. NAME: The name of the project.\n"
            "2. SYNOPSIS: Brief command line usage patterns.\n"
            "3. DESCRIPTION: Detailed summary of what the project does.\n"
            "4. COMMANDS: A list of all available commands and their purpose.\n"
            "5. OPTIONS/ARGUMENTS: For each command, list all flags, arguments, and their descriptions.\n"
            "6. EXAMPLES: Realistic usage examples.\n\n"
            f"Use the following RAG context from the repository:\n\n{full_context}"
        )

        response_parts = []
        with self.lock:
            self.model.generate(prompt, lambda t: response_parts.append(t))

        final_man_content = self._clean_roff("".join(response_parts))
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(final_man_content)
        
        return { "content": [{ "type": "text", "text": f"Successfully generated .man file at {output_path}" }] }

    def reset_conversation(self, args: Dict) -> Dict:
        with self.lock:
            self.model.reset()
        return { "content": [{ "type": "text", "text": "Conversation history reset." }] }
