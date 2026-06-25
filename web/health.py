from fastapi import APIRouter

health_router = APIRouter()


@health_router.get("/health")
async def health() -> dict[str, str]:
    """
    健康检查接口。

    Returns:
        dict[str, str]: 健康状态。
    """
    return {"status": "ok"}
