# Agentic Test Generator — Design Document

**Author:** Bharat Talwar
**Status:** Draft (v1 in progress)

> This document is both the design spec and my learning log. Sections marked **Concept** capture ideas I'm learning as I build, so the whole document reads scratch-to-understanding for anyone (including me, six months from now).

---

## 1. Problem Statement

Writing and maintaining thorough unit tests is one of the most repetitive, time-consuming, and frequently deprioritized parts of software engineering. Under delivery pressure, teams ship code with coverage gaps, and regressions slip through because tests were never written or never updated. The work is mechanical enough to feel like a chore, yet nuanced enough that naive automation produces shallow or broken tests.

I'm building an **agentic AI assistant that automates unit-test creation for Python code**. Given a source file, the agent generates unit tests, executes them in a sandbox, reads the actual failures, and iteratively revises the tests until they pass — or clearly explains why they can't. It then reports what it produced, the pass/fail outcome, and coverage.

What makes this *agentic* rather than a one-shot script: it doesn't just ask an LLM for tests and stop. It operates in a loop — it **acts** (writes tests), **uses a tool** (runs them), **observes** real feedback (the test results), and **decides its next step** based on that feedback, all within guardrails and an evaluation harness that measure whether it's actually helping.

### Goals (v1)
- Take a Python file (or function) as input and produce a runnable `pytest` test file.
- Execute the generated tests in an isolated sandbox and capture results.
- Iterate on failures up to a bounded number of attempts, revising tests each round.
- Report outcomes: tests generated, pass/fail, coverage, and a short summary.
- Enforce guardrails: sandboxed execution, iteration/token limits, no unbounded loops or cost.
- Include a small evaluation harness to measure the agent's quality over time.

### Non-Goals (v1)
- Not multi-language — Python only to start.
- Not whole-repository scanning — single file/module first.
- Not code review, refactoring, or doc generation yet — those are later phases.
- No model training or fine-tuning — we apply existing LLMs.
- No web UI initially — command-line first; a Gradio interface can come later.

> **Concept — "agent" vs "pipeline":** A *pipeline* runs fixed steps once (input → LLM → output). An *agent* has a **loop with feedback**: it takes an action, observes the result through a tool, and chooses its next action based on what it observed — repeating until a goal is met or a limit is hit. Our test-runner-in-the-loop is precisely that difference.

---

## 2. Requirements

