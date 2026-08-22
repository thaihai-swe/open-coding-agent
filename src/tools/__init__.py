from .handlers import agent, communication, discovery, execution, file_io, network, output, planning, search, settings, shell
from .permissions import check_permission, validate_args
from .registry import Tool, ToolRegistry, registry
from .types import ConfigAction, MessageStatus, Risk, Status, ToolCategory

TOOLS = list(registry.tools.values())


def invoke(name: str, **kwargs):
    tool = registry.get(name)
    if not tool:
        return {"status": Status.ERROR, "error": f"Unknown tool: {name}"}
    try:
        validate_args(tool.schema, kwargs)
        check_permission(tool, kwargs)
        return {"status": Status.SUCCESS, "result": tool.handler(**kwargs)}
    except Exception as error:
        return {"status": Status.ERROR, "error": str(error)}


__all__ = ["TOOLS", "Tool", "ToolCategory", "ToolRegistry", "Risk", "Status", "invoke", "registry"]
