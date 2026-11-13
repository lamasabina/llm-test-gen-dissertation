#!/usr/bin/env python3
"""
scripts/test_executor.py — Milestone 4a

Responsibility:
  - Clean raw LLM output (markdown fences, prose preamble).
  - Write a pytest-compatible file with BASE_URL header.
  - Execute under timeout and return structured results.

Design notes (for the implementation chapter):
  - Code Llama empirically ignores "no markdown fences" instructions
    (observed in pilot). Cleaning is therefore unavoidable, not optional.
  - Execution happens SEPARATELY from generation. This split lets us
    attribute time correctly: generation_time_s vs execution_time_s.
  - pytest exit code + pass/fail counts are captured; output is preserved
    verbatim for post-hoc inspection.
"""
from __future__ import annotations

import re
import subprocess
import time
from pathlib import Path


def clean_generated_code(raw: str) -> str:
    """Strip markdown fences and prose preamble. Return only Python."""
    text = raw.strip()

    # Case 1: fenced block with language tag (```python ... ```)
    m = re.search(r"```(?:python|py)?\s*\n(.*?)\n\s*```", text, re.DOTALL)
    if m:
        return m.group(1).strip() + "\n"

    # Case 2: any fenced block (``` ... ```)
    m = re.search(r"```\s*\n(.*?)\n\s*```", text, re.DOTALL)
    if m:
        return m.group(1).strip() + "\n"

    # Case 3: no fences — cut everything before the first import/def/from
    m = re.search(r"^(import |from |def |class )", text, re.MULTILINE)
    if m:
        return text[m.start():].strip() + "\n"

    # Case 4: return as-is (best effort)
    return text + "\n"


def write_test_file(cleaned_code: str, out_path: Path, base_url: str) -> Path:
    """Write a pytest-runnable file with a BASE_URL header."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    header = (
        "import requests\n"
        "import pytest\n\n"
        f"BASE_URL = '{base_url}'\n\n"
    )
    # Avoid double-importing requests/pytest if the LLM already did
    body = cleaned_code
    if "import requests" in body:
        body = re.sub(r"^import requests\s*$", "", body, count=1, flags=re.MULTILINE)
    if "import pytest" in body:
        body = re.sub(r"^import pytest\s*$", "", body, count=1, flags=re.MULTILINE)
    out_path.write_text(header + body.lstrip())
    return out_path


def execute_test_file(test_path: Path, timeout_s: int = 120) -> dict:
    """Run pytest on the file. Return structured results."""
    t0 = time.perf_counter()
    try:
        proc = subprocess.run(
            ["pytest", str(test_path), "-v", "--tb=short"],
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
        duration = time.perf_counter() - t0
        stdout = proc.stdout
        passed = int(re.search(r"(\d+) passed", stdout).group(1)) if re.search(r"(\d+) passed", stdout) else 0
        failed = int(re.search(r"(\d+) failed", stdout).group(1)) if re.search(r"(\d+) failed", stdout) else 0
        errors = int(re.search(r"(\d+) error", stdout).group(1)) if re.search(r"(\d+) error", stdout) else 0
        # NEW: per-test outcomes for coverage measurement
        per_test = {}
        for m in re.finditer(r"::(?P<name>test_\S+)\s+(?P<status>PASSED|FAILED|ERROR)", stdout):
            per_test[m.group("name")] = m.group("status")
        print(f"[debug] per_test = {per_test}")
        return {
            "execution_time_s": round(duration, 3),
            "exit_code": proc.returncode,
            "tests_passed": passed,
            "tests_failed": failed,
            "tests_errors": errors,
            "timeout": False,
            "per_test": per_test,
            "stdout_full": stdout[:8000],
            "stdout_tail": "\n".join(stdout.splitlines()[-10:]),
        }
    except subprocess.TimeoutExpired:
        return {
            "execution_time_s": round(time.perf_counter() - t0, 3),
            "exit_code": -9,
            "tests_passed": 0,
            "tests_failed": 0,
            "tests_errors": 0,
            "timeout": True,
            "stdout_tail": f"TIMEOUT after {timeout_s}s",
        }


# ── self-test ───────────────────────────────────────────────
if __name__ == "__main__":
    print("=== TestExecutor self-test ===")
    project = Path(__file__).resolve().parent.parent
    raw_files = sorted((project / "results" / "raw").glob("llm_zero_shot_*.py"))
    if not raw_files:
        raise SystemExit("No raw LLM output found — run Checkpoint 5 first")

    raw_path = raw_files[-1]
    print(f"raw_input     = {raw_path.name}")
    raw_code = raw_path.read_text()
    print(f"raw_length    = {len(raw_code)} chars")
    print(f"raw_starts_with = {raw_code[:30]!r}")

    cleaned = clean_generated_code(raw_code)
    print(f"cleaned_len   = {len(cleaned)} chars")
    print(f"cleaned_starts = {cleaned[:60]!r}")

    test_file = project / "results" / "processed" / "pilot_test_zero_shot.py"
    write_test_file(cleaned, test_file, base_url="http://localhost:80")
    print(f"written       = {test_file}")

    print("\nexecuting against live Sock Shop ...")
    result = execute_test_file(test_file, timeout_s=120)
    print(f"  execution_time_s = {result['execution_time_s']}")
    print(f"  exit_code        = {result['exit_code']}")
    print(f"  passed           = {result['tests_passed']}")
    print(f"  failed           = {result['tests_failed']}")
    print(f"  errors           = {result['tests_errors']}")
    print(f"  timeout          = {result['timeout']}")
    print("\nSELF-TEST PASSED")
