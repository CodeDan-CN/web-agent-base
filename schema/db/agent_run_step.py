from tortoise import fields
from tortoise.models import Model


class AgentRunStep(Model):
    """
    Agent Loop 单步追加记录。

    Attributes:
        id (str): 主键。
        run_id (str): 运行 ID。
        session_id (str): 会话 ID。
        step_index (int): 步骤序号。
        state_before (str): 执行前状态。
        action (str): 执行动作。
        action_detail (dict): 动作详情。
        execution_result (dict | None): 动作执行结果。
        harness_feedback (dict | None): Harness 反馈。
        state_after (str): 执行后状态。
        created_at (datetime): 创建时间。
    """

    id = fields.CharField(max_length=64, pk=True)
    run_id = fields.CharField(max_length=64, index=True)
    session_id = fields.CharField(max_length=64, index=True)
    step_index = fields.IntField()
    state_before = fields.CharField(max_length=32)
    action = fields.CharField(max_length=32)
    action_detail = fields.JSONField(default=dict)
    execution_result = fields.JSONField(null=True)
    harness_feedback = fields.JSONField(null=True)
    state_after = fields.CharField(max_length=32)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "agent_run_step"
