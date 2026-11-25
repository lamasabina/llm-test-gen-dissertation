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
    """
    Run pytest on the file with JUnit XML output.
    Parse pass/fail/error from the XML report, not the terminal text.

    Returns:
        execution_time_s, exit_code, per_test, tests_passed,
        tests_failed, tests_errors, timeout, junit_xml_path
    """
    import xml.etree.ElementTree as ET
    import tempfile

    xml_path = Path(tempfile.gettempdir()) / f"pytest_{test_path.stem}.xml"
    if xml_path.exists():
        xml_path.unlink()

    t0 = time.perf_counter()
    try:
        proc = subprocess.run(
            [
                "pytest", str(test_path),
                "-v", "--tb=short",
                f"--junitxml={xml_path}",
            ],
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
        duration = time.perf_counter() - t0
    except subprocess.TimeoutExpired:
        return {
            "execution_time_s": round(time.perf_counter() - t0, 3),
            "exit_code": -9,
            "per_test": {},
            "tests_passed": 0,
            "tests_failed": 0,
            "tests_errors": 0,
            "timeout": True,
            "junit_xml_path": None,
            "stdout_tail": f"TIMEOUT after {timeout_s}s",
        }

    # ── Parse JUnit XML (authoritative source) ─────────────────
    per_test = {}
    passed = failed = errors = 0

    if xml_path.exists() and xml_path.stat().st_size > 0:
        try:
            tree = ET.parse(xml_path)
            for tc in tree.iter("testcase"):
                name = tc.get("name") or tc.get("classname") or "unknown"
                if tc.find("failure") is not None:
                    per_test[name] = "FAILED"
                    failed += 1
                elif tc.find("error") is not None:
                    per_test[name] = "ERROR"
                    errors += 1
                elif tc.find("skipped") is not None:
                    per_test[name] = "SKIPPED"
                else:
                    per_test[name] = "PASSED"
                    passed += 1
        except ET.ParseError as e:
            print(f"[WARN] JUnit XML parse error: {e}")

    # Sanity check: XML count must match pytest summary count
    xml_total = len(per_test)
    summary_total = passed + failed + errors
    if xml_total != summary_total:
        print(f"[WARN] XML/terminal mismatch: XML={xml_total}, terminal={summary_total}")

    return {
        "execution_time_s": round(duration, 3),
        "exit_code": proc.returncode,
        "per_test": per_test,
        "tests_passed": passed,
        "tests_failed": failed,
        "tests_errors": errors,
        "timeout": False,
        "junit_xml_path": str(xml_path),
        "stdout_tail": "\n".join((proc.stdout or "").splitlines()[-10:]),
    }