### Functional Requirements (v1)
1. Accept a path to a single Python source file as input.
2. Read the source and identify the functions/classes to be tested.
3. Use the LLM to generate `pytest` unit tests covering happy paths and edge cases.
4. Write the tests to a `test_<module>.py` file.
5. Execute the generated tests in an isolated sandbox and capture pass/fail results and errors.
6. On failure, feed the actual results back to the LLM and revise the tests — repeat up to a bounded number of iterations.
7. Stop when all tests pass, no further progress is made, or the max-iteration limit is reached.
8. Report: tests generated, pass/fail counts, coverage %, iterations used, and a short summary (including anything it couldn't test and why).
9. Expose all of this through a command-line interface.

### Non-Functional Requirements (v1)
1. **Safety** — generated code runs only in a sandboxed subprocess with a timeout; never `exec`'d in the main process.
2. **Cost & latency guardrails** — hard caps on iterations, tokens, and total API calls; log token usage per run.
3. **Reproducibility** — pin the model version, keep generation temperature low, and log every prompt/response for traceability.
4. **Configurability** — model, max iterations, temperature all set via config/`.env`.
5. **Observability** — structured logs of each agent step (action → tool result → decision) so the loop is inspectable.
6. **Secrets hygiene** — API key loaded from `.env`, never hardcoded or committed.
7. **Provider abstraction** — LLM calls sit behind a small interface so OpenAI can be swapped for another provider later.
8. **Evaluability** — a lightweight eval harness to score runs (e.g., % tests passing, coverage delta) on sample inputs.

> **Concept — why non-functional requirements matter *more* for agents:** In a normal app, the code does exactly what you wrote. An agent decides its own next actions and executes generated code, so **safety, cost caps, and observability aren't polish — they're load-bearing.** An unbounded agent loop can burn API budget or run unsafe code. "How did you put guardrails on your agent?" is a near-certain interview question, and NFRs 1, 2, and 5 are the answer.

---

## 3. High-Level Design

### Components (v1)
- **CLI (entry point)** — parses arguments (target file, options), starts a run.
- **Config loader** — reads `.env` + settings: model, max iterations, temperature, token/timeout caps.
- **Agent Orchestrator** — the brain; runs the generate→run→observe→decide loop within guardrails. Everything else is a service it calls.
- **Source Reader / Analyzer** — reads the target Python file; extracts function/class signatures to ground the prompt.
- **Prompt Builder** — builds the initial *test-generation* prompt and the *revision* prompt (which includes the real failure output).
- **LLM Client** — provider-abstracted wrapper around OpenAI; sends prompts, returns completions, tracks token usage.
- **Test Writer** — writes the generated test code to `test_<module>.py`.
- **Test Runner (the tool)** — runs `pytest` in a sandboxed subprocess with a timeout; captures pass/fail, errors, and coverage.
- **Reporter** — produces the final summary (tests, pass/fail, coverage, iterations, notes).
- **Logger** — structured, step-by-step logs of the loop (action → tool result → decision).
- **Eval Harness** — a separate entry point that runs the agent on sample files and scores it.
- **Guardrails** — cross-cutting: iteration cap, token cap, subprocess timeout, sandboxing (enforced in the Orchestrator and Test Runner).

### The agent loop (core control flow)
1. Read the source file → analyze structure.
2. Build the generation prompt.
3. LLM generates tests.
4. Write tests to a file.
5. Run tests in the sandbox → observe results (the "perception" step).
6. **Decide:** all pass → Reporter (done); failures remain and iterations left → build a revision prompt with the failure output → go to step 3; max iterations hit or no improvement → Reporter (partial result).
7. Report.

```
  CLI ──▶ Orchestrator ◀── Config/.env
              │  (bounded loop)
              ▼
   Source ─▶ Prompt ─▶ LLM ─▶ Test ─▶ Test Runner
   Reader    Builder   Client  Writer   (sandbox pytest)
                ▲                             │
                │      results (pass/fail)    │
                └──────── revise ◀────────────┘
                              │
                     pass / limit ▼
                          Reporter
```

> **Concept — the "ReAct" pattern (Reason + Act):** the agent alternates between *reasoning* (LLM decides what tests to write / how to fix them) and *acting* (running the tests via a tool), using each observation to inform the next reasoning step. Agent frameworks like LangGraph formalize this same loop as a state machine — building it by hand first makes the abstraction obvious later.

## 4. Low-Level Design

### 4.1 Project structure
```
agentic-test-generator/
├── README.md
├── DESIGN.md
├── INTERVIEW_PREP.md
├── requirements.txt
├── .env.example            # placeholders (committed)
├── .env                    # real key (local only, gitignored)
├── src/agentic_test_gen/
│   ├── __init__.py
│   ├── cli.py              # entry point, arg parsing
│   ├── config.py           # loads .env + settings → AgentConfig
│   ├── models.py           # dataclasses (the data contracts)
│   ├── llm_client.py       # provider-abstracted LLM wrapper (OpenAI)
│   ├── source_reader.py    # read + analyze the target file
│   ├── prompts.py          # generation + revision prompt templates
│   ├── test_writer.py      # write generated tests to disk
│   ├── test_runner.py      # sandboxed pytest execution
│   ├── orchestrator.py     # THE agent loop
│   ├── reporter.py         # final summary
│   └── logging_setup.py    # structured logging
├── evals/
│   ├── samples/            # sample source files to test the agent on
│   └── run_evals.py        # eval harness
└── tests/                  # tests for the agent's own code
```

### 4.2 Data model (`models.py`, dataclasses)
```
AgentConfig       # model, max_iterations, temperature, max_tokens, timeout_s, ...
SourceInfo        # module_name, code, functions[]
LLMResponse       # text, prompt_tokens, completion_tokens
GeneratedTests    # code, iteration, raw_response, tokens
TestRunResult     # passed, total, passed_n, failed_n, failures[], stdout, stderr, coverage_pct, duration
AgentStep         # iteration, action, observation, decision   (logging)
RunReport         # status, iterations_used, tests_path, last_result, summary, total_tokens
```

### 4.3 Module interfaces
```python
config.load_config() -> AgentConfig
LLMClient(config).complete(system: str, user: str) -> LLMResponse
source_reader.read_source(path) -> SourceInfo
prompts.build_generation_prompt(src: SourceInfo) -> tuple[str, str]        # (system, user)
prompts.build_revision_prompt(src, prev: GeneratedTests, result: TestRunResult) -> tuple[str, str]
test_writer.write_tests(code: str, target_path: str) -> str
test_runner.run_tests(test_path: str, source_dir: str, timeout: int) -> TestRunResult
orchestrator.Orchestrator(config, llm, ...).run(source_path: str) -> RunReport
reporter.render(report: RunReport) -> str
```

### 4.4 Prompt strategy
- **Generation** — *system:* "You are an expert Python test engineer. Output only valid `pytest` code, no prose." *user:* the source code + instructions (cover happy paths and edge cases, one behavior per test, clear names).
- **Revision** — includes previous tests + actual pytest failure output + "fix the failing tests; keep the passing ones."

> **Concept — dataclasses as contracts:** modules talk only through these typed objects, never by reaching into each other's internals — which makes each piece independently testable and swappable (e.g., a Claude `LLMClient`, or a Docker-based `test_runner`) without touching the orchestrator.

## 5. Implementation Notes

- **Package layout:** the package is a flat `agentic_test_gen/` at the repo root (not `src/agentic_test_gen/`). The `src/` layout is best practice for shipping libraries but adds import friction while learning; we may adopt it later with an editable install (`pip install -e .`).
- **Config is environment-driven:** all settings come from `.env` via `load_dotenv()`, with defaults in `config.py`. Secrets (the API key) live only in `.env`, which git ignores.
- **`try_*.py` smoke scripts:** the root-level `first_call.py` → `try_client.py` → `try_generate.py` scripts are manual checkpoints, each proving one new capability. They are not part of the package and will be replaced by the CLI and a real test suite.
- **Run entry scripts, not package modules:** run `python try_generate.py` from the repo root. Running an inner module directly (e.g. `python agentic_test_gen/llm_client.py`) breaks the relative imports — that's expected Python packaging behavior.

## 6. Python & Code Reference (learning + interview prep)

A per-module record of the Python features/functions used and why. Updated as we build.

### `models.py`
- **`from dataclasses import dataclass` / `@dataclass`** — decorator that auto-generates `__init__`, `__repr__`, and `__eq__` from typed fields. Used for `AgentConfig`, `SourceInfo`, `LLMResponse`. *Why:* concise, typed, comparable data holders — less boilerplate than a hand-written class, more structure and safety than a dict.
- **Type hints** (`model: str`, `function_names: list[str]`) — annotations that document intent and power editor/linter tooling. Not enforced at runtime. `list[str]` is the built-in generic form (Python 3.9+).
- **`@property`** (`total_tokens`) — exposes a *computed* value that's accessed like a plain attribute (`resp.total_tokens`, no parentheses). *Why:* derived values without storing/duplicating them.

### `config.py`
- **`load_dotenv()`** (python-dotenv) — reads a `.env` file into `os.environ` so the rest of the code can use `os.getenv`. Keeps secrets/config out of source.
- **`os.getenv("KEY", default)`** — read an environment variable with a fallback if it's unset.
- **`float(...)` / `int(...)`** — env vars are always strings; we cast them to numbers.
- **`raise RuntimeError("…")`** — a *guard clause* that fails fast with a clear message when required config (the API key) is missing. *Interview note:* validate inputs at the boundary, fail early and loudly.

### `llm_client.py`
- **`class` + `__init__(self, config)`** — a constructor that stores config and creates the `OpenAI()` client **once**, then reuses it across calls (avoids re-creating it every request).
- **`client.chat.completions.create(model=, messages=, temperature=, max_tokens=)`** — the core LLM call. `messages` is a list of `{"role": ..., "content": ...}` dicts (system/user/assistant).
- **Nested response access** — `response.choices[0].message.content` (the reply text) and `response.usage.prompt_tokens` / `.completion_tokens` (the cost meter).
- **Returning a typed `LLMResponse`** instead of the raw SDK object — decouples the rest of the app from OpenAI's response shape. *Interview note:* this is the *adapter / provider-abstraction* pattern.

### `source_reader.py`
- **`import ast`** — Python's Abstract Syntax Tree module for reading code *structurally* instead of with string search.
  - **`ast.parse(code)`** — turns source text into a tree of nodes.
  - **`ast.walk(tree)`** — a generator that yields every node in the tree (recursive traversal).
  - **`ast.FunctionDef`** — the node type representing a `def`. We keep nodes where **`isinstance(node, ast.FunctionDef)`** is true and read `node.name`.
- **List comprehension** — `[node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]` builds the list of function names in one expression.
- **`from pathlib import Path`** — object-oriented file paths.
  - **`Path(path).read_text()`** — read the whole file into a string.
  - **`Path(path).stem`** — filename without directory or extension (`.../calculator.py` → `calculator`).
- *Interview note:* `ast` is how real code tools (linters, formatters, coverage) understand code; grounding the prompt in parsed facts reduces model hallucination.

### `prompts.py`
- **Module-level constant** (`SYSTEM_PROMPT`, uppercase by convention) — shared, unchanging text.
- **Multi-line f-string** (`f"""…{src.module_name}…"""`) — a template with variables interpolated inline.
- **`", ".join(src.function_names)`** — joins a list of strings into one comma-separated string.
- **`tuple[str, str]` return** — returns two values (system, user) as a typed tuple.
- *Interview note:* keeping prompt text out of logic lets you iterate on wording (the biggest quality lever) without changing code.

### `test_writer.py`
- **`import re`** — Python's regular-expression module for pattern matching on text.
  - **`re.compile(pattern, re.DOTALL)`** — pre-compile a pattern for reuse. `re.DOTALL` makes `.` also match newlines (so a code block can span many lines).
  - **Pattern `` ```(?:python)?\n?(.*?)``` ``** — `(?:python)?` is a *non-capturing optional* group; `(.*?)` is a *non-greedy capture* (the smallest match, so it stops at the first closing fence); the parentheses make it *group 1*.
  - **`.search(text)`** returns the first match (or `None`); **`.group(1)`** returns the captured code.
- **`ast.parse(code)` inside `try/except SyntaxError`** — a guardrail: if the string isn't valid Python it raises `SyntaxError`, which we catch to return `False`. Reuses `ast` from `source_reader` for a different purpose (validation, not extraction).
- **`Path(target).parent.mkdir(parents=True, exist_ok=True)`** — create the destination folder(s): `parents=True` makes intermediate dirs, `exist_ok=True` doesn't error if it already exists.
- **`Path(...).write_text(clean)`** — write a string to a file in one call.
- *Interview note:* the "output-reliability ladder" — (1) prompt instructions, (2) defensive parsing + validation, (3) structured outputs / tool-calling. Fence-stripping + `ast.parse` validation is layer 2.

### `test_runner.py`
- **`from tempfile import TemporaryDirectory`** — a context manager (`with TemporaryDirectory() as tmp:`) that creates a throwaway directory and **auto-deletes it** (and everything inside) when the block ends. This is our sandbox.
- **`import shutil` → `shutil.copy(src, dst)`** — copy a file (here, the source module into the sandbox).
- **`from pathlib import Path`** — `tmp_path / "test_x.py"` uses the `/` operator to join paths cleanly (pathlib overloads `/` for path joining).
- **`import subprocess` → `subprocess.run(cmd, cwd=, capture_output=True, text=True, timeout=)`** — run an external command as a separate process. `cmd` is a *list* of arguments (safer than a shell string); `cwd` sets the working directory; `capture_output` collects stdout/stderr; `text=True` returns strings not bytes; `timeout` raises after N seconds.
- **`import sys` → `sys.executable`** — the path to the current Python interpreter; `[sys.executable, "-m", "pytest"]` guarantees we run *this* venv's pytest.
- **`completed.returncode`** — the process exit code. Convention: `0` = success. pytest returns non-zero if any test fails — that's our pass/fail signal.
- **`except subprocess.TimeoutExpired`** — raised when the command exceeds `timeout`; we catch it and return a failed result instead of hanging (guardrail NFR-2).
- **`import time` → `time.perf_counter()`** — a high-resolution timer; subtract two readings to measure elapsed seconds.
- *Interview note:* running untrusted/generated code = subprocess + sandbox + timeout. "How did you execute the model's code safely?" — this trio is the answer.

### `orchestrator.py`
- **`class Orchestrator` with `__init__(self, config, llm)`** — *dependency injection*: the config and LLM client are passed in, not created inside. This makes the orchestrator easy to test (you can inject a fake LLM) and swap.
- **`for iteration in range(1, self.config.max_iterations + 1)`** — `range(1, N+1)` counts `1..N` inclusive (range excludes its stop value, so we add 1). The loop bound *is* the guardrail on autonomy.
- **State variables across the loop** (`previous_tests`, `last_result`) — carried from one iteration to the next; this "memory" is what lets the agent revise instead of retry blindly.
- **Conditional first-vs-rest** (`if iteration == 1: generate else: revise`) — attempt 1 generates from scratch; later attempts use the revision prompt with real failure feedback.
- **Early `return`** on success — exits the loop the moment the suite passes (the decision point).
- *Interview note:* this loop is the ReAct pattern realized — Reason (LLM) + Act (run tests) + Observe (results) + Decide (stop/revise), with bounded autonomy. It's exactly what LangGraph will formalize as a state graph.

### `agent_graph.py` (the LangGraph refactor)
This is the same generate → run → decide loop from `orchestrator.py`, re-expressed as an explicit graph. Built from scratch first, then adopted the framework — the intended interview story ("I understand the loop well enough to hand-roll it, then chose LangGraph for the state/observability it gives for free").
- **`class AgentState(TypedDict)`** — the shared state that flows through the graph. `TypedDict` = a dict with a declared shape (keys + types) but still a plain dict at runtime; LangGraph passes this between nodes. Replaces the loose loop variables (`previous_tests`, `last_result`) with one typed object.
- **Node functions (`generate_node`, `run_node`)** — each takes the state and returns a **partial dict** of only the keys it changed; LangGraph merges those updates back into the state. `generate_node` = Reason/Act (write tests); `run_node` = Observe (run pytest via the *same* `run_tests` tool the orchestrator used — one tool, two drivers).
- **`ChatOpenAI` (langchain-openai)** — LangChain's OpenAI wrapper; plays the role the hand-written `LLMClient` did. `.invoke([("system", ...), ("human", ...)])` returns a message whose `.content` is the text.
- **`should_continue(state) -> str`** — the DECIDE step as a **router**: returns a *string* naming the next hop (`"revise"` or `"end"`), based on `last_result.passed` and the iteration guardrail. Pure decision, no side effects.
- **`StateGraph(AgentState)`** — the graph builder, typed on the state shape.
- **`add_node(name, fn)`** — register a node. **`set_entry_point("generate")`** — where every run starts. **`add_edge("generate", "run")`** — a *plain* edge that always fires.
- **`add_conditional_edges("run", should_continue, {...})`** — the branch: run the router after `run`, then map its returned string through the **path map** (`{"revise": "generate", "end": END}`) to the real destination. `"revise" → "generate"` is the **cycle** (the loop); `END` is LangGraph's terminal sentinel.
- **`.compile()`** — turns the definition into a runnable app; call `app.invoke(initial_state)` to execute, which returns the final state.
- *Interview note:* chains run one direction; graphs can loop. The backward `revise → generate` edge is what makes this a **stateful agent** and not a linear pipeline — the reason LangGraph is the go-to for cyclic, stateful agent workflows. Same four verbs as the orchestrator; the difference is the control flow is now **data** (nodes + edges) you can inspect, visualize, checkpoint, and extend, instead of being trapped inside a `for` loop.

### Python vocabulary (quick reference)
- **Built-in function** — available without import (`print`, `len`, `open`, `isinstance`, `range`). Lives in the `builtins` namespace.
- **Standard library** — ships with Python but must be imported (`pathlib`, `ast`, `re`, `os`, `subprocess`, `tempfile`, `json`). No `pip install`.
- **Third-party** — installed via `pip` (`openai`, `python-dotenv`, `pytest`).
- **Function vs method** — a *function* is called alone (`len(x)`); a *method* belongs to an object and is called with a dot (`path.write_text(x)`, `"hi".upper()`). E.g. `Path.write_text` is a *method* from the *standard library* — not a built-in.

---

## 7. Agentic Refactor — Concept Walkthrough (orchestrator → LangGraph)

> I wrote this section as a teaching narrative so I (and anyone I walk through the project) can follow it top-to-bottom without prior LangChain/LangGraph knowledge. It mirrors the exact order I built it in.

### 7.1 The one idea: I already built an agent

Before any framework, my `orchestrator.py` was already an agent. Its `for`-loop does three things, over and over:

1. **Generate** — call the LLM to write tests (ACT).
2. **Observe** — run those tests with `run_tests` and see what happened.
3. **Decide** — if they pass, stop; if they fail and I have attempts left, loop back and revise.

Generate → Observe → Decide, repeating, with a cap on attempts. That *is* an agent. This loop is the **ReAct pattern** (Reason + Act): the model reasons about what to write, acts by running a tool, and uses the observation to reason again. Everything after this is just a cleaner way to *express* this same loop — not a smarter idea.

### 7.2 Two libraries, two different jobs (the thing everyone confuses)

- **LangChain** = the toolkit for *talking to the model*. Its `ChatOpenAI` object is a thin wrapper around the OpenAI API. It replaces my hand-written `llm_client.py`. Benefit: a standard interface — I could swap OpenAI for Claude by changing one line, and every LangChain/LangGraph piece speaks this same interface.
- **LangGraph** = the toolkit for *structuring the loop*. It replaces the `for`-loop in `orchestrator.py` with **nodes** and **edges**. It does not talk to the model itself — the nodes do that (using LangChain).

One-line memory hook: **LangChain talks to the model; LangGraph organizes the steps.**

### 7.3 State — the shared memory

My `for`-loop kept its working memory in local variables (`previous_tests`, `last_result`, `iteration`). A graph has no single loop scope, because the steps are separate functions. So all that memory has to live in **one shared object that gets passed from step to step** — the **State**.

I declare its shape with a `TypedDict` (`AgentState`) — literally a list of the keys the state holds and their types: `src`, `iteration`, `test_code`, `last_result`, `status`. At runtime it's still an ordinary dict; the `TypedDict` just documents and type-checks the shape.

### 7.4 A node is just a function

A **node** is a plain Python function that:

- takes the whole `state` as input, and
- returns a **dict of only the keys it changed**.

LangGraph merges that returned dict back into the state for me. That merge is the entire mechanism — the same thing as calling `state.update(returned_dict)` by hand (which is literally how I tested the nodes before wiring the graph). Two nodes:

- **`generate_node`** — the ACT step. First attempt (`iteration == 0`) generates from scratch with `build_generation_prompt`; later attempts **revise** with `build_revision_prompt`, feeding the previous tests + the real pytest failure output back to the model. It calls `ChatOpenAI.invoke([...])` and returns the cleaned `test_code` plus a bumped `iteration`.
- **`run_node`** — the OBSERVE step. Runs the tests with the *same* `run_tests` tool the orchestrator uses (subprocess pytest in a temp sandbox), and returns `last_result` + a `status`.

Key point for the interview: I did **not** rebuild the work. `run_tests` and the prompt builders are reused unchanged. The graph only changes *how the steps are wired*, not *what they do*.

### 7.5 Edges, and the decision that makes it loop

Edges connect nodes.

- A **plain edge** always fires: `add_edge("generate", "run")` means "after generate, always go to run."
- The **entry point** (`set_entry_point("generate")`) is where every run starts.
- `END` is LangGraph's built-in "stop here" marker.

The DECIDE step is a **router function**, `should_continue(state) -> str`. It is *not* a node — it does no work and changes no state. It just looks at the state and returns a **string** naming where to go next:

- tests passed → `"end"`
- out of attempts (`iteration >= max_iterations`) → `"end"`
- failed but attempts remain → `"revise"`

That string is turned into a real destination by a **conditional edge**:

```python
graph.add_conditional_edges("run", should_continue, {"revise": "generate", "end": END})
```

This reads: "after `run`, call `should_continue`; take the string it returns; look it up in this path map to find the next node." The entry `"revise": "generate"` points **backward** to `generate` — and a backward edge is the **cycle**. That cycle is the whole reason to use LangGraph: chains run one direction; a graph can loop. The loop is what makes this a **stateful agent** instead of a straight-line pipeline.

### 7.6 Compile and run

`graph.compile()` freezes the wiring into a runnable app. `app.invoke(initial_state)` starts at the entry point, walks the edges, merges each node's updates into the state, and returns the final state — exactly what my `for`-loop did, but now the control flow is **data** (nodes + edges) I can inspect, draw, checkpoint, and extend, rather than logic buried inside a loop.

### 7.7 Terminology I want to get exactly right (so I don't fumble it live)

- **Node vs router.** `generate_node` and `run_node` are nodes (they do work and update state). `should_continue` is a **router / conditional-edge function** (it only decides direction). Calling it a "decision node" is loose; interviewers may probe this.
- **LangChain vs LangGraph.** ChatOpenAI (the model wrapper) is **LangChain**. StateGraph / nodes / edges is **LangGraph**. I keep these separate.
- **`LLMResponse`.** My dataclass is used on the hand-built `orchestrator` path (via `LLMClient`). On the LangGraph path, `ChatOpenAI` returns its own message object and I read `.content`, so `LLMResponse` isn't used there — worth stating plainly.
- **This is not RAG.** See INTERVIEW_PREP.md §RAG. This project retrieves nothing from a knowledge base; it's an agentic loop. RAG is a different technique that can be *added* to an agent, but generate/observe/decide is not RAG.

### 7.8 The two implementations, side by side

| | `orchestrator.py` (hand-built) | `agent_graph.py` (LangGraph) |
|---|---|---|
| Loop | Python `for` with `max_iterations` | Graph with a conditional-edge cycle |
| Memory | local variables | `AgentState` (TypedDict) |
| Model call | `LLMClient` (my wrapper) | `ChatOpenAI` (LangChain) |
| The tool | `run_tests` | `run_tests` (same) |
| Decide | `if result.passed: return` | `should_continue` router |
| Why keep both | proves I understand the loop from first principles | shows I can adopt the standard framework |

Interview story in one line: *"I built the agent loop by hand first so I understood every moving part, then refactored it into LangGraph to get standard state handling, a visualizable graph, and room to grow — keeping the hand-built version to show the fundamentals."*
