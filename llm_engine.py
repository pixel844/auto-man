from llmware.models import ModelCatalog
from llmware.configs import LLMWareConfig
import os
from pathlib import Path
import time
from typing import Callable

class GenerationStats:
    def __init__(self, ttft: float, total_duration: float, total_tokens: int):
        self.ttft = ttft
        self.total_duration = total_duration
        self.total_tokens = total_tokens

    def tps(self) -> float:
        if self.total_duration > 0:
            return self.total_tokens / self.total_duration
        return 0.0

class LlmEngine:
    def __init__(self, model_path: Path, tokenizer_path: Path):
        self.model_dir = model_path.parent
        self.model_name = self.model_dir.name
        self.using_fallback = False
        
        # Detect platform for proactive fallback
        import platform
        machine = platform.machine().lower()
        is_arm = "arm" in machine or "aarch" in machine
        
        # We can also load by name if it's a known catalog model
        # Default to qwen if no local path exists or we want specific model
        catalog_name = "qwen2.5-7b-instruct-onnx-qnn"
        
        try:
            if not is_arm:
                print(f"Detected {machine} architecture. NPU models requires ARM64. Switching to CPU fallback immediately.")
                raise OSError("Architecture mismatch for QNN")

            if not ModelCatalog().lookup_model_card(catalog_name):
                 # If it's not in catalog, and we have local path, register it
                 if model_path.exists():
                     self._register_local_model(self.model_name, self.model_dir)
                     self.model_name = self.model_name
                 else:
                     # Fallback to catalog name which will trigger download by llmware
                     self.model_name = catalog_name
            else:
                self.model_name = catalog_name
            
            # load model with max_output as suggested
            print(f"Attempting to load NPU model: {self.model_name}")
            self.model = ModelCatalog().load_model(self.model_name, max_output=512)
            
        except (Exception, RuntimeError, OSError) as e:
            print(f"\n[WARNING] NPU Model Load Failed: {e}")
            print("[INFO] Switching to CPU Fallback Model (GGUF)...")
            self.using_fallback = True
            
            # Fallback to a reliable CPU model
            fallback_model = "phi-3-mini-instruct-gguf"
            
            # Ensure fallback is in catalog or download it
            self.model = ModelCatalog().load_model(fallback_model, max_output=512)
            self.model_name = fallback_model
            print(f"[SUCCESS] Loaded CPU Model: {fallback_model}")

    def _register_local_model(self, name: str, model_dir: Path):
        onnx_files = [f.name for f in model_dir.glob("*.onnx")]
        
        model_card = {
            "model_name": name,
            "display_name": name,
            "model_family": "ONNXGenerativeModel",
            "model_category": "generative_local",
            "model_location": "llmware_repo",
            "context_window": 4096,
            "instruction_following": True,
            "prompt_wrapper": "chatml", # Qwen 2.5 uses ChatML usually
            "temperature": 0.0,
            "sample_default": False,
            "tokenizer_local": "tokenizer.json",
            "custom_model_files": onnx_files,
            "validation_files": onnx_files,
            "hf_repo": ""
        }
        
        llmware_model_repo = Path(LLMWareConfig().get_model_repo_path())
        target_dir = llmware_model_repo / name
        
        if not target_dir.exists():
            target_dir.mkdir(parents=True, exist_ok=True)
            import shutil
            for item in model_dir.iterdir():
                if item.is_file():
                    shutil.copy2(item, target_dir / item.name)

        ModelCatalog().register_new_model_card(model_card)

    def reset(self):
        pass

    def generate(self, prompt: str, callback: Callable[[str], None]) -> GenerationStats:
        start_time = time.perf_counter()
        token_count = 0
        first_token_time = None
        
        # Using the stream method from the example
        for token in self.model.stream(prompt):
            if first_token_time is None:
                first_token_time = time.perf_counter() - start_time
            
            callback(token)
            token_count += 1
            
        total_duration = time.perf_counter() - start_time
        return GenerationStats(
            ttft=first_token_time or total_duration,
            total_duration=total_duration,
            total_tokens=token_count
        )
