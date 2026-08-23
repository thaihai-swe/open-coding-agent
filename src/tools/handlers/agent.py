from .. import skills
from ..registry import Tool, registry


def load_skill(name: str) -> str:
    return skills.load_skill_content(name)


def compact() -> str:
    return "Compacted. History summarized."


TOOLS = [
    Tool(
        "load_skill",
        "Agent",
        "LOW",
        "Load the full content of a skill by name.",
        {"required": ["name"], "properties": {"name": {"type": "string"}}},
        load_skill,
    ),
    Tool(
        "compact",
        "Agent",
        "LOW",
        "Triggers context compaction to summarize earlier conversation history and free up context window space.",
        {"properties": {}, "type": "object"},
        compact,
    ),
]

for tool in TOOLS:
    registry.register(tool)
