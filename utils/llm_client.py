from openai import AsyncOpenAI

from exception.error_code import BizErrorCode
from utils.config import get_settings


class LLMClient:
    """
    OpenAI-compatible 模型调用客户端。

    Attributes:
        client (AsyncOpenAI): OpenAI 异步客户端。
        model_name (str): 模型名称。
    """

    def __init__(self) -> None:
        """
        初始化 LLMClient。
        """
        settings = get_settings()
        if not settings.model_base_url or not settings.model_api_key or not settings.model_name:
            raise BizErrorCode.INTERNAL_ERROR.exception("模型配置不完整")
        self.client = AsyncOpenAI(
            api_key=settings.model_api_key,
            base_url=settings.model_base_url,
        )
        self.model_name = settings.model_name
        self.disable_reasoning = settings.model_disable_reasoning

    async def chat_text(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 3000,
    ) -> str:
        """
        调用模型并返回文本。

        Args:
            system_prompt (str): system prompt。
            user_prompt (str): user prompt。
            temperature (float): 采样温度。
            max_tokens (int): 最大输出 token 数。

        Returns:
            str: 模型输出文本。
        """
        request_kwargs = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if self.disable_reasoning:
            request_kwargs["extra_body"] = {"thinking": {"type": "disabled"}}
        response = await self.client.chat.completions.create(**request_kwargs)
        content = response.choices[0].message.content
        if not content:
            raise BizErrorCode.INTERNAL_ERROR.exception("模型返回为空")
        return content

    async def chat_text_stream(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 3000,
    ):
        """
        流式调用模型并逐段返回文本。

        Args:
            system_prompt (str): system prompt。
            user_prompt (str): user prompt。
            temperature (float): 采样温度。
            max_tokens (int): 最大输出 token 数。

        Yields:
            str: 模型输出片段。
        """
        request_kwargs = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        if self.disable_reasoning:
            request_kwargs["extra_body"] = {"thinking": {"type": "disabled"}}
        stream = await self.client.chat.completions.create(**request_kwargs)
        async for chunk in stream:
            if not chunk.choices:
                continue
            content = chunk.choices[0].delta.content
            if content:
                yield content
