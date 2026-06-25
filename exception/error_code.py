from enum import Enum

from exception.exceptions import BizException


class BizErrorCode(Enum):
    """
    业务错误码定义。

    Attributes:
        value (tuple[int, str]): 错误码和默认文案。
    """

    VALIDATION_ERROR = (400, "参数错误")
    AGENT_LOAD_ERROR = (500, "Agent 加载失败")
    ACTION_PARSE_ERROR = (500, "Action 解析失败")
    ACTION_EXECUTE_ERROR = (500, "Action 执行失败")
    HARNESS_ERROR = (500, "Harness 评估失败")
    STATE_ERROR = (500, "状态流转失败")
    NOT_FOUND = (404, "资源不存在")
    INTERNAL_ERROR = (500, "服务内部错误")

    def exception(self, detail: str | None = None) -> BizException:
        """
        构建业务异常。

        Args:
            detail (str | None): 动态错误文案。

        Returns:
            BizException: 业务异常。
        """
        code, message = self.value
        return BizException(code=code, message=detail or message)
