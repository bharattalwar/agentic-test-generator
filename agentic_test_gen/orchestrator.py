"""Orchestrator — THE agent loop.

This is what turns our capabilities into an agent: it generates tests, runs them,
observes the result, and DECIDES what to do next — stop if they pass, or revise
and try again if they fail — all within a bounded number of iterations.

The loop carries STATE across iterations (the previous tests + last result),
which is what lets the agent improve instead of blindly retrying.
"""

from .config import AgentConfig
from .llm_client import LLMClient
from .models import RunReport
from .source_reader import read_source
from .prompts import build_generation_prompt, build_revision_prompt
from .test_writer import strip_code_fences
from .test_runner import run_tests


class Orchestrator:
    def __init__(self, config: AgentConfig, llm: LLMClient):
        self.config = config
        self.llm = llm

    def run(self, source_path: str) -> RunReport:
        src = read_source(source_path)

        previous_tests = None
        last_result = None

        for iteration in range(1, self.config.max_iterations + 1):
            # ACT: attempt 1 generates from scratch; later attempts revise using feedback.
            if iteration == 1:
                system, user = build_generation_prompt(src)
            else:
                feedback = last_result.stdout + "\n" + last_result.stderr
                system, user = build_revision_prompt(src, previous_tests, feedback)

            resp = self.llm.complete(system, user)
            test_code = strip_code_fences(resp.text)

            # OBSERVE: run the tests and see what reality says.
            result = run_tests(test_code, src, self.config)
            print(
                f"[iter {iteration}] passed={result.passed} "
                f"return_code={result.return_code} ({result.duration_seconds:.2f}s)"
            )

            # Carry state forward for the next iteration.
            previous_tests = test_code
            last_result = result

            # DECIDE: stop as soon as everything passes.
            if result.passed:
                return RunReport(
                    status="success",
                    iterations_used=iteration,
                    test_code=test_code,
                    last_result=result,
                )

        # Ran out of iterations without a fully-passing suite.
        return RunReport(
            status="failed",
            iterations_used=self.config.max_iterations,
            test_code=previous_tests,
            last_result=last_result,
        )
