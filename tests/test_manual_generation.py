from auto_man.manual_generation import clean_roff_content, format_man_filename


def test_clean_roff_content():
    """Verify ROFF content is correctly sanitized."""
    # Test bold simulation removal: B\x08B -> B
    raw_content = "B\x08BO\x08OL\x08LD\x08D"
    cleaned = clean_roff_content(raw_content)
    assert cleaned == "BOLD"

    # Test literal \b and backspace removal
    # Note: re.sub(r".\x08", ...) removes the character before \x08 too.
    raw_content = "content with \\b and backspaces\x08"
    cleaned = clean_roff_content(raw_content)
    assert cleaned == "content with  and backspace"


def test_format_man_filename_remote():
    """Verify filename generation from remote Git URL."""
    url = "https://github.com/user/project.git"
    assert format_man_filename(url) == "project.man"


def test_format_man_filename_local():
    """Verify filename generation from local path."""
    url = "/path/to/my-project"
    assert format_man_filename(url) == "my-project.man"
