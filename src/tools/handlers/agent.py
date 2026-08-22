from typing import Any, Dict, Optional
from ..registry import Tool, registry


def skill(skill: str, args: Optional[Dict[str, Any]] = None) -> str:
    if skill == "known":
        return f"Loaded skill {skill}"
    raise ValueError(f"Unknown skill: {skill}")


TOOLS = [Tool("skill", "Agent", "LOW", "Loads workflow skill", {"required": ["skill"], "properties": {"skill": {"type": "string"}}}, skill)]

for tool in TOOLS:
    registry.register(tool)
