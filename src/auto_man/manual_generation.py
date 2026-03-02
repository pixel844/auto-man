import re


def clean_roff_content(content: str) -> str:
    """Sanitize LLM output by removing ROFF control characters."""
    # Remove character followed by backspace (bold/underline simulation)
    content = re.sub(r".\x08", "", content)
    # Remove remaining backspaces
    content = content.replace("\x08", "")
    # Remove literal backslash-b that some models output
    content = content.replace("\\b", "")
    return content


def format_man_filename(repo_url: str) -> str:
    """Generate a .man filename from a repository URL."""
    repo_name = repo_url.rstrip("/").split("/")[-1].replace(".git", "")
    return f"{repo_name}.man"
