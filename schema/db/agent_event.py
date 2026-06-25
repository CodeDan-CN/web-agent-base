from tortoise import fields
from tortoise.models import Model


class AgentEvent(Model):
    """
    Agent 事件。

    Attributes:
        event_id (str): 事件 ID。
        user_id (str): 用户 ID。
        session_id (str): 会话 ID。
        root_agent_id (str): 创建事件的主 Agent ID。
        status (str): 事件状态。
        title (str | None): 事件标题。
        parent_event_id (str | None): 父事件 ID。
        event_chain_id (str | None): 事件链 ID。
        metadata (dict | None): 扩展信息。
        created_at (datetime): 创建时间。
        updated_at (datetime): 更新时间。
        completed_at (datetime | None): 完成时间。
    """

    event_id = fields.CharField(max_length=128, pk=True)
    user_id = fields.CharField(max_length=128, index=True)
    session_id = fields.CharField(max_length=64, index=True)
    root_agent_id = fields.CharField(max_length=128, index=True)
    status = fields.CharField(max_length=32, index=True)
    title = fields.CharField(max_length=256, null=True)
    parent_event_id = fields.CharField(max_length=128, null=True)
    event_chain_id = fields.CharField(max_length=128, null=True)
    metadata = fields.JSONField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    completed_at = fields.DatetimeField(null=True)

    class Meta:
        table = "agent_event"


class AgentEventRun(Model):
    """
    Agent 事件与 run 的关联。

    Attributes:
        id (str): 主键。
        event_id (str): 事件 ID。
        run_id (str): run ID。
        user_id (str): 用户 ID。
        agent_id (str): Agent ID。
        session_id (str): 会话 ID。
        created_at (datetime): 创建时间。
    """

    id = fields.CharField(max_length=64, pk=True)
    event_id = fields.CharField(max_length=128, index=True)
    run_id = fields.CharField(max_length=64, unique=True)
    user_id = fields.CharField(max_length=128, index=True)
    agent_id = fields.CharField(max_length=128, index=True)
    session_id = fields.CharField(max_length=64, index=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "agent_event_run"


class AgentEventContext(Model):
    """
    单个 Agent 在某个事件下的上下文摘要。

    Attributes:
        id (str): 主键。
        event_id (str): 事件 ID。
        user_id (str): 用户 ID。
        agent_id (str): Agent ID。
        summary (str): 事件摘要。
        turn_count (int): 汇总 run 数。
        char_count (int): 汇总字符数。
        summarize_mode (str): direct 或 llm。
        metadata (dict | None): 扩展信息。
        created_at (datetime): 创建时间。
        updated_at (datetime): 更新时间。
    """

    id = fields.CharField(max_length=64, pk=True)
    event_id = fields.CharField(max_length=128, index=True)
    user_id = fields.CharField(max_length=128, index=True)
    agent_id = fields.CharField(max_length=128, index=True)
    summary = fields.TextField(default="")
    turn_count = fields.IntField(default=0)
    char_count = fields.IntField(default=0)
    summarize_mode = fields.CharField(max_length=32, default="direct")
    metadata = fields.JSONField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "agent_event_context"
        unique_together = (("event_id", "agent_id"),)
