# Agentic Test Generator — Interview Prep

**Author:** Bharat Talwar
**Purpose:** My study + talking-points doc for this project. Concepts explained plainly (so I can teach them, e.g. to Manish), plus likely interview questions with honest answers. Pair this with DESIGN.md §7 (the concept walkthrough).

---

## 0. The 60-second project pitch

I built an **agentic test-generation assistant**: point it at a Python file, and an LLM-driven agent writes a pytest suite, runs it in a sandbox, reads the actual results, and if anything fails it revises and tries again — up to a bounded number of attempts. I built the agent loop **from scratch first** (plain Python, no framework) so I understood every moving part, then **refactored it into LangGraph** to get standard state management and a graph I can inspect and extend. It's a real, running project on GitHub, not a tutorial clone. It mirrors the "AI agents for code + QA automation" work that agentic-AI roles are hiring for.

Honest framing (I say this out loud): this is a **recently built** portfolio project, not years of production agentic experience. My depth is 20+ years in payments/accounting platforms; the agentic work is how I'm applying that judgment to a new toolset.

---

## 1. What is an "agent" (vs a chatbot, vs a workflow)?

- A **chatbot / single LLM call** takes input → returns output. One shot. No memory of a goal, no actions in the world.
- A **workflow / chain** is a fixed sequence of steps (A → B → C). Deterministic order, no branching back.
- An **agent** adds two things: it can **use tools** (take actions and get real feedback), and it **loops** — it decides what to do next based on what it observed, until a goal is met or a limit is hit.

My agent's loop is **Generate → Observe → Decide**:
- **Generate** (reason + act): the LLM writes tests.
- **Observe**: run the tests with a tool (`run_tests`) and capture the real pytest output.
- **Decide**: pass → stop; fail + attempts left → revise and loop; out of attempts → stop.

This is the **ReAct pattern** (Reason + Act): alternate between the model reasoning and the model acting on a tool, using each observation to inform the next step.

**The "tool" is the crux.** What separates an agent from a fancy prompt is that it acts on the world and *reacts to real results*. My tool is a pytest runner — the model doesn't guess whether tests pass, it finds out for real and fixes based on the actual error.

**Bounded autonomy.** The `max_iterations` cap is a deliberate guardrail — an agent left to loop forever is a liability. Interviewers like hearing that I thought about the stop condition, cost, and runaway-loop risk.

---

## 2. LangChain vs LangGraph (know the difference cold)

- **LangChain** = talking to the model + common building blocks (model wrappers like `ChatOpenAI`, prompt templates, output parsers, tools). It replaced my hand-written `llm_client.py`.
- **LangGraph** = structuring a **stateful, possibly cyclic** multi-step process as a graph of **nodes** and **edges**. It replaced my `for`-loop.

One-liner: **LangChain talks to the model; LangGraph organizes the steps.**

Why LangGraph over a plain LangChain "chain"? A **chain is one-directional** (A→B→C). My agent needs to **loop back** (fail → revise → run again). LangGraph is built for cycles and shared state, which is exactly a stateful agent. That's why it's the go-to for agentic workflows.

---

## 3. The LangGraph mechanics (be able to draw this)

```
        ┌─────────────┐
        │  generate   │◄─────────┐
        └──────┬──────┘          │  "revise"
               │ (plain edge)    │
        ┌──────▼──────┐          │
        │     run     │──────────┘
        └──────┬──────┘   should_continue: failed + attempts left
               │ "end": passed OR out of attempts
        ┌──────▼──────┐
        │     END     │
        └─────────────┘
```

- **State** (`AgentState`, a `TypedDict`): the shared memory passed between nodes — `src`, `iteration`, `test_code`, `last_result`, `status`. Replaces the scattered local variables from my `for`-loop.
- **Node** = a function `f(state) -> dict of changes`. LangGraph merges the returned dict back into state. My nodes: `generate_node` (ACT), `run_node` (OBSERVE).
- **Plain edge** (`add_edge`) always fires: generate → run.
- **Router** (`should_continue`) = a function that returns a *string* naming the next hop. It is **not a node** — it does no work, only decides direction.
- **Conditional edge** (`add_conditional_edges`) maps that string to a real destination via a path map `{"revise": "generate", "end": END}`. The `"revise" → "generate"` entry is the **cycle**.
- **`compile()`** freezes it into an app; **`invoke(initial_state)`** runs it and returns the final state.

Why keep both `orchestrator.py` and `agent_graph.py`? The hand-built version proves I understand the fundamentals; the LangGraph version shows I can adopt the standard framework. Great story: *"from first principles, then production framework."*

---

## 4. RAG — what it is, and why this project is NOT RAG

**Short answer to "is generate/observe/decide RAG?": No.** They're unrelated ideas that often appear together.

**RAG = Retrieval-Augmented Generation.** The problem it solves: an LLM only knows its training data and whatever you put in the prompt. If you need it to answer using *your* private/current documents (a policy manual, a codebase, product docs), you can't fit everything in the prompt and the model won't have it memorized. RAG fixes that by **retrieving the relevant pieces at query time and injecting them into the prompt.**

