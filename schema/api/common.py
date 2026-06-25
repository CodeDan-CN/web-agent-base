from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class BaseResponse(BaseModel, Generic[T]):
    """
    统一接口响应。

    Attributes:
        code (int): 响应码。
        msg (str): 响应信息。
        data (T | None): 响应数据。
    """

    code: int = 200
    msg: str = "success"
    data: T | None = None
