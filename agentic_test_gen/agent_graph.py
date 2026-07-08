"""LangGraph version of the agent — built step by step.
Step 2: State + generate_node.
"""

from typing import Optional, TypedDict

from langchain_openai import ChatOpenAI

from .config import load_config
from .models import SourceInfo, TestRunResult
from .prompts import build_generation_prompt
from .test_writer import strip_code_fences
from .test_runner import run_tests
from langgraph.graph import END, StateGraph
from .prompts import build_generation_prompt, build_revision_prompt

_config = load_config()

# Same model wrapper you just used in langchain_hello.py.
_llm = ChatOpenAI(
    model=_config.model,
    temperature=_config.temperature,
    max_tokens=_config.max_tokens,
)


class AgentState(TypedDict):
    """The shared memory that flows through the graph — the same variables your
    orchestrator kept as locals, gathered into one object."""
    src: SourceInfo                       # the file we're testing
    iteration: int                        # how many attempts so far
    test_code: Optional[str]              # the latest generated tests
    last_result: Optional[TestRunResult]  # result of the last run
    status: str                           # "pending" / "success" / "failed"


def generate_node(state: AgentState) -> dict:
    """ACT step. First attempt writes tests from scratch; later attempts REVISE
    using the previous tests + the real pytest failure output."""
    src = state["src"]

    if state["iteration"] == 0:
        # First attempt — generate fresh.
        system, user = build_generation_prompt(src)
    else:
        # Later attempt — feed back what failed so the model can fix it.
        result = state["last_result"]
        feedback = f"{result.stdout}\n{result.stderr}"
        system, user = build_revision_prompt(src, state["test_code"], feedback)

    response = _llm.invoke([("system", system), ("human", user)])

    return {
        "test_code": strip_code_fences(response.content),
        "iteration": state["iteration"] + 1,
    }

def run_node(state: AgentState) -> dict:
    """A NODE for the OBSERVE step: run the generated tests with our existing
    run_tests tool, and record the result + a status."""
    result = run_tests(state["test_code"], state["src"], _config)

    print(
        f"[iter {state['iteration']}] passed={result.passed} "
        f"return_code={result.return_code} ({result.duration_seconds:.2f}s)"
    )

    return {
        "last_result": result,
        "status": "success" if result.passed else "failed",
    }

def should_continue(state: AgentState) -> str:
    """The DECIDE step, as a router. Returns the NAME of the next hop."""
    if state["last_result"].passed:
        return "end"                                  # passed — stop
    if state["iteration"] >= _config.max_iterations:
        return "end"                                  # out of attempts — stop
    return "revise"                                   # failed, attempts left — loop

def build_graph():
    """Wire the two nodes into a graph and compile it into a runnable app.
    For now it's linear: generate -> run -> END (no loop yet)."""
    graph = StateGraph(AgentState)

    graph.add_node("generate", generate_node)
    graph.add_node("run", run_node)

    graph.set_entry_point("generate")   # start here
    graph.add_edge("generate", "run")   # always: generate -> run
    graph.add_conditional_edges(
        "run",
        should_continue,
        {
            "revise": "generate",   # <-- the backward arrow: THE LOOP
            "end": END,
        },
    )

    return graph.compile()


