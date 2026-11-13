#!/usr/bin/env python3
"""Final pilot analysis + figures for Chapter 4."""
import csv
from pathlib import Path
from statistics import mean, stdev
import numpy as np
from scipy import stats
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

PROJ = Path(__file__).resolve().parent.parent
CSV = PROJ / "results" / "raw" / "results.csv"
FIG = PROJ / "results" / "figures"
FIG.mkdir(parents=True, exist_ok=True)

rows = list(csv.DictReader(open(CSV)))
methods = ["llm_zero_shot", "llm_few_shot", "schemathesis"]
labels = {"llm_zero_shot": "LLM\nzero-shot",
          "llm_few_shot": "LLM\nfew-shot",
          "schemathesis": "Schemathesis"}

def get(m, col):
    return [float(r[col]) for r in rows if r["method"] == m
            and r[col] not in ("", "None")]

def ci95(xs):
    if len(xs) < 2: return (0, 0)
    m, s = mean(xs), stdev(xs)
    se = s / np.sqrt(len(xs))
    t = stats.t.ppf(0.975, len(xs) - 1)
    return (m - t * se, m + t * se)

print("=" * 78)
print("TABLE 1 — DESCRIPTIVE STATISTICS WITH 95% CI (n=5 per cell)")
print("=" * 78)
print(f"{'method':18s} {'metric':22s} {'mean':>8s} {'95% CI':>18s} {'SD':>7s}")
print("-" * 78)
for m in methods:
    for col, name in [("api_operation_coverage_pct", "attempted_cov_%"),
                      ("verified_coverage_pct", "verified_cov_%"),
                      ("generation_time_s", "gen_time_s"),
                      ("cce_verified", "CCE_verified")]:
        xs = get(m, col)
        if not xs: continue
        lo, hi = ci95(xs)
        print(f"{m:18s} {name:22s} {mean(xs):>7.2f} "
              f"[{lo:>6.2f}, {hi:>6.2f}] {stdev(xs) if len(xs)>1 else 0:>7.2f}")
    print("-" * 78)

# ── Hypothesis test: does method affect verified coverage? ──
print("\n" + "=" * 78)
print("HYPOTHESIS TEST — H1: Method affects verified coverage")
print("=" * 78)
groups = [get(m, "verified_coverage_pct") for m in methods]
h, p = stats.kruskal(*groups)
print(f"Kruskal-Wallis H = {h:.3f}, p = {p:.4f}")
print("→ " + ("REJECT H0 (methods differ significantly)" if p < 0.05
              else "FAIL TO REJECT H0 (no significant difference at α=0.05)"))

# Pairwise: Schemathesis vs each LLM
print("\nPairwise (Mann-Whitney U, two-sided):")
for llm in ("llm_zero_shot", "llm_few_shot"):
    a = get(llm, "verified_coverage_pct")
    b = get("schemathesis", "verified_coverage_pct")
    u, p = stats.mannwhitneyu(a, b, alternative="two-sided")
    print(f"  {llm:15s} vs schemathesis: U={u:.1f}, p={p:.4f}")

# ── Figure 1: Verified coverage box plot ──
fig, ax = plt.subplots(figsize=(7, 5))
data = [get(m, "verified_coverage_pct") for m in methods]
bp = ax.boxplot(data, tick_labels=[labels[m] for m in methods], patch_artist=True,
                widths=0.6)
for patch, color in zip(bp["boxes"], ["#d62728", "#ff7f0e", "#2ca02c"]):
    patch.set_facecolor(color); patch.set_alpha(0.6)
ax.set_ylabel("Verified coverage (%)")
ax.set_title("Figure 1: Verified operation coverage by method (5 reps)")
ax.grid(axis="y", alpha=0.3)
plt.tight_layout()
plt.savefig(FIG / "fig1_verified_coverage.png", dpi=200)
print(f"\n✅ saved {FIG / 'fig1_verified_coverage.png'}")

# ── Figure 2: Attempted vs Verified gap ──
fig, ax = plt.subplots(figsize=(8, 5))
x = np.arange(len(methods))
att = [mean(get(m, "api_operation_coverage_pct")) for m in methods]
ver = [mean(get(m, "verified_coverage_pct")) for m in methods]
w = 0.35
ax.bar(x - w/2, att, w, label="Attempted", color="#1f77b4", alpha=0.85)
ax.bar(x + w/2, ver, w, label="Verified", color="#d62728", alpha=0.85)
for i, (a, v) in enumerate(zip(att, ver)):
    ax.text(i - w/2, a + 1, f"{a:.1f}%", ha="center", fontsize=9)
    ax.text(i + w/2, v + 1, f"{v:.1f}%", ha="center", fontsize=9)
ax.set_xticks(x); ax.set_xticklabels([labels[m] for m in methods])
ax.set_ylabel("Coverage (%)")
ax.set_title("Figure 2: Attempted vs. verified coverage — the semantic gap")
ax.legend(); ax.grid(axis="y", alpha=0.3)
plt.tight_layout()
plt.savefig(FIG / "fig2_attempted_vs_verified.png", dpi=200)
print(f"✅ saved {FIG / 'fig2_attempted_vs_verified.png'}")

# ── Figure 3: CCE_verified comparison ──
fig, ax = plt.subplots(figsize=(7, 5))
cce = [mean(get(m, "cce_verified")) for m in methods]
bars = ax.bar([labels[m] for m in methods], cce,
              color=["#d62728", "#ff7f0e", "#2ca02c"], alpha=0.85)
for bar, v in zip(bars, cce):
    ax.text(bar.get_x() + bar.get_width()/2, v + 0.5,
            f"{v:.2f}", ha="center", fontsize=10, fontweight="bold")
ax.set_ylabel("CCE_verified (verified% per generation second)")
ax.set_title("Figure 3: Coverage-Cost Efficiency (verified)")
ax.grid(axis="y", alpha=0.3)
plt.tight_layout()
plt.savefig(FIG / "fig3_cce.png", dpi=200)
print(f"✅ saved {FIG / 'fig3_cce.png'}")

print("\n" + "=" * 78)
print("Analysis complete. Figures in results/figures/")
print("=" * 78)
