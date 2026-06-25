from tortoise import fields
from tortoise.models import Model


class ToolCall(Model):
    """
    mock executor 调用记录。

    Attributes:
        id (str): 主键。
        run_id (str): 运行 ID。
        session_id (str): 会话 ID。
        action (str): call_skill 或 call_agent。
        tool_name (str): mock executor 名称。
        input_payload (dict): 输入参数。
        output_payload (dict): 输出结果。
        status (str): 执行状态。
        created_at (datetime): 创建时间。
    """

    id = fields.CharField(max_length=64, pk=True)
    run_id = fields.CharField(max_length=64, index=True)
    session_id = fields.CharField(max_length=64, index=True)
    action = fields.CharField(max_length=32)
    tool_name = fields.CharField(max_length=128)
    input_payload = fields.JSONField(default=dict)
    output_payload = fields.JSONField(default=dict)
    status = fields.CharField(max_length=32)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "tool_call"
