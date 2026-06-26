from tortoise import fields
from tortoise.models import Model


class SessionState(Model):
    """
    会话状态快照。

    Attributes:
        id (str): 主键。
        session_id (str): 会话 ID。
        user_id (str): 用户 ID。
        agent_id (str): Agent ID。
        title (str): 会话标题。
        state (str): 当前状态。
        loop_count (int): 最近一次 Loop 次数。
        pending_action (dict | None): 待继续动作。
        missing_params (list): 缺失参数。
        conversation_summary (str): 第一阶段轻量会话摘要。
        deleted_at (datetime | None): 软删除时间。
        created_at (datetime): 创建时间。
        updated_at (datetime): 更新时间。
    """

    id = fields.CharField(max_length=64, pk=True)
    session_id = fields.CharField(max_length=64, index=True)
    user_id = fields.CharField(max_length=128, index=True)
    agent_id = fields.CharField(max_length=128, index=True)
    title = fields.CharField(max_length=128, default="新会话")
    state = fields.CharField(max_length=32)
    loop_count = fields.IntField(default=0)
    pending_action = fields.JSONField(null=True)
    missing_params = fields.JSONField(default=list)
    conversation_summary = fields.TextField(default="")
    deleted_at = fields.DatetimeField(null=True, index=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "session_state"
        unique_together = (("user_id", "agent_id", "session_id"),)
