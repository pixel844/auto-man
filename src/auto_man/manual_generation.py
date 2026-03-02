import re
from pathlib import Path
from typing import Callable

from auto_man.llm_engine import LlmEngine
from auto_man.prompting import PromptHandler
from auto_man.rag import Rag


def build_manual_prompt(model_name: str, full_context: str) -> str:
    """
    Build a complete prompt for generating a ROFF manual page.

    Args:
        model_name: Name of the LLM model being used
        full_context: Retrieved context from RAG system

    Returns:
        Complete prompt string with appropriate formatting
    """
    handler = PromptHandler(model_name)
    prompt_content = (
        "You are a technical writer. Generate a ROFF .man page for 'Auto-Man'.\n"
        "Identify and describe these flags from the code: --repo, --gui, --mcp, --reset, --prompt, --model_path.\n\n"
        "--- ROFF TEMPLATE ---\n"
        ".TH AUTO-MAN 1\n"
        ".SH NAME\n"
        "auto-man \\- NPU manual generator\n"
        ".SH SYNOPSIS\n"
        "python main.py [options]\n"
        ".SH DESCRIPTION\n"
        "[Summarize tool]\n"
        ".SH OPTIONS\n"
        "[Describe flags]\n"
        ".SH EXAMPLES\n"
        "[Usage example]\n"
        "--- END TEMPLATE ---\n\n"
        f"--- CODE ---\n{full_context}"
    )
    return handler.get_prompt_with_tag(prompt_content)


def generate_manual_content(
    model: LlmEngine,
    rag: Rag,
    repo_url: str,
    token_callback: Callable[[str], None] = None,
) -> str:
    """
    Generate manual page content for a repository.

    Args:
        model: The LLM engine to use for generation
        rag: The RAG system with indexed repository context
        repo_url: URL or path of the repository
        token_callback: Optional callback for streaming tokens

    Returns:
        Raw generated content as a string
    """
    full_context = rag.retrieve_context("Full project source code")
    prompt = build_manual_prompt(model.model_name, full_context)

    content_parts = []

    def collect_token(token: str):
        content_parts.append(token)
        if token_callback:
            token_callback(token)

    model.generate(prompt, collect_token)
    return "".join(content_parts)


def clean_roff_content(content: str) -> str:
    """
    Clean ROFF content by removing backspace artifacts and control characters.

    Args:
        content: Raw generated content

    Returns:
        Cleaned content suitable for writing to a .man file
    """
    # Remove character followed by backspace (bold/underline simulation)
    content = re.sub(r".\x08", "", content)
    # Remove remaining backspaces
    content = content.replace("\x08", "")
    # Remove literal \b that some models output
    content = content.replace("\\b", "")
    return content


# Backward compatibility alias
_clean_roff = clean_roff_content


def generate_manual(
    model: LlmEngine,
    rag: Rag,
    repo_url: str,
    output_path: Path,
    token_callback: Callable[[str], None] = None,
) -> Path:
    """
    Generate and save a manual page for a repository.

    Args:
        model: The LLM engine to use for generation
        rag: The RAG system with indexed repository context
        repo_url: URL or path of the repository
        output_path: Path where to save the .man file
        token_callback: Optional callback for streaming tokens

    Returns:
        Path to the generated manual file
    """
    raw_content = generate_manual_content(model, rag, repo_url, token_callback)
    cleaned_content = clean_roff_content(raw_content)

    output_path.write_text(cleaned_content, encoding="utf-8")
    return output_path
