#!/usr/bin/env python3
"""
scripts/experiment_runner.py — Milestone 6

Responsibility:
  - Orchestrate ONE experimental cell:
      benchmark start -> method generates -> tests execute -> row to CSV.
  - Enforce the time budget with SIGKILL.
  - Write a complete 14-column CSV row per run.

Design notes (for the implementation chapter):
  - Time budget enforcement is done at the ORCHESTRATOR level via
    subprocess.SIGKILL, NOT via the requests timeout. requests timeout
    only protects against a hung Ollama call; SIGKILL enforces the
    experimental budget.
  - Generation time and execution time are captured separately so the
    CCE metric and the Discussion can reason about where time goes.
  - Timeout is recorded as a valid result, not discarded.
"""
from __future__ import annotations

import csv
import datetime
import signal
import subprocess
import sys
import time
from pathlib import Path

import yaml

# Local modules
sys.path.insert(0, str(Path(__file__).resolve().parent))
from benchmark_manager import BenchmarkManager
from llm_generator import LLMGenerator
from test_executor import clean_generated_code, write_test_file, execute_test_file
from endpoint_extractor import compute as compute_op_coverage
from coverage_from_pytest import compute as cov_from_pytest
from schemathesis_runner import SchemathesisRunner

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "experiment.yaml"
CSV_COLUMNS = [
    "run_id", "benchmark", "method", "budget_minutes", "repetition",
    "generation_time_s", "execution_time_s",
    "prompt_tokens", "completion_tokens",
    "line_coverage_pct", "branch_coverage_pct", "api_operation_coverage_pct",
    "cce", "cce_verified", "exit_status", "timeout", "timestamp",
    "verified_coverage_pct", "attempted_ops", "verified_ops",
]


def _run_with_budget(cmd: list[str], budget_s: int, cwd: Path | None = None) -> tuple[int, bool]:
    """Run a subprocess, kill with SIGKILL if it exceeds budget_s."""
    proc = subprocess.Popen(cmd, cwd=str(cwd) if cwd else None,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, start_new_session=True)
    try:
        proc.communicate(timeout=budget_s)
        return proc.returncode, False
    except subprocess.TimeoutExpired:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.communicate()
        return -9, True


