"""Run generate_node then run_node BY HAND, passing state between them.
This is exactly what LangGraph automates for us next step.
Run from repo root: python try_two_nodes.py
"""

from agentic_test_gen.agent_graph import generate_node, run_node
from agentic_test_gen.source_reader import read_source

# The shared state, built by hand.
state = {
    "src": read_source("evals/samples/calculator.py"),
    "iteration": 0,
    "test_code": None,
    "last_result": None,
    "status": "pending",
}

# Node 1: generate. Merge its returned updates back into state.
state.update(generate_node(state))

# Node 2: run. Merge again.
state.update(run_node(state))

print("\nfinal status:", state["status"])
print("passed:", state["last_result"].passed)