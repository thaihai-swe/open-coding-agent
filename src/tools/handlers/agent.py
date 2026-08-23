from .. import skills
from ..registry import Tool, registry


def load_skill(name: str) -> str:
    return skills.load_skill_content(name)


TOOLS = [
    Tool(
        "load_skill",
        "Agent",
        "LOW",
        "Load the full content of a skill by name.",
        {"required": ["name"], "properties": {"name": {"type": "string"}}},
        load_skill,
    )
]

for tool in TOOLS:
    registry.register(tool)
