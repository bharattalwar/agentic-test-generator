"""LLM client — the ONE place that talks to the model provider.

Everything else in the app calls this wrapper, not OpenAI directly. So if we
later swap to Claude, add retries, or log every call, we change this one file
instead of touching the whole codebase. This is the 'provider abstraction'.
"""

from openai import OpenAI

from .models import AgentConfig, LLMResponse


class LLMClient:
    def __init__(self, config: AgentConfig):
        self.config = config
        self._client = OpenAI()  # reads OPENAI_API_KEY from the environment

    def complete(self, system: str, user: str) -> LLMResponse:
        """Send a system + user message, return the reply and its token usage."""
        response = self._client.chat.completions.create(
            model=self.config.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        )
        usage = response.usage
        return LLMResponse(
            text=response.choices[0].message.content,
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
        )
