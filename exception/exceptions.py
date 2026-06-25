class BizException(Exception):
    """
    业务异常。

    Attributes:
        code (int): HTTP 状态码。
        message (str): 错误信息。
    """

    def __init__(self, code: int, message: str) -> None:
        """
        初始化业务异常。

        Args:
            code (int): HTTP 状态码。
            message (str): 错误信息。
        """
        self.code = code
        self.message = message
        super().__init__(message)
