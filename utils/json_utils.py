import json
from typing import Any

from exception.error_code import BizErrorCode


def parse_json_object(text: str) -> dict[str, Any]:
    """
    从模型输出中解析 JSON 对象。

    Args:
        text (str): 模型输出文本。

    Returns:
        dict[str, Any]: JSON 对象。

    Raises:
        BizException: JSON 无法解析或不是对象。
    """
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:].strip()
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start < 0 or end <= start:
            raise BizErrorCode.ACTION_PARSE_ERROR.exception(str(exc)) from exc
        parsed = json.loads(cleaned[start : end + 1])
    if not isinstance(parsed, dict):
        raise BizErrorCode.ACTION_PARSE_ERROR.exception("模型输出不是 JSON 对象")
    return parsed
