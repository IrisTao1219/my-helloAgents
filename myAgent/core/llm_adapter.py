import asyncio
import os
import time
from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, Iterator, List, Optional

from dotenv import load_dotenv

from .llm_response import LLMResponse, StreamStats

# 加载环境变量
load_dotenv()

MODEL_ID = os.getenv("LLM_MODEL_ID", "")
BASE_URL = os.getenv("LLM_BASE_URL")
API_KEY = os.getenv("LLM_API_KEY")
TIMEOUT = int(os.getenv("LLM_TIMEOUT", 60))


class BaseLLMAdapter(ABC):
    def __init__(self, api_key: str, base_url: Optional[str], model: str, timeout: int):
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout
        self.model = model
        self._client = None

    @abstractmethod
    def create_client(self):
        """创建客户端实例"""
        pass

    def create_async_client(self):
        """创建异步客户端实例"""
        pass

    @abstractmethod
    def invoke(self, messages: List[Dict], **kwargs) -> LLMResponse:
        """非流式调用"""
        pass

    @abstractmethod
    def stream_invoke(self, messages: List[Dict], **kwargs) -> Iterator[str]:
        """流式调用"""
        pass

    async def astream_invoke(
        self, messages: List[Dict], **kwargs
    ) -> AsyncIterator[str]:
        """异步流式调用"""
        queue = asyncio.Queue()
        loop = asyncio.get_event_loop()

        def _stream_to_queue():
            try:
                for chunk in self.stream_invoke(messages, **kwargs):
                    asyncio.run_coroutine_threadsafe(queue.put(chunk), loop)
            except Exception as e:
                asyncio.run_coroutine_threadsafe(queue.put(e), loop)
            finally:
                asyncio.run_coroutine_threadsafe(queue.put(None), loop)

        loop.run_in_executor(None, _stream_to_queue)

        while True:
            chunk = await queue.get()
            if chunk is None:
                break
            if isinstance(chunk, Exception):
                raise chunk
            yield chunk

    # @abstractmethod
    def invoke_with_tools(self, messages: List[Dict], **kwargs) -> Any:
        """调用包含工具的模型"""
        pass


class OpenAIAdapter(BaseLLMAdapter):
    def create_client(self) -> Any:
        """创建客户端实例"""
        from openai import OpenAI

        return OpenAI(
            api_key=self.api_key, base_url=self.base_url, timeout=self.timeout
        )

    def create_async_client(self) -> Any:
        """创建异步客户端实例"""
        from openai import AsyncOpenAI

        return AsyncOpenAI(
            api_key=self.api_key, base_url=self.base_url, timeout=self.timeout
        )

    def invoke(self, messages: List[Dict], **kwargs) -> LLMResponse:
        """非流式调用"""
        if not self._client:
            self._client = self.create_client()

        start_time = time.time()

        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=False,
                **kwargs,
            )

            latency_ms = int(time.time() - start_time * 1000)

            choice = response.choices[0]
            content = choice.message.content or ""
            reasoning_content = None

            if hasattr(choice.message, "reasoning_content"):
                reasoning_content = choice.message.reasoning_content
            elif hasattr(choice, "reasoning_content"):
                reasoning_content = choice.reasoning_content

            usage = {}
            if hasattr(response, "usage") and response.usage:
                usage = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                }

            return LLMResponse(
                content=content,
                model=self.model,
                usage=usage,
                latency_ms=latency_ms,
                reasoning_content=reasoning_content,
            )

        except Exception as e:
            raise Exception(f"OpenAI API调用失败: {str(e)}")

    def stream_invoke(self, messages: List[Dict], **kwargs) -> Iterator[str]:
        """流式调用"""
        if not self._client:
            self._client = self.create_client()

        start_time = time.time()

        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=True,
                **kwargs,
            )

            usage = {}

            for chunk in response:
                if chunk.choices:
                    delta = chunk.choices[0].delta
                    content = getattr(delta, "content", "") or ""
                    if content:
                        yield content

                    if hasattr(chunk, "usage") and chunk.usage:
                        usage = {
                            "prompt_tokens": chunk.usage.prompt_tokens,
                            "completion_tokens": chunk.usage.completion_tokens,
                            "total_tokens": chunk.usage.total_tokens,
                        }

            latency_ms = int((time.time() - start_time) * 1000)

            self.last_stats = StreamStats(
                model=self.model, usage=usage, latency_ms=latency_ms
            )

        except Exception as e:
            raise Exception(f"OpenAI API流式调用失败: {str(e)}")

def create_adapter(
    api_key: str, base_url: Optional[str], timeout: int, model: str
) -> BaseLLMAdapter:
    """
    根据base_url自动选择适配器

    检测逻辑：
    - anthropic.com -> AnthropicAdapter
    - googleapis.com 或 generativelanguage -> GeminiAdapter
    - 其他 -> OpenAIAdapter（默认）
    """
    if base_url:
        base_url_lower = base_url.lower()

    # if "anthropic.com" in base_url_lower:
    #     return AnthropicAdapter(api_key, base_url, timeout, model)

    # if "googleapis.com" in base_url_lower or "generativelanguage" in base_url_lower:
    #     return GeminiAdapter(api_key, base_url, timeout, model)

    # 默认使用OpenAI适配器（兼容所有OpenAI格式接口）
    return OpenAIAdapter(api_key, base_url, model, timeout)
