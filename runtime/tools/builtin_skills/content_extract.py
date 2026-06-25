from typing import Any

from runtime.tools.builtin_skills.base import BaseCodeSkill


class ContentExtractSkill(BaseCodeSkill):
    """
    文本提取 Code Skill。
    """

    name = "content_extract"

    async def run(self, payload: dict[str, Any], context: Any) -> dict[str, Any]:
        """
        执行文本提取。
        """
        content = str(payload.get("content") or "").strip()
        mode = str(payload.get("extract_mode") or "key_points")
        if not content:
            return {
                "status": "missing_params",
                "data": {},
                "summary": "缺少需要处理的原始文本",
                "missing_params": ["content"],
                "error": None,
            }
        if mode == "summary":
            data = {"summary": self._summary(content)}
            summary = "已生成文本摘要"
        elif mode == "outline":
            data = {"outline": self._items(content)}
            summary = f"已生成 {len(data['outline'])} 条大纲"
        else:
            data = {"items": self._items(content)}
            summary = f"已提取 {len(data['items'])} 个关键要点"
        return {
            "status": "success",
            "data": data,
            "summary": summary,
            "missing_params": [],
            "error": None,
        }

    def _summary(self, content: str) -> str:
        """
        生成简短摘要。
        """
        return content[:180] if len(content) > 180 else content

    def _items(self, content: str) -> list[dict[str, str]]:
        """
        提取条目。
        """
        normalized = (
            content.replace("；", "\n")
            .replace("。", "\n")
            .replace("，", "\n")
            .replace("、", "\n")
        )
        fragments = [item.strip(" \n\t:：") for item in normalized.split("\n")]
        items = [item for item in fragments if item]
        return [
            {"title": f"要点 {index + 1}", "detail": item}
            for index, item in enumerate(items[:8])
        ] or [{"title": "要点 1", "detail": content[:180]}]
