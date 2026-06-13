
from agents.reflection_agent import ReflectionAgent
from api_llm import MyOpenAIClient


llm_client = MyOpenAIClient()

agent = ReflectionAgent(llm_client)
question = "编写一个Python函数，找出1到n之间所有的素数 (prime numbers)"
agent.run(question)