import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from exception.exceptions import BizException
from schema.api.common import BaseResponse

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """
    注册全局异常处理器。

    Args:
        app (FastAPI): FastAPI 应用实例。
    """

    @app.exception_handler(BizException)
    async def handle_biz_exception(_: Request, exc: BizException) -> JSONResponse:
        """
        处理业务异常。

        Args:
            _ (Request): HTTP 请求。
            exc (BizException): 业务异常。

        Returns:
            JSONResponse: 统一错误响应。
        """
        response = BaseResponse(code=exc.code, msg=exc.message, data=None)
        return JSONResponse(status_code=exc.code, content=response.model_dump())

    @app.exception_handler(RequestValidationError)
    async def handle_validation_exception(
        _: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        """
        处理请求参数校验异常。

        Args:
            _ (Request): HTTP 请求。
            exc (RequestValidationError): 参数校验异常。

        Returns:
            JSONResponse: 统一错误响应。
        """
        response = BaseResponse(code=400, msg=str(exc.errors()), data=None)
        return JSONResponse(status_code=400, content=response.model_dump())

    @app.exception_handler(Exception)
    async def handle_unknown_exception(_: Request, exc: Exception) -> JSONResponse:
        """
        处理未捕获异常。

        Args:
            _ (Request): HTTP 请求。
            exc (Exception): 未捕获异常。

        Returns:
            JSONResponse: 统一错误响应。
        """
        logger.exception("Unhandled exception", exc_info=exc)
        response = BaseResponse(code=500, msg="服务内部错误", data=None)
        return JSONResponse(status_code=500, content=response.model_dump())
