class Memory:
    def __init__(self):
        self.records = []
        
    def add_record(self, record_type: str, content: str):
        record = {"type": record_type, "content": content}
        self.records.append(record)
        print(f"🧠 记忆已更新，添加了记录：{record}")
        
    def get_trajectory(self) -> str:
        trajectory_parts = []
        return "\n".join(trajectory_parts)
        