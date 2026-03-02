import time
import re
import gc
from typing import Callable
from loguru import logger
from llmware.models import ModelCatalog
from llmware.configs import LLMWareConfig
from system_checks import is_snapdragon

class LlmEngine:
    def __init__(self):
        from config import BASE_DIR
        LLMWareConfig().set_home(str(BASE_DIR / "models"))
        
        # Priority NPU Model
        self.model_name = "qwen2.5-7b-instruct-onnx-qnn"
        self.model = None
        
        try:
            if is_snapdragon():
                logger.info(f"Loading NPU Model: {self.model_name}")
                # Use max_output=4096 as requested
                self.model = ModelCatalog().load_model(self.model_name, max_output=4096)
                logger.success("NPU Model constructed.")
            else:
                self._load_fallback()
        except Exception as e:
            logger.warning(f"NPU fail: {e}")
            self._load_fallback()

    def _load_fallback(self):
        self.model_name = "bling-phi-3-onnx"
        logger.info(f"Loading CPU Fallback: {self.model_name}")
        self.model = ModelCatalog().load_model(self.model_name, max_output=4096)

    def generate(self, prompt: str, callback: Callable[[str], None]):
        # Tag setup
        tag_u, tag_a = ("<|im_start|>user\n", "<|im_end|>\n<|im_start|>assistant\n") if "qwen" in self.model_name else ("<|user|>\n", "<|assistant|>\n")
        full_prompt = f"{tag_u}{prompt}{tag_a}"
        
        raw_output = ""
        sent_len = 0
        max_tokens = 4096
        token_count = 0
        early_stop = False
        
        try:
            for token in self.model.stream(full_prompt):
                token_str = str(token)
                raw_output += token_str
                
                # Strip tags and technical artifacts
                clean = re.sub(r'<[^>]*>?(:)?', '', raw_output)
                unwanted = ["<bot>:", "<|assistant|>", "<bot>", "<|bot|>", "<|end|>", "<|im_end|>"]
                for u in unwanted: 
                    clean = clean.replace(u, "")
                
                new_chunk = clean[sent_len:]
                if new_chunk:
                    callback(new_chunk)
                    sent_len = len(clean)
                
                # Repetition break
                if len(clean) > 500:
                    tail = clean[-100:]
                    if clean.count(tail) > 2:
                        logger.warning("Stream repetition detected. Breaking.")
                        early_stop = True
                        break
                
                token_count += 1
                if token_count >= max_tokens:
                    break
                
        except Exception as e:
            logger.error(f"Generation error: {e}")
        finally:
            # CORE FIX: Explicitly call llmware's cleanup for early stopping
            if early_stop and hasattr(self.model, "cleanup_stream_gen_on_early_stop"):
                logger.info("Cleaning up early-stopped stream...")
                self.model.cleanup_stream_gen_on_early_stop()

    def cleanup(self):
        """Explicitly attempt to release NPU resources."""
        try:
            if self.model:
                logger.info("Releasing Model resources...")
                # Attempt to call unload_model if it exists (though likely not implemented)
                if hasattr(self.model, "unload_model"):
                    self.model.unload_model()
                
                # Clear references and force GC
                self.model = None
                gc.collect()
                logger.success("Resources released.")
        except Exception as e:
            logger.debug(f"Cleanup error: {e}")
