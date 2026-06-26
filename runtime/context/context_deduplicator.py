import hashlib
from typing import Any


class ContextDeduplicator:
    """
    上下文原始对话去重器。
    """

    def dedupe_event_dialogues(
        self,
        recent_turns: list[dict[str, Any]],
        event_dialogues: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        去除已经存在于 recent_turns 中的事件对话。

        Args:
            recent_turns (list[dict[str, Any]]): 当前 session 最近原始对话。
            event_dialogues (list[dict[str, Any]]): 命中事件原始对话。

        Returns:
            list[dict[str, Any]]: 去重后的事件对话。
        """
        recent_keys = {self.dialogue_key(turn) for turn in recent_turns}
        deduped: list[dict[str, Any]] = []
        for dialogue in event_dialogues:
            if self.dialogue_key(dialogue) in recent_keys:
                continue
            deduped.append(dialogue)
        return deduped

    def dialogue_key(self, dialogue: dict[str, Any]) -> str:
        """
        构建对话去重键。

        Args:
            dialogue (dict[str, Any]): 对话数据。

        Returns:
            str: 去重键。
        """
        turn_id = str(dialogue.get("turn_id") or "").strip()
        if turn_id:
            return f"turn:{turn_id}"
        run_id = str(dialogue.get("run_id") or "").strip()
        if run_id:
            return f"run:{run_id}"
        agent_id = str(dialogue.get("agent_id") or "").strip()
        user = str(
            dialogue.get("user")
            or dialogue.get("user_message")
            or ""
        )
        assistant = str(
            dialogue.get("assistant")
            or dialogue.get("assistant_message")
            or dialogue.get("final_answer")
            or ""
        )
        raw = f"{agent_id}\n{user}\n{assistant}"
        return "sha1:" + hashlib.sha1(raw.encode("utf-8")).hexdigest()
