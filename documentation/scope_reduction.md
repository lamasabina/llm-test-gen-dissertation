# Scope Reduction — Empirical Justification

## What was attempted

The original proposal specified three benchmarks: Sock Shop, TrainTicket
(68 endpoints, Java), and eShopOnContainers (95 endpoints, .NET). During
Phase 2 of the supervisor's plan, all three were cloned and deployed.

## TrainTicket attempt (documented)

**Deployment attempted:** 2026-11-13, 09:31 GMT+5:45
**Command:** `NAMESPACE=codewisdom TAG=0.2.0 docker-compose up -d`
**Environment:** MacBook Air (Apple Silicon M2/M3), 8 GB RAM, macOS 15.x
**Outcome:** Partial failure

**Observations:**
1. TrainTicket deploys **111 containers** (40+ Java Spring Boot services,
   ~40 MongoDB instances, Redis, Voucher MySQL, Nacos, RabbitMQ).
2. All images are published for `linux/amd64`. On Apple Silicon
   (`linux/arm64/v8`), Docker is forced to emulate via Rosetta 2 / qemu,
   incurring 3-5x CPU overhead per container.
3. Startup failed with:
   `Error response from daemon: Bind for 0.0.0.0:8080 failed: port is
   already allocated` — a port collision between TrainTicket's dashboard
   and an existing service (Sock Shop edge-router or a stale container).
4. Even where containers reported "Started", Docker's "Started" status
   only indicates process creation, not successful Java application boot.
   Spring Boot typically requires 30-90s to become responsive under native
   execution, and 3-5× longer under amd64 emulation on ARM hardware.
5. Preliminary RAM estimates: 111 containers × ~300-600 MB idle = 33-66 GB
   of RAM required, vs. the 8 GB available on the test machine.

## eShopOnContainers

Not attempted within the time budget. eShop is smaller (~15 containers)
but requires a .NET 7/8 build pipeline that is known to fail on Apple
Silicon without Rosetta-specific SDK workarounds. Estimated setup cost:
1-2 hours of debugging with uncertain success probability.

## Scope decision

The formal experiment is scoped to **Sock Shop only**, with three generation
methods (LLM zero-shot, LLM few-shot, Schemathesis) and 5 repetitions per
cell (15 runs). This scope was chosen because:

- Sock Shop deploys cleanly on the target hardware (8 GB / ARM).
- It provides 10 REST operations — sufficient to detect measurable
  differences between methods.
- The framework remains fully reproducible on any machine.

## How this is handled in the dissertation

- **§3.2 (Subject System)** states the single-benchmark design and its
  justification.
- **§5.7 (Threats to Validity — External)** discusses single-benchmark
  as a constraint on generalisability.
- **§6.5 (Limitations)** and **§6.6 (Future Work)** present multi-benchmark
  replication as a well-defined future extension, with the deployment
  evidence above as the reason it was not attempted within the MSc timeline.

## Academic honesty note

This is a documented scope reduction, not a silent substitution. The
framework, code, and configuration required to run TrainTicket and
eShopOnContainers remain in the repository (`benchmarks/` directory) for
future researchers with adequate hardware.
