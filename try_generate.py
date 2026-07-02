"""Milestone check: feed real code to the model and print the tests it writes.

Run from the repo root (venv active):
    python try_generate.py
"""

from agentic_test_gen.config import load_config
from agentic_test_gen.llm_client import LLMClient
from agentic_test_gen.source_reader import read_source
from agentic_test_gen.prompts import build_generation_prompt

config = load_config()
client = LLMClient(config)

# 1. Read the target file and find its functions.
src = read_source("evals/samples/calculator.py")
print("Functions found:", src.function_names)

# 2. Build the generation prompt from that source.
system, user = build_generation_prompt(src)

# 3. Ask the model to write the tests.
resp = client.complete(system, user)

# 4. Show what it produced.
print("\n--- Generated tests ---\n")
print(resp.text)
print(f"\n(tokens: {resp.total_tokens})")
