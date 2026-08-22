from typing import Dict, List, Optional
from urllib import request
from ..registry import Tool, registry


def web_fetch(url: str, prompt: str = "") -> str:
    with request.urlopen(url, timeout=10) as response:
        return response.read().decode("utf-8", errors="replace")[:4000]


def web_search(query: str, allowed_domains: Optional[List[str]] = None) -> List[Dict[str, str]]:
    return [{"title": f"Result for {query}", "url": f"https://example.com/search?q={query}"}]


TOOLS = [
    Tool("web_fetch", "Network", "MEDIUM", "Scrapes web page", {"required": ["url"], "properties": {"url": {"type": "string"}}}, web_fetch),
    Tool("web_search", "Network", "LOW", "Searches the web", {"required": ["query"], "properties": {"query": {"type": "string"}}}, web_search),
]

for tool in TOOLS:
    registry.register(tool)
