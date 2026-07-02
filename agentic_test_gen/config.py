"""Configuration — read settings from the environment (.env) exactly once.

Why keep config separate from code:
- No magic numbers scattered across the codebase; every setting lives here.
- Behavior changes (model, temperature, limits) without editing logic.
- Secrets stay in .env, never in source.
"""

import os
from dotenv import load_dotenv

from .models import AgentConfig


def load_config() -> AgentConfig:
    load_dotenv()  # load .env into environment variables

    # Fail fast with a clear message if the key is missing.
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not set. Add it to your .env file.")

    # Each setting has a sensible default but can be overridden in .env.
    return AgentConfig(
        model=os.getenv("MODEL", "gpt-4o-mini"),
        temperature=float(os.getenv("TEMPERATURE", "0.2")),
        max_tokens=int(os.getenv("MAX_TOKENS", "1500")),
        max_iterations=int(os.getenv("MAX_ITERATIONS", "3")),
        timeout_seconds=int(os.getenv("TIMEOUT_SECONDS", "60")),
    )
