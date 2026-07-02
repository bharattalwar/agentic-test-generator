# Agentic Test Generator

An **agentic AI assistant** that automatically writes, runs, and *self-corrects* Python unit tests.

Give it a Python file and the agent uses an LLM to generate `pytest` tests, executes them in an isolated sandbox, reads any failures, and revises the tests in a loop until they pass — the same **generate → run → observe → decide** cycle that defines an AI agent.

Built from scratch on the raw OpenAI API to understand agent internals, then refactored onto LangGraph.

## How it works

1. **Read** the target file (via Python's `ast`) and extract its functions.
2. **Generate** `pytest` tests with an LLM.
3. **Sanitize + validate** the model's output (strip code fences, confirm it parses).
4. **Run** the tests in a throwaway temp-directory sandbox (`subprocess` + timeout).
5. **Decide:** if the tests fail, feed the real `pytest` output back to the LLM and **revise** — repeat up to a bounded number of iterations. Stop as soon as they pass.
6. **Report** the outcome.

## Features

- Self-correcting **generate → run → revise** agent loop
- **Sandboxed**, timed test execution (safe to run generated code)
- **Provider-abstracted** LLM client (swap providers in one place)
- **Guardrails:** bounded iterations, subprocess timeouts, output validation
- Fully configurable via `.env`

## Requirements

- Python 3.10+
- An OpenAI API key

## Setup

```bash
git clone https://github.com/bharattalwar/agentic-test-generator.git
cd agentic-test-generator

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env     # then open .env and add your OPENAI_API_KEY
```

## Usage

```bash
# Run on the bundled sample module:
python try_agent.py

# Or point it at your own Python file:
python try_agent.py path/to/your_module.py
```

You'll see each iteration's result and a final report:

```
[iter 1] passed=True return_code=0 (0.31s)

=== FINAL REPORT ===
Status: success
Iterations used: 1
Final suite passed: True
```

## Configuration (`.env`)

| Variable | Default | Purpose |
|---|---|---|
| `OPENAI_API_KEY` | — | Your OpenAI key (required) |
| `MODEL` | `gpt-4o-mini` | Model to use |
| `TEMPERATURE` | `0.2` | Lower = more focused/repeatable |
| `MAX_TOKENS` | `1500` | Max tokens per generation |
| `MAX_ITERATIONS` | `3` | Max generate/revise attempts |
| `TIMEOUT_SECONDS` | `60` | Per-run test timeout |

## Project structure

```
agentic-test-generator/
├── agentic_test_gen/        # the package
│   ├── config.py            # load settings from .env
│   ├── models.py            # dataclasses (typed contracts)
│   ├── llm_client.py        # provider-abstracted LLM wrapper
│   ├── source_reader.py     # read + parse the target file (ast)
│   ├── prompts.py           # generation + revision prompts
│   ├── test_writer.py       # sanitize + validate + write tests
│   ├── test_runner.py       # sandboxed pytest execution (the tool)
│   └── orchestrator.py      # the agent loop
├── evals/samples/           # sample modules to test against
├── try_agent.py             # run the full agent
├── DESIGN.md                # full design doc + Python/code reference
└── requirements.txt
```

## Design

See **[DESIGN.md](DESIGN.md)** for the full problem statement, requirements, high- and low-level design, and a detailed per-module Python/code reference.

## Roadmap

- LangGraph refactor of the agent loop
- Code-review agent (in addition to test generation)
- CLI + coverage reporting
- Evaluation harness

---

*A learning and portfolio project demonstrating practical agentic-AI patterns (LLM tool-use, self-correction loops, guardrails).*

**Author:** Bharat Talwar
