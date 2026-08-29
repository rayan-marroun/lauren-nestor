import os

from openai import OpenAI


class LLMRouter:
    """Tries Groq primary, then Groq secondary, then local Ollama.

    Each call re-tries from the top -- there's no persistent "stuck on
    fallback" state, so a transient Groq blip self-heals on the next turn
    without needing retry/backoff logic here.
    """

    def __init__(self):
        groq_key = os.environ.get("GROQ_API_KEY", "").strip()
        # Groq is normally fast -- a hang past ~30s means something's
        # actually wrong (bad key, network issue), so fail fast and fall
        # through rather than block the whole loop waiting on it.
        self._groq_client = (
            OpenAI(base_url="https://api.groq.com/openai/v1", api_key=groq_key, timeout=30.0, max_retries=1)
            if groq_key else None
        )
        self._groq_primary = os.environ.get("GROQ_MODEL_PRIMARY", "openai/gpt-oss-120b")
        self._groq_fallback = os.environ.get("GROQ_MODEL_FALLBACK", "openai/gpt-oss-20b")

        # Local CPU inference is legitimately slow -- generous timeout since
        # this is the last resort and bailing early would leave her stuck.
        self._ollama_client = OpenAI(
            base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
            api_key="ollama",
            timeout=180.0,
            max_retries=1,
        )
        self._ollama_model = os.environ.get("OLLAMA_MODEL", "qwen2.5:14b")

    def create(self, **kwargs):
        errors = []

        if self._groq_client is not None:
            for model in (self._groq_primary, self._groq_fallback):
                try:
                    response = self._groq_client.chat.completions.create(model=model, **kwargs)
                    return response, model
                except Exception as exc:  # noqa: BLE001 -- any failure just tries the next provider
                    errors.append(f"{model}: {exc}")

        try:
            response = self._ollama_client.chat.completions.create(model=self._ollama_model, **kwargs)
            return response, self._ollama_model
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{self._ollama_model}: {exc}")
            raise RuntimeError("All providers failed: " + " | ".join(errors)) from exc
