"""Run the compiled graph. LangGraph now walks the nodes + merges state for us —
the same generate -> run we did by hand in try_two_nodes.py.
Run from repo root: python try_graph.py
"""

from agentic_test_gen.agent_graph import build_graph
from agentic_test_gen.source_reader import read_source

app = build_graph()   # compile the graph once

initial_state = {
    "src": read_source("evals/samples/calculator.py"),
    "iteration": 0,
    "test_code": None,
    "last_result": None,
    "status": "pending",
}

# .invoke() starts at the entry point and follows the edges to END,
# merging each node's updates into the state along the way.
final_state = app.invoke(initial_state)

print("\nstatus:", final_state["status"])
print("iterations:", final_state["iteration"])
print("passed:", final_state["last_result"].passed)