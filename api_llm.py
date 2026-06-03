from openai import OpenAI

class MyOpenAIClient:
    def __init__(self, model: str, api_key, base_url=None, timeout=60):
        self.client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout)
        self.model = model
    
    def generate(self, prompt: str, system_prompt: str) -> str:
        """生成文本响应，兼容OpenAI接口"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                stream=False
            )
            
            answer = response.choices[0].message.content
            # ensure we always return a str (avoid None)
            if answer is None:
                answer = ""
            
            print("大语言模型响应成功。")
            return answer
        except Exception as e:
            return f"LLM调用失败: {str(e)}"