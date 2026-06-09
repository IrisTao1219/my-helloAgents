from pathlib import Path

def load_prompt(path: str) -> str:
    return Path(__file__).parent.joinpath(path).read_text(encoding="utf-8")

def re_group(pattern: str, text: str, group_index: int = 1) -> str:
    import re
    match = re.search(pattern, text)
    return match.group(group_index) if match else ""