import re


ENGLISH_WORD_RE = re.compile(r"[A-Za-z0-9_]+")


def estimate_text_tokens(text: str) -> int:
    """
    估算文本 token 数。

    Args:
        text (str): 待估算文本。

    Returns:
        int: 近似 token 数。
    """
    stripped = text.strip()
    if not stripped:
        return 0
    english_words = ENGLISH_WORD_RE.findall(stripped)
    english_chars = sum(len(word) for word in english_words)
    other_chars = max(len(stripped) - english_chars, 0)
    return max(int(other_chars / 1.5) + len(english_words), 1)


def estimate_turn_tokens(user_message: str, assistant_message: str) -> int:
    """
    估算一轮对话 token 数。

    Args:
        user_message (str): 用户输入。
        assistant_message (str): Agent 回复。

    Returns:
        int: 近似 token 数。
    """
    return estimate_text_tokens(f"用户: {user_message}\n助手: {assistant_message}")
