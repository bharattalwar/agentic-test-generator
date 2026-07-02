"""Test runner — the agent's 'tool'. Runs the generated tests and reports back.

Safety-first design:
- Runs pytest in a SEPARATE process (subprocess), so bad generated code can't
  crash or hang our app, and we can enforce a timeout.
- Runs inside a throwaway TEMP DIRECTORY (the 'sandbox'): we copy the source
  module and the generated tests into it, run there, and let it auto-delete.
  This isolates execution AND makes `from <module> import ...` resolve, since
  the module and its tests sit side by side.
"""

import shutil
import subprocess
import sys
import time
from pathlib import Path
from tempfile import TemporaryDirectory

from .models import AgentConfig, SourceInfo, TestRunResult


def run_tests(test_code: str, src: SourceInfo, config: AgentConfig) -> TestRunResult:
    with TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        # Copy the source module into the sandbox so the tests can import it.
        shutil.copy(src.path, tmp_path / Path(src.path).name)

        # Write the generated tests next to it.
        (tmp_path / f"test_{src.module_name}.py").write_text(test_code)

        start = time.perf_counter()
        try:
            # sys.executable + "-m pytest" runs THIS venv's pytest reliably.
            completed = subprocess.run(
                [sys.executable, "-m", "pytest", "-q"],
                cwd=tmp,                 # run inside the sandbox
                capture_output=True,     # collect stdout/stderr
                text=True,               # give us strings, not bytes
                timeout=config.timeout_seconds,   # hard guardrail
            )
            return TestRunResult(
                passed=(completed.returncode == 0),   # pytest: 0 = all passed
                return_code=completed.returncode,
                stdout=completed.stdout,
                stderr=completed.stderr,
                duration_seconds=time.perf_counter() - start,
            )
        except subprocess.TimeoutExpired as e:
            return TestRunResult(
                passed=False,
                return_code=-1,
                stdout=e.stdout or "",
                stderr=f"Timed out after {config.timeout_seconds}s",
                duration_seconds=time.perf_counter() - start,
            )
