"""Test the generate_node by itself — no graph yet.
Run from the repo root: python try_node.py
"""

from agentic_test_gen.agent_graph import generate_node
from agentic_test_gen.source_reader import read_source

# Build a starting state BY HAND. (Later, LangGraph passes this around for us.)
state = {
    "src": read_source("evals/samples/calculator.py"),
    "iteration": 0,
    "test_code": None,
    "last_result": None,
    "status": "pending",
}

# A node is just a function — call it and look at what it returns.
updates = generate_node(state)

print("iteration is now:", updates["iteration"])
print("---- generated tests ----")
print(updates["test_code"])