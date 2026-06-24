import os
from typing import Iterable, cast
from dotenv import load_dotenv
from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam

# 加载环境变量
load_dotenv()

MODEL_ID = os.getenv("LLM_MODEL_ID", "")
BASE_URL = os.getenv("LLM_BASE_URL")
API_KEY = os.getenv("LLM_API_KEY")
TIMEOUT = int(os.getenv("LLM_TIMEOUT", 60))


class MyOpenAIClient:
    def __init__(
        self,
        model: str | None = None,
        api_key= None,
        base_url= None,
        timeout= None,
    ):
        self.model = model or MODEL_ID
        apiKey = api_key or API_KEY
        baseUrl = base_url or BASE_URL
        timeout = timeout or TIMEOUT

        if not all([self.model, apiKey, baseUrl]):
            raise ValueError("模型ID、API密钥和服务地址必须被提供或在.env文件中定义。")

        # use the resolved apiKey and baseUrl variables when creating the client
        self.client = OpenAI(api_key=apiKey, base_url=baseUrl, timeout=timeout)

    def generate(self, prompt: str, system_prompt: str) -> str:
        """生成文本响应，兼容OpenAI接口"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                stream=False,
            )

            answer = response.choices[0].message.content
            # ensure we always return a str (avoid None)
            if answer is None:
                answer = ""

            print("大语言模型响应成功。")
            return answer
        except Exception as e:
            return f"LLM调用失败: {str(e)}"
        
    def think(self, messages:Iterable[ChatCompletionMessageParam], temperature: float = 0) -> str:
        """生成文本响应，兼容OpenAI接口"""
        
        print(f"🧠 正在调用 {self.model} 模型...")
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                stream=True,
            )
            
            collected_content = []
            for chunk in response:
                if not getattr(chunk, "choices", None):
                    continue
                # some SDK ChoiceDelta objects expose content as an attribute rather than via __getitem__
                delta = chunk.choices[0].delta
                content = getattr(delta, "content", "") or ""
                print(content, end="", flush=True)  # 实时输出增量内容
                collected_content.append(content)

            # join accumulated streamed pieces into the final answer
            answer = "".join(collected_content)

            print("\n✅ 大语言模型响应成功。\n")
            return answer

        except Exception as e:
            print(f"⚠️ LLM调用失败: {str(e)}")
            return ""

if __name__ == "__main__":
    try:
        llm = MyOpenAIClient()
        
        exampleMessages = [
            {"role": "system", "content": "You are a helpful assistant that writes Python code."},
            {"role": "user", "content": "写一个快速排序算法"}
        ]
        
        print("--- 调用LLM ---")
        response = llm.think(cast(Iterable[ChatCompletionMessageParam], exampleMessages))
        
        if response:
            print("\n--- 完整LLM响应开始 ---")
            print(response)
            print("\n--- 完整LLM响应结尾 ---")
            
    except Exception as e:
        print(f"初始化LLM客户端失败: {str(e)}")