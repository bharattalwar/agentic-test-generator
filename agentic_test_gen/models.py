"""Data model — the typed 'contracts' that flow between components.

Using dataclasses means every part of the app exchanges these well-defined
objects instead of loose dicts, which keeps the interfaces clear and testable.
"""

from dataclasses import dataclass


@dataclass
class AgentConfig:
    """All the knobs for a run, loaded once from the environment."""
    model: str
    temperature: float
    max_tokens: int
    max_iterations: int
    timeout_seconds: int


@dataclass
class SourceInfo:
    """What we learn about the file we're going to test."""
    module_name: str
    path: str
    code: str
    function_names: list[str]


@dataclass
class LLMResponse:
    """A single reply from the LLM, plus how many tokens it cost."""
    text: str
    prompt_tokens: int
    completion_tokens: int

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


@dataclass
class TestRunResult:
    """The outcome of running the generated tests — the agent's 'observation'."""
    passed: bool
    return_code: int
    stdout: str
    stderr: str
    duration_seconds: float


@dataclass
class RunReport:
    """The final result of an agent run across all iterations."""
    status: str            # "success" or "failed"
    iterations_used: int
    test_code: str
    last_result: TestRunResult
