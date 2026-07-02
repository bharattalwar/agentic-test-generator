"""Milestone check: generate tests, then RUN them in the sandbox and report.

Run from the repo root (venv active):
    python try_run.py
"""

from agentic_test_gen.config import load_config
from agentic_test_gen.llm_client import LLMClient
from agentic_test_gen.source_reader import read_source
from agentic_test_gen.prompts import build_generation_prompt
from agentic_test_gen.test_writer import strip_code_fences
from agentic_test_gen.test_runner import run_tests

config = load_config()
client = LLMClient(config)

# Generate tests
src = read_source("evals/samples/calculator.py")
system, user = build_generation_prompt(src)
resp = client.complete(system, user)
test_code = strip_code_fences(resp.text)

# Run them in the sandbox — the agent's first look at reality
result = run_tests(test_code, src, config)

print("Passed:", result.passed)
print("Return code:", result.return_code)
print(f"Duration: {result.duration_seconds:.2f}s")
print("\n--- pytest output ---\n")
print(result.stdout)
