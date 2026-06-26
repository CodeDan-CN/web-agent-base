from tortoise import fields
from tortoise.models import Model


class ConversationTurn(Model):
    """
    用户可见的一轮 Agent 对话。

    Attributes:
        id (str): 主键。
        turn_id (str): 稳定 Turn ID。
        run_id (str): 对应 AgentRun ID。
        session_id (str): 会话 ID。
        user_id (str): 用户 ID。
        agent_id (str): Agent ID。
        event_id (str | None): 事件 ID。
        user_message (str): 用户输入。
        assistant_message (str): Agent 最终回答或追问。
        final_state (str): 当前 run 最终状态。
        token_estimate (int): 近似 token 估算。
        summary_batch_id (str | None): 被压缩批次 ID。
        summarized_at (datetime | None): 被压缩时间。
        created_at (datetime): 创建时间。
        updated_at (datetime): 更新时间。
    """

    id = fields.CharField(max_length=64, pk=True)
    turn_id = fields.CharField(max_length=64, unique=True)
    run_id = fields.CharField(max_length=64, unique=True)
    session_id = fields.CharField(max_length=64, index=True)
    user_id = fields.CharField(max_length=128, index=True)
    agent_id = fields.CharField(max_length=128, index=True)
    event_id = fields.CharField(max_length=64, null=True, index=True)
    user_message = fields.TextField()
    assistant_message = fields.TextField()
    final_state = fields.CharField(max_length=32)
    token_estimate = fields.IntField(default=0)
    summary_batch_id = fields.CharField(max_length=64, null=True, index=True)
    summarized_at = fields.DatetimeField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "conversation_turn"
        unique_together = (("user_id", "agent_id", "session_id", "turn_id"),)
