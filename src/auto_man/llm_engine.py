from llmware.models import ModelCatalog
import time
from pathlib import Path
from typing import Callable, Optional
from loguru import logger


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
    def __init__(
        self, model_path: Optional[Path] = None, tokenizer_path: Optional[Path] = None
    ):
        self.is_npu = False
        self.model_name = "qwen2.5-7b-instruct-onnx-qnn"

        try:
            logger.info(f"Initializing NPU model: {self.model_name}...")
            # llmware handles NPU discovery automatically for onnx-qnn models
            self.model = ModelCatalog().load_model(self.model_name, max_output=512)
            self.is_npu = True
            logger.success("NPU acceleration engaged.")
        except Exception as e:
            logger.warning(f"NPU initialization failed: {e}")
            logger.info("Falling back to CPU model...")
            self.model_name = "bling-phi-3-mini-instruct"
            self.model = ModelCatalog().load_model(self.model_name, max_output=512)
            self.is_npu = False
            logger.info(f"CPU model '{self.model_name}' loaded.")

    def generate(self, prompt: str, callback: Callable[[str], None]) -> GenerationStats:
        start_time = time.perf_counter()
        token_count = 0
        first_token_time = None

        # Some models might need a slightly different stream iteration
        try:
            for token in self.model.stream(prompt):
                if not token:
                    continue

                # Ensure it's a clean string
                token_str = str(token)

                if first_token_time is None:
                    first_token_time = time.perf_counter() - start_time

                callback(token_str)
                token_count += 1
        except Exception as e:
            logger.error(f"Error during generation: {e}")

        total_duration = time.perf_counter() - start_time
        return GenerationStats(
            ttft=first_token_time or total_duration,
            total_duration=total_duration,
            total_tokens=token_count,
        )

    def reset(self):
        pass
