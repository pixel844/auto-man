from auto_man.prompting import PromptHandler


def test_qwen_prompt_tagging():
    """Verify Qwen-specific tags are correctly applied."""
    handler = PromptHandler("qwen2.5-7b")
    prompt = "Hello"
    tagged = handler.get_prompt_with_tag(prompt)
    assert "<|im_start|>user\nHello<|im_end|>\n<|im_start|>assistant\n" == tagged


def test_default_prompt_tagging():
    """Verify default tags are correctly applied for other models."""
    handler = PromptHandler("phi-3-mini")
    prompt = "Hello"
    tagged = handler.get_prompt_with_tag(prompt)
    assert "<|user|>\nHello<|assistant|>\n" == tagged