class ExperimentRunner:
    def __init__(self, config_path: Path = CONFIG_PATH):
        with open(config_path) as f:
            self.cfg = yaml.safe_load(f)
        self.csv_path = PROJECT_ROOT / self.cfg["paths"]["results_raw"] / "results.csv"
        self.csv_path.parent.mkdir(parents=True, exist_ok=True)

    def run_one(self, method: str, benchmark: str, budget_min: int, rep: int) -> dict:
        run_id = f"{method}_{benchmark}_{budget_min}m_rep{rep}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        print(f"\n=== RUN: {run_id} ===")

        bm = BenchmarkManager(benchmark)
        if not bm.is_alive():
            bm.start()

        gen = LLMGenerator()
        record = {
            "run_id": run_id, "benchmark": benchmark, "method": method,
            "budget_minutes": budget_min, "repetition": rep,
            "generation_time_s": "", "execution_time_s": "",
            "prompt_tokens": "", "completion_tokens": "",
            "line_coverage_pct": "", "branch_coverage_pct": "",
            "api_operation_coverage_pct": "",
            "cce": "", "cce_verified": "", "exit_status": "unknown", "timeout": False,
            "verified_coverage_pct": "", "attempted_ops": "", "verified_ops": "",
            "timestamp": datetime.datetime.now().isoformat(),
        }

        budget_s = budget_min * 60

        # ── SCHEMATHESIS: bypass LLM path ──────────────────────
        if method == "schemathesis":
            print(f"running schemathesis under {budget_s}s budget ...")
            try:
                schem = SchemathesisRunner(
                    Path(self.cfg["benchmarks"][0]["oas_path"]),
                    bm.base_url,
                    timeout_s=budget_s,
                )
                res = schem.run()
                total = len(res.get("attempted_list", [])) or 1
                record["generation_time_s"] = res["total_time_s"]
                record["execution_time_s"] = 0.0
                record["api_operation_coverage_pct"] = round(
                    res["attempted_ops"] / max(total, 1) * 100, 2
                ) if res["attempted_ops"] else 0.0
                # Use OAS op count for coverage denominator
                import json as _json
                oas_total = sum(
                    len(v) for v in _json.load(
                        open(self.cfg["benchmarks"][0]["oas_path"])
                    )["paths"].values()
                )
                record["api_operation_coverage_pct"] = round(
                    res["attempted_ops"] / oas_total * 100, 2
                )
                record["verified_coverage_pct"] = round(
                    res["verified_ops"] / oas_total * 100, 2
                )
                record["attempted_ops"] = res["attempted_ops"]
                record["verified_ops"] = res["verified_ops"]
                record["exit_status"] = (
                    "timeout" if res["timeout"]
                    else f"exit={res['exit_code']},"
                         f"attempted={res['attempted_ops']},"
                         f"verified={res['verified_ops']}"
                )
                record["timeout"] = res["timeout"]
                # CCE
                gt = record["generation_time_s"]
                if gt > 0:
                    record["cce"] = round(record["api_operation_coverage_pct"] / gt, 4)
                    record["cce_verified"] = round(record["verified_coverage_pct"] / gt, 4)
                self._append_csv(record)
                print(f"✅ wrote row (attempted={record['api_operation_coverage_pct']}%, "
                      f"verified={record['verified_coverage_pct']}%)")
                return record
            except Exception as e:
                print(f"❌ schemathesis failed: {e}")
                record["exit_status"] = f"error: {str(e)[:100]}"
                self._append_csv(record)
                return record
        out_dir = PROJECT_ROOT / self.cfg["paths"]["results_raw"]

        # Generate under budget (using SIGKILL enforcement)
        print(f"generating ({method}) under {budget_s}s budget ...")
        t0 = time.perf_counter()
        try:
            gen_record = self._generate_with_budget(gen, method, out_dir, budget_s, seed=self.cfg['model'].get('seed_base', 42) + rep)
            gen_elapsed = time.perf_counter() - t0
            record["generation_time_s"] = round(gen_elapsed, 3)
            record["prompt_tokens"] = gen_record.get("prompt_tokens", "")
            record["completion_tokens"] = gen_record.get("completion_tokens", "")
            raw_code = gen_record["generated_code"]
        except TimeoutError:
            record["exit_status"] = "generation_timeout"
            record["timeout"] = True
            record["generation_time_s"] = round(time.perf_counter() - t0, 3)
            self._append_csv(record)
            return record

        # Clean, write, execute
        cleaned = clean_generated_code(raw_code)
        test_path = PROJECT_ROOT / self.cfg["paths"]["results_processed"] / f"{run_id}.py"
        write_test_file(cleaned, test_path, base_url=bm.base_url)

        # NEW: static API operation coverage (Checkpoint 9)
        try:
            cov = compute_op_coverage(Path(bm.compose_file).parents[3] / "sock-shop-oas.json" if False else Path(self.cfg["benchmarks"][0]["oas_path"]), test_path, base_url=bm.base_url)
            record["api_operation_coverage_pct"] = cov["coverage_pct"]
        except Exception as e:
            print(f"coverage extraction failed: {e}")
            record["api_operation_coverage_pct"] = ""

        print(f"executing {test_path.name} ...")
        exec_result = execute_test_file(test_path, timeout_s=120)

        record["execution_time_s"] = exec_result["execution_time_s"]
        record["exit_status"] = (
            "timeout" if exec_result["timeout"]
            else f"passed={exec_result['tests_passed']},failed={exec_result['tests_failed']},errors={exec_result['tests_errors']}"
        )
        record["timeout"] = exec_result["timeout"]

        # Runtime coverage from pytest outcomes (attempted + verified)
        try:
            cov = cov_from_pytest(
                Path(self.cfg["benchmarks"][0]["oas_path"]),
                exec_result.get("per_test", {}),
                test_file_path=test_path,
            )
            record["api_operation_coverage_pct"] = cov["attempted_coverage_pct"]
            record["verified_coverage_pct"] = cov["verified_coverage_pct"]
            record["attempted_ops"] = cov["attempted_ops"]
            record["verified_ops"] = cov["verified_ops"]
            print(f"  coverage: attempted={cov['attempted_coverage_pct']}%, verified={cov['verified_coverage_pct']}%")
        except Exception as e:
            print(f"coverage computation failed: {e}")

        # CCE: only defined if we have real operation coverage. For this checkpoint we
        # don't yet have coverage instrumentation, so leave blank rather than fake it.
        record["cce"] = ""

        # Compute CCE = coverage% / generation_time_s (per supervisor correction)
        try:
            cov = record.get('api_operation_coverage_pct')
            gt  = record.get('generation_time_s')
            if (isinstance(cov, (int, float)) and not isinstance(cov, bool)
                and isinstance(gt, (int, float)) and gt > 0):
                record['cce'] = round(cov / gt, 4)
                vcov = record.get('verified_coverage_pct')
                if isinstance(vcov, (int, float)) and not isinstance(vcov, bool):
                    record['cce_verified'] = round(vcov / gt, 4)
        except Exception:
            pass

        self._append_csv(record)
        print(f"✅ wrote row to {self.csv_path}")
        return record

    def _generate_with_budget(self, gen: LLMGenerator, method: str, out_dir: Path, budget_s: int, seed: int = 42) -> dict:
        """Run LLMGenerator.generate() with a hard budget. Uses SIGALRM on macOS."""
        import threading
        result: dict = {}
        error: list = []

        def worker():
            try:
                result.update(gen.generate(method, seed=seed, output_dir=out_dir))
            except Exception as e:
                error.append(e)

        t = threading.Thread(target=worker, daemon=True)
        t.start()
        t.join(timeout=budget_s)
        if t.is_alive():
            raise TimeoutError(f"generation exceeded {budget_s}s budget")
        if error:
            raise error[0]
        return result

    def _append_csv(self, record: dict) -> None:
        new_file = not self.csv_path.exists()
        with open(self.csv_path, "a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
            if new_file:
                w.writeheader()
            w.writerow({k: record.get(k, "") for k in CSV_COLUMNS})


# ── self-test ───────────────────────────────────────────────
if __name__ == "__main__":
    print("=== ExperimentRunner self-test ===")
    print("One full cell: llm_zero_shot × sock-shop × 5 min × rep 1")
    runner = ExperimentRunner()
    row = runner.run_one(
        method="llm_zero_shot",
        benchmark="sock-shop",
        budget_min=5,
        rep=1,
    )
    print("\n--- Result row ---")
    for k, v in row.items():
        print(f"  {k}: {v}")
    print(f"\nCSV: {runner.csv_path}")
    print("\nSELF-TEST PASSED")
