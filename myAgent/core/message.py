from datetime import datetime
from typing import Dict, Literal, Optional

from pydantic import BaseModel

MessageRole = Literal["user", "assistant", "system", "tool", "summary"]

class Message(BaseModel):
    role: str
    content: str
    timestamp: datetime
    metadata: Optional[Dict[str, str]] = None

    def __init__(self, content: str, role: str, timestamp: Optional[datetime] = None, ):
        super().__init__(
        role = role,
        content = content,
        timestamp = timestamp or datetime.now(),
        metadata = {})

    def to_dict(self) -> Dict[str, str]:
        return {
            "role": self.role,
            "content": self.content
        }

    def __str__(self) -> str:
        return f"{self.role}: {self.content}"
