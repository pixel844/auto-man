class PromptHandler:
    """Formatter for LLM prompts with model-specific tags."""

    def __init__(self, model_name: str = ""):
        if "qwen" in model_name.lower():
            self.user_tag = "<|im_start|>user\n"
            self.assistant_tag = "<|im_end|>\n<|im_start|>assistant\n"
        else:
            self.user_tag = "<|user|>\n"
            self.assistant_tag = "<|assistant|>\n"

    def get_prompt_with_tag(self, prompt: str) -> str:
        """Wrap prompt with model-specific user and assistant tags."""
        return f"{self.user_tag}{prompt}{self.assistant_tag}"


ROFF_TEMPLATE = """You are a technical writer. Generate a ROFF .man page for '{project_name}'.
Identify and describe these flags from the code: --repo, --gui, --mcp, --reset, --prompt, --model_path.

--- ROFF TEMPLATE ---
.TH {project_name_upper} 1
.SH NAME
{project_name} \\- NPU manual generator
.SH SYNOPSIS
python main.py [options]
.SH DESCRIPTION
[Summarize tool]
.SH OPTIONS
[Describe flags]
.SH EXAMPLES
[Usage example]
--- END TEMPLATE ---

--- CODE ---
{full_context}
"""
