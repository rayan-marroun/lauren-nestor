import os

from openai import OpenAI


def get_client() -> OpenAI:
    base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")
    return OpenAI(base_url=base_url, api_key="ollama")


def get_model() -> str:
    return os.environ.get("OLLAMA_MODEL", "qwen2.5:14b")
