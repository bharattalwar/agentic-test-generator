"""Run the full agent end to end.

Run from the repo root (venv active). Defaults to the calculator sample,
or pass a path to any Python file:
    python try_agent.py
    python try_agent.py evals/samples/stats.py
"""

import sys

from agentic_test_gen.config import load_config
from agentic_test_gen.llm_client import LLMClient
from agentic_test_gen.orchestrator import Orchestrator

# Take the target file from the command line, or default to the calculator.
target = sys.argv[1] if len(sys.argv) > 1 else "evals/samples/calculator.py"

config = load_config()
llm = LLMClient(config)

agent = Orchestrator(config, llm)
report = agent.run(target)

print("\n=== FINAL REPORT ===")
print("Target:", target)
print("Status:", report.status)
print("Iterations used:", report.iterations_used)
print("Final suite passed:", report.last_result.passed)
