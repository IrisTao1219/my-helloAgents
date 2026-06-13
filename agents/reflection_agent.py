from utils import load_prompt


class Memory:
    def __init__(self):
        self.records = []

    def add_record(self, record_type: str, content: str):
        record = {"type": record_type, "content": content}
        self.records.append(record)
        print(f"📝 记忆已更新，新增一条 '{record_type}' 记录。")

    def get_trajectory(self) -> str:
        trajectory_parts = []
        for record in self.records:
            if record["type"] == "execution":
                trajectory_parts.append(
                    f"--- 上一轮尝试 (代码) ---\n{record['content']}"
                )
            elif record["type"] == "reflection":
                trajectory_parts.append(f"--- 评审员反馈 ---\n{record['content']}")

        return "\n\n".join(trajectory_parts)

    def get_last_execution(self):
        for record in reversed(self.records):
            if record["type"] == "execution":
                return record["content"]
        return None


class ReflectionAgent:
    def __init__(self, llm_client, max_iterations=3):
        self.llm_client = llm_client
        self.max_iterations = max_iterations
        self.memory = Memory()

    def _get_llm_response(self, prompt: str) -> str:
        messages = [{"role": "user", "content": prompt}]
        response_text = self.llm_client.think(messages)
        return response_text

    def run(self, task: str):
        print(f"\n--- 开始处理任务 ---\n任务: {task}")

        print("\n--- 正在进行初始尝试 ---")
        initial_prompt = load_prompt(
            "prompts/reflection/execution_prompt_template.md"
        ).format(task=task)
        initial_code = self._get_llm_response(initial_prompt)
        print(initial_code)
        self.memory.add_record("execution", initial_code)

        for i in range(self.max_iterations):
            print(f"\n--- round {i + 1}/{self.max_iterations} ---")

            print("\n-> 正在进行反思...")
            last_code = self.memory.get_last_execution()
            reflect_prompt = load_prompt(
                "prompts/reflection/reflection_prompt_template.md"
            ).format(task=task, code=last_code)
            feedback = self._get_llm_response(reflect_prompt)
            self.memory.add_record("reflection", feedback)

            if "无需改进" in feedback:
                print("\n✅ 反思认为代码已无需改进，任务完成。")
                break

            print("\n-> 正在进行优化...")
            refine_prompt = load_prompt(
                "prompts/reflection/refinement_prompt_template.md"
            ).format(task=task, last_code_attempt=last_code, feedback=feedback)

            refined_code = self._get_llm_response(refine_prompt)
            self.memory.add_record("execution", refined_code)

        final_code = self.memory.get_last_execution()
        print(f"\n--- 任务完成 ---\n最终生成的代码:\n```python\n{final_code}\n```")
        return final_code