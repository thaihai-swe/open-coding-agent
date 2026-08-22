import subprocess
import sys
from typing import Any, Dict
from ..registry import Tool, registry
from ..types import Status


def bash(command: str, timeout: int = 600000, description: str = "", run_in_background: bool = False, dangerously_disable_sandbox: bool = False, bypass_permissions: bool = False) -> Dict[str, Any]:
    proc = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=min(timeout, 600000) / 1000.0)
    return {"exit_code": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}


def powershell(command: str, timeout: int = 600000, bypass_permissions: bool = False) -> Dict[str, Any]:
    if sys.platform != "win32":
        return {"status": Status.UNSUPPORTED_PLATFORM, "platform": sys.platform}
    proc = subprocess.run(["powershell", "-Command", command], capture_output=True, text=True, timeout=timeout / 1000.0)
    return {"exit_code": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}


TOOLS = [
    Tool("bash", "Shell", "HIGH", "Executes shell commands", {"required": ["command"], "properties": {"command": {"type": "string"}}}, bash),
    Tool("powershell", "Shell", "HIGH", "Executes PowerShell command", {"required": ["command"], "properties": {"command": {"type": "string"}}}, powershell),
]

for tool in TOOLS:
    registry.register(tool)
