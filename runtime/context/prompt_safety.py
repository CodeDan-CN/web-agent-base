from copy import deepcopy
from typing import Any


EVENT_ID_KEYS = {
    "event_id",
    "parent_event_id",
    "event_chain_id",
    "matched_event_id",
    "related_event_id",
    "turn_id",
    "run_id",
    "summary_batch_id",
}


def remove_event_identifiers(value: Any) -> Any:
    """
    移除不应进入模型 Prompt 的事件标识字段。

    Args:
        value (Any): 原始对象。

    Returns:
        Any: 移除事件标识后的对象。
    """
    copied = deepcopy(value)
    return _remove_event_identifiers(copied)


def _remove_event_identifiers(value: Any) -> Any:
    """
    递归移除事件标识字段。

    Args:
        value (Any): 原始对象。

    Returns:
        Any: 处理后的对象。
    """
    if isinstance(value, dict):
        return {
            key: _remove_event_identifiers(item)
            for key, item in value.items()
            if str(key) not in EVENT_ID_KEYS
        }
    if isinstance(value, list):
        return [_remove_event_identifiers(item) for item in value]
    return value
