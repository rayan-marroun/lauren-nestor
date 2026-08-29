from ddgs import DDGS

SCHEMA = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": "Search the public web. Returns titles, URLs, and snippets.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "max_results": {"type": "integer", "default": 8},
            },
            "required": ["query"],
        },
    },
}


def web_search(query: str, max_results: int = 8) -> str:
    with DDGS() as ddgs:
        results = list(ddgs.text(query, max_results=max_results))
    if not results:
        return "no results"
    lines = []
    for r in results:
        lines.append(f"- {r.get('title')}\n  {r.get('href')}\n  {r.get('body', '')[:300]}")
    return "\n".join(lines)
