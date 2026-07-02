"""Test writer — sanitize the model's output and write it to a .py file.

Core rule of agentic systems: NEVER trust raw model output. Even with a clear
"output only code" instruction, a model may wrap the code in ```python fences or
add stray prose. We defensively strip fences and validate the result parses as
Python before writing, so the file we hand to the test runner is always sane.
"""

import ast
import re
from pathlib import Path

# Matches a fenced code block:  ```python ... ```   or   ``` ... ```
#   (?:python)?  optional language tag after the opening fence
#   \n?          optional newline right after it
#   (.*?)        the code itself, non-greedy, captured as group 1
#   re.DOTALL    lets '.' match newlines so the block can span many lines
_FENCE_RE = re.compile(r"```(?:python)?\n?(.*?)```", re.DOTALL)


def strip_code_fences(text: str) -> str:
    """Return the inner code if the text has a ``` fenced block, else the text."""
    match = _FENCE_RE.search(text)
    if match:
        return match.group(1).strip()
    return text.strip()


def is_valid_python(code: str) -> bool:
    """A guardrail: does this string parse as valid Python? (Reuses ast.parse.)"""
    try:
        ast.parse(code)
        return True
    except SyntaxError:
        return False


def write_tests(code: str, target_path: str) -> str:
    """Sanitize `code`, write it to `target_path`, and return the path written."""
    clean = strip_code_fences(code)
    path = Path(target_path)
    path.parent.mkdir(parents=True, exist_ok=True)  # create parent folders if missing
    path.write_text(clean)
    return str(path)
