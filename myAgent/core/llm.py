import os
from typing import Dict, Iterator, List, Optional

from dotenv import load_dotenv

from myAgent.core.llm_response import LLMResponse

from .llm_adapter import BaseLLMAdapter, create_adapter

# 加载环境变量
load_dotenv()


class MyLLM:
    def __init__(
        self,
        provider: str = "openai",
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        timeout: Optional[int] = None,
        **kwargs,
    ):
        # 加载配置
        self.model = model or os.getenv("LLM_MODEL_ID")
        self.api_key = api_key or os.getenv("LLM_API_KEY")
        self.base_url = base_url or os.getenv("LLM_BASE_URL")
        self.timeout = timeout or int(os.getenv("LLM_TIMEOUT", "60"))
        self.provider = provider or self._auto_detect_provider(api_key, base_url)

        self.temperature = temperature
        self.max_tokens = max_tokens
        self.kwargs = kwargs

        # 验证必要参数
        if not self.model:
            raise Exception("必须提供模型名称（model参数或LLM_MODEL_ID环境变量）")
        if not self.api_key:
            raise Exception("必须提供API密钥（api_key参数或LLM_API_KEY环境变量）")
        if not self.base_url:
            raise Exception("必须提供服务地址（base_url参数或LLM_BASE_URL环境变量）")

        # 创建适配器（自动检测）
        self._adapter: BaseLLMAdapter = create_adapter(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout,
            model=self.model,
        )

    def think(
        self, messages: List[Dict[str, str]], temperature: Optional[float] = None
    ) -> Iterator[str]:
        """
        调用大语言模型进行思考，并返回流式响应。
        这是主要的调用方法，默认使用流式响应以获得更好的用户体验。

        Args:
            messages: 消息列表
            temperature: 温度参数，如果未提供则使用初始化时的值

        Yields:
            str: 流式响应的文本片段
        """
        print(f"🧠 正在调用 {self.model} 模型...")

        # 准备参数
        kwargs = {
            "temperature": temperature if temperature is not None else self.temperature,
        }
        if self.max_tokens:
            kwargs["max_tokens"] = self.max_tokens

        try:
            print("✅ 大语言模型响应成功:")
            for chunk in self._adapter.stream_invoke(messages, **kwargs):
                print(chunk, end="", flush=True)
                yield chunk
            print()  # 换行

        except Exception as e:
            print(f"❌ 调用LLM API时发生错误: {e}")
            raise

    def invoke(self, messages: List[Dict], **kwargs) -> LLMResponse:
        """调用大语言模型"""
        # 准备参数
        call_kwargs = {
            "temperature": kwargs.pop("temperature", self.temperature),
        }
        if self.max_tokens:
            call_kwargs["max_tokens"] = self.max_tokens
        call_kwargs.update(kwargs)

        return self._adapter.invoke(messages, **call_kwargs)

    def stream_invoke(
        self, messages: List[Dict], temperature: Optional[float] = None
    ) -> Iterator[str]:
        """流式调用大语言模型"""
        # 准备参数
        kwargs = {
            "temperature": temperature if temperature is not None else self.temperature,
        }
        if self.max_tokens:
            kwargs["max_tokens"] = self.max_tokens

        for chunk in self._adapter.stream_invoke(messages, **kwargs):
            yield chunk

    def _auto_detect_provider(
        self, api_key: Optional[str], base_url: Optional[str]
    ) -> str:
        """
        自动检测LLM提供商
        """
        # 获取通用的环境变量
        actual_api_key = api_key or os.getenv("LLM_API_KEY")
        actual_base_url = base_url or os.getenv("LLM_BASE_URL")

        # 2. 根据 base_url 判断
        if actual_base_url:
            base_url_lower = actual_base_url.lower()
            if "api-inference.modelscope.cn" in base_url_lower:
                return "modelscope"
            if "open.bigmodel.cn" in base_url_lower:
                return "zhipu"
            if "localhost" in base_url_lower or "127.0.0.1" in base_url_lower:
                if ":11434" in base_url_lower:
                    return "ollama"
                if ":8000" in base_url_lower:
                    return "vllm"
                return "local"  # 其他本地端口

        # 3. 根据 API 密钥格式辅助判断
        if actual_api_key:
            if actual_api_key.startswith("ms-"):
                return "modelscope"
            # ... 其他密钥格式判断

        # 4. 默认返回 'auto'，使用通用配置
        return "auto"
