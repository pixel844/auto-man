class PromptHandler:
    """Handles prompt formatting with model-specific tags."""

    def __init__(self, model_name: str = ""):
        if "qwen" in model_name.lower():
            self.user_tag = "<|im_start|>user\n"
            self.assistant_tag = "<|im_end|>\n<|im_start|>assistant\n"
        else:
            self.user_tag = "<|user|>\n"
            self.assistant_tag = "<|assistant|>\n"

    def get_prompt_with_tag(self, prompt: str) -> str:
        """Format a prompt with appropriate tags for the model."""
        return f"{self.user_tag}{prompt}{self.assistant_tag}"


def make_single_prompt(model_name: str, user_prompt: str) -> str:
    """Create a complete prompt for single generation."""
    handler = PromptHandler(model_name)
    return handler.get_prompt_with_tag(user_prompt)
