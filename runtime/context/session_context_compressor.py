import json

from schema.db.conversation_turn import ConversationTurn
from utils.llm_client import LLMClient


class SessionContextCompressor:
    """
    当前 session 会话摘要压缩器。
    """

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        """
        初始化压缩器。

        Args:
            llm_client (LLMClient | None): 模型客户端。
        """
        self.llm_client = llm_client or LLMClient()

    async def compress(
        self,
        previous_summary: str,
        turns: list[ConversationTurn],
        target_tokens: int,
    ) -> str:
        """
        压缩较早 conversation_turns。

        Args:
            previous_summary (str): 已有会话摘要。
            turns (list[ConversationTurn]): 待压缩对话。
            target_tokens (int): 目标 token 数。

        Returns:
            str: 新会话摘要。
        """
        system_prompt = (
            "你是当前 session 的会话上下文压缩器。"
            "只输出摘要正文，不要输出 Markdown。"
            "摘要只服务当前会话，不要写入长期记忆。"
        )
        user_prompt = json.dumps(
            {
                "previous_summary": previous_summary,
                "turns_to_compress": [
                    {
                        "user": turn.user_message,
                        "assistant": turn.assistant_message,
                        "final_state": turn.final_state,
                    }
                    for turn in turns
                ],
                "requirements": [
                    "保留用户当前目标",
                    "保留已确认参数",
                    "保留已完成动作",
                    "保留待补充问题",
                    "保留当前结论",
                    "保留仍可能影响后续回答的约束",
                    "不要包含 API Key",
                    "不要包含内部 Prompt",
                    "不要展开全量工具原始响应",
                ],
                "target_tokens": target_tokens,
            },
            ensure_ascii=False,
            indent=2,
        )
        return await self.llm_client.chat_text(
            system_prompt,
            user_prompt,
            max_tokens=max(target_tokens * 2, 600),
        )
