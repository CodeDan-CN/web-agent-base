from contextlib import asynccontextmanager
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from tortoise import Tortoise
import uvicorn

from exception.handler import register_exception_handlers
from utils.config import get_settings
from web.router import api_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    """
    FastAPI 生命周期管理。

    Args:
        _ (FastAPI): FastAPI 应用。
    """
    settings = get_settings()
    await Tortoise.init(
        db_url=settings.tortoise_database_url,
        modules={"models": ["schema.db.models"]},
    )
    await Tortoise.generate_schemas(safe=True)
    yield
    await Tortoise.close_connections()


app = FastAPI(title="Agent Base", lifespan=lifespan)
register_exception_handlers(app)
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router)


def main() -> None:
    """
    直接运行 app.py 时启动服务。
    """
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8003"))
    uvicorn.run("app:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