The typical RAG pipeline:
1. **Index (offline):** chunk your documents → convert each chunk to an **embedding** (a vector capturing meaning) → store in a **vector database** (FAISS, Pinecone, pgvector, Chroma).
2. **Retrieve (per query):** embed the user's question → find the most **similar** chunks by vector distance (semantic search).
3. **Augment + generate:** paste those chunks into the prompt as context → the LLM answers **grounded** in them.

Payoff: current/private knowledge, fewer hallucinations, citeable sources — without retraining the model.

**Why my agent isn't RAG:** it retrieves nothing from a knowledge base. It reads one source file (via `ast`), generates tests, and grounds itself in **real tool output** (pytest results), not in retrieved documents. Grounding in *tool feedback* (agentic) is a different thing from grounding in *retrieved text* (RAG).

**How they relate:** RAG and agents are **composable**. RAG can be *a tool an agent uses* — e.g., an agent that, before writing tests, retrieves my team's testing-style guide from a vector store (RAG) and then runs tests (tool). So: RAG = a retrieval technique; agent = a looping tool-user. My next project (a reconciliation/ledger agent) is where I plan to add a real RAG step (retrieve relevant accounting rules/policies), so I can speak to RAG hands-on too.

Interview-safe one-liner: *"RAG is about feeding the model the right knowledge at query time via retrieval; my agent is about letting the model take actions and react to real results. Different axes — and you can combine them by making RAG one of the agent's tools."*

---

## 5. Evals — how I'd know the agent is any good

An agent's output is non-deterministic, so "it ran once" isn't proof. **Evals** = a repeatable way to measure quality. For this project:
- A set of **sample source files** with known characteristics (edge cases, error paths) in `evals/samples/`.
- Metrics I care about: does the generated suite **pass**, does it **cover the edge cases** (e.g., divide-by-zero), how many **iterations** it took, token **cost**, wall-clock time.
- Interview point: I'd add an `evals/run_evals.py` harness that runs the agent over all samples and reports a scorecard, so a change (new prompt, new model) can be measured, not guessed. This is "prompt-regression / eval framework" — language the agentic JDs explicitly ask for.

(Honest status: the eval harness is a planned next step; the sample files and the manual pass/fail checks exist today.)

---

## 6. Guardrails & production concerns (shows senior judgment)

- **Sandboxing:** generated code is untrusted, so `run_tests` executes pytest in a **subprocess** inside a **temp directory**, with a **timeout**. Bad/looping generated code can't crash or hang my app.
- **Bounded autonomy:** `max_iterations` caps cost and prevents infinite loops.
- **Determinism knobs:** low `temperature` (0.2) for more stable output; config lives in `.env`, not code.
- **Output validation:** `strip_code_fences` + an `ast.parse` check ensure the model returned valid Python before I try to run it.
- **Provider abstraction:** started behind my own `LLMClient`; LangChain's `ChatOpenAI` continues that — swap models without touching logic.
- **What I'd add for real production:** cost/latency logging per run, an eval gate in CI, human-in-the-loop review before tests are committed, secrets management, retries/backoff on API errors.

---

## 7. Likely interview questions (with my answers)

**Q: Walk me through the architecture.**
Source reader (`ast`) → prompt builder → LLM (generate) → test writer (clean/validate) → test runner (sandboxed pytest) → orchestrator/graph that loops generate→run→decide until pass or max attempts. Two implementations: hand-built `orchestrator.py` and LangGraph `agent_graph.py`.

**Q: What makes it "agentic" and not just an LLM call?**
It uses a **tool** (pytest) and **loops on real feedback** — it observes actual failures and revises, with a bounded stop condition. That feedback loop is the agent.

**Q: Why LangGraph and not a simple chain?**
A chain can't loop back. My agent must revise on failure, which is a cycle over shared state — LangGraph's core use case.

**Q: What's the difference between a node and the router?**
Nodes (`generate_node`, `run_node`) do work and return state updates. The router (`should_continue`) does no work — it inspects state and returns the *name* of the next hop for a conditional edge.

**Q: How do you prevent runaway cost or infinite loops?**
`max_iterations` cap, low temperature, timeouts on the test subprocess, and (next) per-run cost logging + eval gates.

**Q: How would you evaluate it?**
An eval harness over labeled sample files, scoring pass rate, edge-case coverage, iterations, and cost — so changes are measured, not vibes.

**Q: Is this RAG?**
No — see §4. It grounds in tool output, not retrieved documents. RAG could be added as one of the agent's tools.

**Q: How would you extend it?**
Multi-file/project support, coverage-driven prompting, more tools (linter, coverage report), a RAG step to pull in team testing conventions, human-in-the-loop approval, CI integration.

**Q: What was hard / what did you learn?**
Coming from Java, I built this in Python and learned the agentic stack hands-on. The insight that stuck: an agent is only as good as its tool and its stop condition — the LLM is one part; the engineering around feedback, sandboxing, and guardrails is what makes it trustworthy. That maps directly to my payments background, where correctness and guardrails are everything.

---

## 8. Honesty guardrails (my own rules for these interviews)

- Lead with **domain depth** (payments/accounting, 20+ yrs) — that's unfakeable and differentiating.
- Call the agentic work **recent and self-built**, not years of production. Never claim multi-year agentic experience.
- I can confidently **walk through the design and every line of code**, because I built it from scratch — that's stronger than having used a framework I can't explain.
