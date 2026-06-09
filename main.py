import os
import re

from api_llm import MyOpenAIClient
from tool import available_tools
from utils import load_prompt, re_group

def chat():
    llm = MyOpenAIClient()

    user_prompt = "请告诉我北京当前的天气，并推荐一个适合这个天气的旅游景点。"
    prompt_history = [f"用户请求: {user_prompt}"]

    print(f"用户请求: {user_prompt}\n" + "=" * 50)

    for i in range(3):
        print(f"\n第 {i+1} 轮对话:")

        full_prompt = "\n".join(prompt_history)

        SYSTEMP_PROMPT = load_prompt("./prompt_system.md")
        llm_output = llm.generate(full_prompt, system_prompt=SYSTEMP_PROMPT)

        match = re.search(r"(Thought:.*?Action:.*?)(?=\n\s*(?:Thought:|Action:|Observation:)|\Z)", llm_output, re.DOTALL)
        if match:
            truncated = match.group(1).strip()

            if truncated  != llm_output.strip():
                print("⚠️ 输出被截断了，可能缺少 Observation 或后续内容。")
                
        print(f"LLM 输出:\n{llm_output}\n" + "-" * 50)
        prompt_history.append(llm_output)

        action_match = re.search(r"Action: (.*)", llm_output, re.DOTALL)
        if not action_match:
            observation = "错误: 未能解析到 Action 字段。请确保你的回复严格遵循 'Thought: ... Action: ...' 的格式。"
            observation_str = f"Observation: {observation}"
            print(f"⚠️ {observation}\n", "-" * 50)
            prompt_history.append(observation_str)
            continue
        action_str = action_match.group(1).strip()

        if action_str.startswith("Finish"):
            final_answer = re_group(r"Finish\[(.*)\]", action_str)
            print(f"✅ 任务完成，最终答案: {final_answer}\n")
            break
        
        tool_name = re_group(r"(\w+)\(", action_str)
        args_str = re_group(r"\((.*)\)", action_str)
        kwargs = dict(re.findall(r'(\w+)="([^"]*)"', args_str))

        if tool_name in available_tools:
            tool_func = available_tools[tool_name]
            observation = tool_func(**kwargs)
        else:
            observation = f"错误: 未找到工具 '{tool_name}'。请检查工具名称是否正确，并确保它已在 available_tools 中注册。"


        observation_str = f"Observation: {observation}"
        print(f"{observation_str}\n" + "=" * 50)
        prompt_history.append(observation_str)
        
if __name__ == "__main__":
    chat()