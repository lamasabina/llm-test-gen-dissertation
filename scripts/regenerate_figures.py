import csv
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

PROJ = Path.cwd()
CSV = PROJ / "results" / "raw" / "results.csv"
FIG = PROJ / "results" / "figures"

rows = list(csv.DictReader(open(CSV)))
methods = ["llm_zero_shot", "llm_few_shot", "schemathesis"]
labels = {"llm_zero_shot": "LLM\nzero-shot", "llm_few_shot": "LLM\nfew-shot", "schemathesis": "Schemathesis"}

def get(m, col):
    return [float(r[col]) for r in rows if r["method"] == m and r[col] not in ("", "None")]

# ── Figure 1: Dot/Strip Plot ──
fig, ax = plt.subplots(figsize=(7, 5))
for i, m in enumerate(methods):
    y = get(m, "verified_coverage_pct")
    x = np.random.normal(i, 0.04, size=len(y)) # Jitter to prevent overlap
    ax.plot(x, y, 'o', markersize=8, color=["#d62728", "#ff7f0e", "#2ca02c"][i], alpha=0.7, label=labels[m])
    # Add a horizontal line for the mean
    ax.hlines(np.mean(y), i-0.15, i+0.15, colors='black', lw=2, label='Mean' if i==0 else "")

ax.set_xticks(range(len(methods)))
ax.set_xticklabels([labels[m] for m in methods])
ax.set_ylabel("Verified coverage (%)")
ax.set_title("Figure 1: Verified operation coverage (5 repetitions)")
ax.grid(axis="y", alpha=0.3)
plt.tight_layout()
plt.savefig(FIG / "fig1_verified_coverage.png", dpi=200)
print("✅ Figure 1 regenerated (strip plot)")

# ── Figure 3: CCE with Log Scale ──
fig, ax = plt.subplots(figsize=(7, 5))
cce = [np.mean(get(m, "cce_verified")) for m in methods]
# Replace exact 0 with a tiny number for log scale, but label it 0
plot_cce = [max(val, 0.01) for val in cce] 
bars = ax.bar([labels[m] for m in methods], plot_cce, color=["#d62728", "#ff7f0e", "#2ca02c"], alpha=0.85)

for bar, v, pv in zip(bars, cce, plot_cce):
    ax.text(bar.get_x() + bar.get_width()/2, pv * 1.1, f"{v:.2f}", ha="center", fontsize=11, fontweight="bold")

ax.set_yscale('symlog', linthresh=0.1) # Log scale handles 0 gracefully
ax.set_ylabel("CCE_verified (verified% / generation second) [Log Scale]")
ax.set_title("Figure 3: Coverage-Cost Efficiency")
ax.grid(axis="y", alpha=0.3)
plt.tight_layout()
plt.savefig(FIG / "fig3_cce.png", dpi=200)
print("✅ Figure 3 regenerated (symlog scale)")
