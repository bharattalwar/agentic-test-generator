"""Milestone check: generate tests, sanitize + validate them, and write to a file.

Run from the repo root (venv active):
    python try_write.py
"""

from agentic_test_gen.config import load_config
from agentic_test_gen.llm_client import LLMClient
from agentic_test_gen.source_reader import read_source
from agentic_test_gen.prompts import build_generation_prompt
from agentic_test_gen.test_writer import write_tests, strip_code_fences, is_valid_python

config = load_config()
client = LLMClient(config)

# Generate
src = read_source("evals/samples/calculator.py")
system, user = build_generation_prompt(src)
resp = client.complete(system, user)

# Sanitize + validate (the guardrail) before writing
clean = strip_code_fences(resp.text)
print("Valid Python?", is_valid_python(clean))

# Write
path = write_tests(resp.text, "generated/test_calculator.py")
print("Wrote tests to:", path)
