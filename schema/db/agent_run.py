from tortoise import fields
from tortoise.models import Model


class AgentRun(Model):
    """
    单次 Agent 运行记录。

    Attributes:
        id (str): 运行 ID。
        request_id (str): 请求 ID。
        session_id (str): 会话 ID。
        user_id (str): 用户 ID。
        agent_id (str): Agent ID。
        user_message (str): 用户输入。
        initial_state (str): 初始状态。
        final_state (str | None): 最终状态。
        final_answer (str | None): 最终回答。
        error_message (str | None): 错误信息。
        created_at (datetime): 创建时间。
        updated_at (datetime): 更新时间。
    """

    id = fields.CharField(max_length=64, pk=True)
    request_id = fields.CharField(max_length=128, index=True)
    session_id = fields.CharField(max_length=64, index=True)
    user_id = fields.CharField(max_length=128, index=True)
    agent_id = fields.CharField(max_length=128, index=True)
    user_message = fields.TextField()
    initial_state = fields.CharField(max_length=32)
    final_state = fields.CharField(max_length=32, null=True)
    final_answer = fields.TextField(null=True)
    error_message = fields.TextField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "agent_run"
