import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    """
    应用运行配置。

    Attributes:
        database_url (str): 原始数据库连接串。
        tortoise_database_url (str): Tortoise ORM 可识别的数据库连接串。
        model_provider (str): 模型服务类型。
        model_base_url (str): OpenAI-compatible 模型服务地址。
        model_api_key (str): 模型服务密钥。
        model_name (str): 模型名称。
        model_disable_reasoning (bool): 是否关闭模型推理输出。
        max_loop_steps (int): 单次 Agent Run 最大 Loop 步数。
        cors_origins (list[str]): 允许跨域访问的来源。
        skill_api_timeout_ms (int): API Skill 超时时间。
        event_summary_direct_max_turns (int): 事件摘要直接汇总最大轮数。
        event_summary_direct_max_chars (int): 事件摘要直接汇总最大字符数。
        event_summary_target_chars (int): 事件摘要模型总结目标字符数。
    """

    database_url: str
    tortoise_database_url: str
    model_provider: str
    model_base_url: str
    model_api_key: str
    model_name: str
    model_disable_reasoning: bool
    max_loop_steps: int
    cors_origins: list[str]
    skill_api_timeout_ms: int
    event_summary_direct_max_turns: int
    event_summary_direct_max_chars: int
    event_summary_target_chars: int


def _to_tortoise_database_url(database_url: str) -> str:
    """
    将常见 PostgreSQL URL 转换为 Tortoise ORM 可识别格式。

    Args:
        database_url (str): 原始数据库连接串。

    Returns:
        str: Tortoise ORM 可识别连接串。
    """
    if database_url.startswith("postgresql+psycopg://"):
        return database_url.replace("postgresql+psycopg://", "postgres://", 1)
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgres://", 1)
    return database_url


@lru_cache
def get_settings() -> Settings:
    """
    加载应用配置。

    Returns:
        Settings: 应用配置对象。
    """
    load_dotenv()
    database_url = os.getenv("DATABASE_URL", "")
    model_api_key = os.getenv("MODEL_API_KEY", "")
    return Settings(
        database_url=database_url,
        tortoise_database_url=_to_tortoise_database_url(database_url),
        model_provider=os.getenv("MODEL_PROVIDER", "openai_compatible"),
        model_base_url=os.getenv("MODEL_BASE_URL", ""),
        model_api_key=model_api_key,
        model_name=os.getenv("MODEL_NAME", ""),
        model_disable_reasoning=os.getenv("MODEL_DISABLE_REASONING", "true").lower()
        == "true",
        max_loop_steps=int(os.getenv("MAX_LOOP_STEPS", "5")),
        cors_origins=[
            item.strip()
            for item in os.getenv(
                "CORS_ORIGINS",
                "http://127.0.0.1:5173,http://localhost:5173",
            ).split(",")
            if item.strip()
        ],
        skill_api_timeout_ms=int(os.getenv("SKILL_API_TIMEOUT_MS", "10000")),
        event_summary_direct_max_turns=int(
            os.getenv("EVENT_SUMMARY_DIRECT_MAX_TURNS", "6")
        ),
        event_summary_direct_max_chars=int(
            os.getenv("EVENT_SUMMARY_DIRECT_MAX_CHARS", "1200")
        ),
        event_summary_target_chars=int(
            os.getenv("EVENT_SUMMARY_TARGET_CHARS", "100")
        ),
    )
