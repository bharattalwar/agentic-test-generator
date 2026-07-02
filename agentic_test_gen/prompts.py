"""Prompt templates — how we ask the model to write tests.

A prompt has two parts:
- system: the model's role and hard rules (persona + output format)
- user:   the actual task (the code + specific instructions)

Keeping prompts in their own file means we can tune wording (a big lever on
quality) without touching any logic.
"""

from .models import SourceInfo

SYSTEM_PROMPT = (
    "You are an expert Python test engineer. "
    "You write thorough, correct unit tests using pytest. "
    "Output ONLY valid Python code — no explanations, and no markdown code fences."
)


def build_generation_prompt(src: SourceInfo) -> tuple[str, str]:
    """Return (system_prompt, user_prompt) for generating tests from scratch."""
    user = f"""Write pytest unit tests for the following module.

Module name: {src.module_name}
Functions to cover: {", ".join(src.function_names)}

Requirements:
- Import what you need from the module, e.g. `from {src.module_name} import add`.
- Cover normal/happy-path cases AND important edge cases (zero, negatives, empty
  inputs, and error conditions).
- Use `pytest.raises(...)` to assert expected exceptions.
- Give each test a clear, descriptive name.
- Output only runnable Python code.

Source code:
```python
{src.code}
```"""
    return SYSTEM_PROMPT, user


REVISION_SYSTEM_PROMPT = (
    "You are an expert Python test engineer fixing failing pytest tests. "
    "Return the COMPLETE corrected test file. "
    "Output ONLY valid Python code — no explanations, and no markdown code fences."
)


def build_revision_prompt(src: SourceInfo, previous_tests: str, pytest_output: str) -> tuple[str, str]:
    """Return (system, user) for fixing tests that failed, given the pytest output."""
    user = f"""The pytest tests you wrote for module `{src.module_name}` failed.

Here are the tests you wrote:
```python
{previous_tests}
```

Here is the actual pytest output:
```
{pytest_output}
```

Fix the failing tests. Keep the tests that passed. Do NOT change the module under
test — only correct the tests. Import from the module like:
`from {src.module_name} import <function>`. Output the complete corrected test file
as runnable Python code."""
    return REVISION_SYSTEM_PROMPT, user
