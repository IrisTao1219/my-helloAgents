import asyncio

from agents import MyAgent
from core import MyLLM

from myAgent.tools.my_calculator_tool import my_calculate
from myAgent.tools.registry import ToolRegistry


def myMain():
    llm = MyLLM()

    messages = [{"role": "user", "content": "你好，请介绍一下你自己。"}]

    response = llm.stream_invoke(messages)

    print("ModelScope Response:")
    for chunk in response:
        # print(chunk, end="", flush=True)
        pass
    print()


def local():
    llm = MyLLM(model="Qwen2.5:0.5b", base_url="http://localhost:11434/v1")

    messages = [{"role": "user", "content": "你好，请介绍一下你自己。"}]

    response = llm.stream_invoke(messages)

    print("ModelScope Response:")
    for chunk in response:
        # print(chunk, end="", flush=True)
        pass
    print()


def test_simple_agent():
    llm = MyLLM(model="Qwen2.5:0.5b", base_url="http://localhost:11434/v1")

    agent = MyAgent(
        name="TestAgent",
        llm=llm,
        system_prompt="你是一个专业的助手，能够回答用户的问题。",
    )

    for chunk in agent.stream_run("你好，请介绍一下你自己。"):
        pass


async def test_func_registry():
    llm = MyLLM()

    registry = ToolRegistry()

    registry.register_function(
        name="my_calculator",
        description="简单的数学计算工具，支持基本运算(+,-,*,/)和sqrt函数",
        func=my_calculate,
    )

    calc_result = await registry.execute_tool("my_calculator", "sqrt(16) + 2 * 3")

    print(f"计算结果: {calc_result}")

    user_question = "请帮我计算 sqrt(16) + 2 * 3"
    messages = [
        {
            "role": "user",
            "content": f"计算结果是 {calc_result}，请用自然语言回答用户的问题：{user_question}",
        }
    ]

    response = llm.stream_invoke(messages)

    print("\n🎯 LLM Response:")
    for chunk in response:
        # print(chunk, end="", flush=True)
        pass
    print()


if __name__ == "__main__":
    # myMain()
    # local()
    # test_simple_agent()

    asyncio.run(test_func_registry())
