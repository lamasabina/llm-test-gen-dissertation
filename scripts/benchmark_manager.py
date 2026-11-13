#!/usr/bin/env python3
"""
scripts/benchmark_manager.py — Milestone 2

Responsibility:
  1. Start the benchmark microservice via docker-compose.
  2. Poll the health endpoint until the API actually responds.
  3. Provide clean shutdown.
  4. Expose is_alive() so the experiment runner can pre-check each run.

Design notes (for the implementation chapter):
  - A running container != a ready API. We poll the health endpoint.
  - All paths come from config/experiment.yaml (single source of truth).
  - Methods raise on failure; the caller decides how to log.
"""
from __future__ import annotations

import subprocess
import time
from pathlib import Path

import requests
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "experiment.yaml"


class BenchmarkManager:
    def __init__(self, benchmark_name: str, config_path: Path = CONFIG_PATH):
        with open(config_path) as f:
            cfg = yaml.safe_load(f)
        matches = [b for b in cfg["benchmarks"] if b["name"] == benchmark_name]
        if not matches:
            raise ValueError(f"Benchmark '{benchmark_name}' not found in {config_path}")
        b = matches[0]

        self.name = benchmark_name
        self.base_url = b["base_url"].rstrip("/")
        self.health_url = f"{self.base_url}{b['health_endpoint']}"
        self.compose_file = Path(b["compose_file"])
        self.ready_timeout_s = b.get("ready_timeout_s", 120)

        if not self.compose_file.exists():
            raise FileNotFoundError(f"compose_file not found: {self.compose_file}")

    def start(self) -> float:
        """Start the benchmark. Returns startup time in seconds."""
        print(f"[{self.name}] docker-compose up -d ...")
        t0 = time.perf_counter()
        try:
            subprocess.run(
                ["docker-compose", "-f", str(self.compose_file), "up", "-d"],
                cwd=str(self.compose_file.parent),
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"docker-compose up failed:\nSTDERR:\n{e.stderr}"
            ) from e
        self._wait_until_ready()
        elapsed = time.perf_counter() - t0
        print(f"[{self.name}] ready in {elapsed:.1f}s")
        return elapsed

    def stop(self) -> None:
        print(f"[{self.name}] docker-compose down ...")
        subprocess.run(
            ["docker-compose", "-f", str(self.compose_file), "down"],
            cwd=str(self.compose_file.parent),
            check=True,
            capture_output=True,
            text=True,
        )
        print(f"[{self.name}] stopped")

    def is_alive(self) -> bool:
        try:
            return requests.get(self.health_url, timeout=5).status_code == 200
        except requests.RequestException:
            return False

    def _wait_until_ready(self) -> None:
        deadline = time.perf_counter() + self.ready_timeout_s
        last = None
        while time.perf_counter() < deadline:
            try:
                r = requests.get(self.health_url, timeout=5)
                if r.status_code == 200:
                    return
                last = f"HTTP {r.status_code}"
            except requests.RequestException as e:
                last = type(e).__name__
            time.sleep(2)
        raise TimeoutError(
            f"[{self.name}] not ready within {self.ready_timeout_s}s (last: {last})"
        )


# ── self-test ───────────────────────────────────────────────
if __name__ == "__main__":
    print("=== BenchmarkManager self-test ===")
    mgr = BenchmarkManager("sock-shop")
    print(f"health_url   = {mgr.health_url}")
    print(f"compose_file = {mgr.compose_file}")

    if mgr.is_alive():
        print("already running - skipping start()")
    else:
        print(f"start() took {mgr.start():.1f}s")

    assert mgr.is_alive(), "is_alive() returned False"
    print("is_alive() = True")
    print("SELF-TEST PASSED (benchmark left running for next module)")
