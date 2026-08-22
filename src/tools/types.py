from enum import StrEnum


class Risk(StrEnum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ToolCategory(StrEnum):
    SHELL = "Shell"
    FILE_IO = "File I/O"
    SEARCH = "Search"
    NETWORK = "Network"
    PLANNING = "Planning"
    AGENT = "Agent"
    DISCOVERY = "Discovery"
    COMMUNICATION = "Communication"
    SETTINGS = "Settings"
    OUTPUT = "Output"
    EXECUTION = "Execution"


class Status(StrEnum):
    SUCCESS = "success"
    ERROR = "error"
    UNSUPPORTED_PLATFORM = "unsupported_platform"


class ConfigAction(StrEnum):
    GET = "get"
    SET = "set"


class MessageStatus(StrEnum):
    NORMAL = "normal"
    PROACTIVE = "proactive"


TODO_STATUSES = {"pending", "in_progress", "completed"}
PROTECTED_KEYS = {".env", "secret"}
PROTECTED_PATHS = (".gitconfig", ".bashrc", ".zshrc", ".env", "id_rsa")
