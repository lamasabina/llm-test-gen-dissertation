# LLM Test Generation for REST Microservices — Replication Package

This repository contains the code and frozen dataset for the MSc dissertation:

**"Empirical Evaluation of LLM-Based Test Case Generation for REST Microservices: Coverage vs. Execution Cost in CI/CD-Constrained Environments"**

by Sabina Ghising (London Met ID: 24059547)

## What This Study Compares

- **Code Llama 7B** (via Ollama, Q4_K_M quantisation) — zero-shot and few-shot prompting
- **Schemathesis 4.25.2** — property-based testing from OpenAPI

**Benchmark:** Sock Shop (10 REST operations, OpenAPI 3.0)
**Budget:** 5-minute execution budget
**Repetitions:** 5 per method (15 total runs)

## Contents

- `scripts/` — The RATE framework (7 modules)
- `config/` — `experiment.yaml` and the OpenAPI specification
- `benchmarks/sock-shop/` — Docker Compose and OAS files for reproducibility
- `results/raw/results_frozen_15.csv` — The frozen 15-run dataset
- `results/raw/calibration.csv` — Parser calibration runs (not part of the study)
- `results/figures/` — The three figures used in Chapter 5

## Reproducibility

The exact version used in the dissertation is tagged as **`dissertation-experiment-v1.1`**.

## Limitations

Three measurement limitations are documented in §3.10 of the dissertation:
1. LLM verified coverage = test's own assertion passed
2. Schemathesis verified coverage = JUnit testcase didn't fail
3. Operation lists for Schemathesis are illustrative (counts are valid)

## License

MIT (see LICENSE file).
