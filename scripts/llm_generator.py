#!/usr/bin/env python3
"""
scripts/llm_generator.py — Milestone 3

Responsibility:
  - Build a prompt from a template (zero-shot OR few-shot) + the OAS.
  - POST it to Ollama and capture generated code + timings + tokens.
  - Save code and metadata to results/raw/<strategy>_<run_id>.{py,json}.

Design (for the implementation chapter):
  - Zero-shot and few-shot share the SAME model, temperature, and OAS.
    The only difference is the prompt template.
  - Generation time is wall-clock, captured client-side; includes HTTP
    round-trip and any Ollama queueing. NOT taken from Ollama's internal timer.
  - Tokens come from Ollama's response (prompt_eval_count / eval_count).
  - One generation = one atomic call. Timeout / retry / SIGKILL is the
    experiment_runner's job, not this module's.
"""
from __future__ import annotations

import datetime
import json
import time
from pathlib import Path
from typing import Literal

import requests
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "experiment.yaml"
PROMPTS_DIR = PROJECT_ROOT / "prompts"

Strategy = Literal["llm_zero_shot", "llm_few_shot"]


class LLMGenerator:
    def __init__(self, config_path: Path = CONFIG_PATH):
        with open(config_path) as f:
            cfg = yaml.safe_load(f)
        self.model = cfg["model"]
        self.benchmark = cfg["benchmarks"][0]

    # ── public API ──────────────────────────────────────────

    def generate(self, strategy: Strategy, seed: int | None = None, output_dir: Path | None = None) -> dict:
        """Generate tests. Returns a structured record."""
        if strategy not in ("llm_zero_shot", "llm_few_shot"):
            raise ValueError(f"Unknown strategy: {strategy}")

        template = self._load_template(strategy)
        oas = self._load_oas()
        prompt = template.replace("{oas}", oas)

        payload = {
            "model": self.model["name"],
            "prompt": prompt, "stream": False,
            "options": {"temperature": self.model["temperature"], "seed": seed if seed is not None else self.model.get("seed_base", 42)},
        }

        t0 = time.perf_counter()
        response = requests.post(
            self.model["ollama_url"],
            json=payload,
            timeout=self.model.get("timeout_safety_s", 600),
        )
        elapsed = time.perf_counter() - t0
        response.raise_for_status()
        data = response.json()

        code = data.get("response", "")
        record = {
            "strategy": strategy,
            "model": self.model["name"],
            "temperature": self.model["temperature"],
            "seed": seed,
            "generation_time_s": round(elapsed, 3),
            "prompt_chars": len(prompt),
            "prompt_tokens": data.get("prompt_eval_count"),
            "completion_tokens": data.get("eval_count"),
            "generated_chars": len(code),
            "generated_code": code,
            "timestamp": datetime.datetime.now().isoformat(),
        }

        if output_dir is not None:
            out = Path(output_dir)
            out.mkdir(parents=True, exist_ok=True)
            run_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            (out / f"{strategy}_{run_id}.py").write_text(code)
            (out / f"{strategy}_{run_id}.json").write_text(json.dumps(record, indent=2))
            record["output_files"] = {
                "code": str(out / f"{strategy}_{run_id}.py"),
                "meta": str(out / f"{strategy}_{run_id}.json"),
            }

        return record

    # ── helpers ─────────────────────────────────────────────

    def _load_template(self, strategy: Strategy) -> str:
        name = "zero_shot.txt" if strategy == "llm_zero_shot" else "few_shot.txt"
        path = PROMPTS_DIR / name
        if not path.exists():
            raise FileNotFoundError(f"Prompt template missing: {path}")
        return path.read_text()

    def _load_oas(self) -> str:
        path = Path(self.benchmark["oas_path"])
        if not path.exists():
            raise FileNotFoundError(f"OAS missing: {path}")
        return json.dumps(json.loads(path.read_text()))

    def _ollama_alive(self) -> bool:
        try:
            return requests.get("http://localhost:11434/api/tags", timeout=3).status_code == 200
        except requests.RequestException:
            return False


# ── self-test ───────────────────────────────────────────────
if __name__ == "__main__":
    print("=== LLMGenerator self-test ===")
    gen = LLMGenerator()

    # Pre-flight
    print(f"model         = {gen.model['name']}")
    print(f"oas_path      = {gen.benchmark['oas_path']}")
    print(f"template 0-shot = {PROMPTS_DIR / 'zero_shot.txt'}")
    print(f"template n-shot = {PROMPTS_DIR / 'few_shot.txt'}")

    if not gen._ollama_alive():
        print("\n❌ Ollama not reachable at http://localhost:11434")
        print("   Open a second terminal and run: ollama serve")
        raise SystemExit(1)
    print("\n✅ Ollama reachable")

    # Two real generations (zero-shot then few-shot)
    for strategy in ("llm_zero_shot", "llm_few_shot"):
        print(f"\n[{strategy}] generating ...")
        try:
            rec = gen.generate(strategy, output_dir=PROJECT_ROOT / "results" / "raw")
        except Exception as e:
            print(f"❌ {strategy} failed: {e}")
            raise
        print(f"  generation_time_s = {rec['generation_time_s']}")
        print(f"  prompt_tokens     = {rec['prompt_tokens']}")
        print(f"  completion_tokens = {rec['completion_tokens']}")
        print(f"  generated_chars   = {rec['generated_chars']}")
        print(f"  first 100 chars   = {rec['generated_code'][:100]!r}")

    print("\nSELF-TEST PASSED")
    print("Outputs written to results/raw/")
