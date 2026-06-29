from exception.exceptions import BizException


def build_failure_message(
    reason: str,
    input_issue: bool,
    next_step: str,
    attempted_action: str = "继续处理你的请求",
) -> str:
    """
    构造面向用户的失败说明。

    Args:
        reason (str): 失败原因。
        input_issue (bool): 是否更像输入或信息不足问题。
        next_step (str): 下一步建议。
        attempted_action (str): 本次尝试做的动作。

    Returns:
        str: 面向用户的失败说明。
    """
    normalized_reason = reason.strip() or "当前步骤没有成功完成。"
    normalized_next_step = next_step.strip() or "请根据上面的原因调整后再试一次。"
    input_line = (
        "这更像是当前信息还不够完整，未必是你的操作有问题。"
        if input_issue
        else "这不是你的输入问题，更像是 Agent 运行环境、依赖服务或能力调用侧的问题。"
    )
    return (
        f"我刚刚尝试{attempted_action}，但这一步失败了。\n\n"
        f"当前原因是：{normalized_reason}\n\n"
        f"{input_line}\n"
        f"{normalized_next_step}"
    )


def build_exception_failure_message(exc: Exception) -> str:
    """
    将异常转换成面向用户的失败说明。

    Args:
        exc (Exception): 运行时异常。

    Returns:
        str: 面向用户的失败说明。
    """
    reason = exception_reason(exc)
    input_issue = isinstance(exc, BizException) and exc.code == 400
    next_step = infer_next_step(reason, input_issue=input_issue)
    return build_failure_message(
        reason=reason,
        input_issue=input_issue,
        next_step=next_step,
    )


def exception_reason(exc: Exception) -> str:
    """
    提取异常的可读原因。

    Args:
        exc (Exception): 运行时异常。

    Returns:
        str: 原因说明。
    """
    if isinstance(exc, BizException):
        return exc.message
    return "Agent 服务在运行过程中出现了未预期的内部错误。"


def infer_next_step(
    reason: str,
    input_issue: bool,
    suggested_question: str | None = None,
) -> str:
    """
    根据失败原因推导下一步建议。

    Args:
        reason (str): 失败原因。
        input_issue (bool): 是否更像输入问题。
        suggested_question (str | None): 建议追问。

    Returns:
        str: 下一步建议。
    """
    if input_issue:
        if suggested_question:
            return f"请先补充或确认这条信息：{suggested_question}"
        return "请根据上面的原因补充更具体的信息后再试一次。"
    if "缺少环境变量:" in reason:
        env_name = reason.split("缺少环境变量:", 1)[1].strip()
        return f"补齐环境变量 `{env_name}` 并重启服务后，再重试这一步。"
    if "模型配置不完整" in reason:
        return "补齐模型相关环境变量并重启服务后，再重新发起请求。"
    if any(token in reason for token in ["后端接口返回失败", "接口调用失败", "连接失败", "Connect call failed"]):
        return "请检查后端服务状态、网络连通性和接口配置，确认恢复后再重试。"
    if any(token in reason for token in ["超时", "timeout", "Timeout"]):
        return "可以稍后重试；如果频繁出现，请检查依赖服务响应时间和网络情况。"
    return "请检查服务配置或日志，确认原因处理完成后再重试。"
