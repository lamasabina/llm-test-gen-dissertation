"""
reconcile_data.py — Build a clean, reconciled dataset.

Rules:
  - Keep only runs with budget_minutes == 5 (primary comparison).
  - Exclude generation failures (0% attempted AND 0% verified with empty per_test).
  - Keep latest 5 valid runs per method (by timestamp).
  - Set execution_time_s to None for Schemathesis (fused tool).
  - Save to reconciled_results.csv.
  - Save the 15-min Schemathesis run to budget_sensitivity.csv (separate file).
"""
import csv
from collections import defaultdict
from pathlib import Path

src = Path("results/raw/results.csv")
dst = Path("results/raw/reconciled_results.csv")
dst_15m = Path("results/raw/budget_sensitivity.csv")

rows = list(csv.DictReader(open(src)))

# ── Split: 5-min (primary) vs non-5-min (sensitivity) ─────────
primary = []
sensitivity = []
for r in rows:
    if r["budget_minutes"] == "5":
        primary.append(r)
    else:
        sensitivity.append(r)

# ── Filter: remove generation failures from primary ───────────
by_method = defaultdict(list)
excluded = []
for r in primary:
    try:
        attempted = float(r["api_operation_coverage_pct"] or 0)
        verified = float(r["verified_coverage_pct"] or 0)
    except (ValueError, TypeError):
        excluded.append(r)
        print(f"  EXCLUDED (malformed row): {r.get('run_id', '?')}")
        continue
    if attempted == 0 and verified == 0:
        excluded.append(r)
        print(f"  EXCLUDED (generation failure): {r['run_id']}")
        continue
    by_method[r["method"]].append(r)

# ── Keep latest 5 per method ─────────────────────────────────
final = []
for method, m_rows in by_method.items():
    m_rows.sort(key=lambda r: r["timestamp"])
    latest = m_rows[-5:]
    final.extend(latest)
    print(f"{method}: kept {len(latest)} runs (of {len(m_rows)} valid)")

# ── Fix Schemathesis execution_time_s: 0.0 → empty ───────────
fieldnames = list(rows[0].keys())
for r in final:
    if r["method"] == "schemathesis":
        r["execution_time_s"] = ""   # NaN in pandas, "not applicable" in prose

# ── Write primary reconciled CSV ─────────────────────────────
with open(dst, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader()
    w.writerows(final)

# ── Write 15-min sensitivity CSV ─────────────────────────────
with open(dst_15m, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader()
    w.writerows(sensitivity)

print(f"\n✅ Primary dataset (5-min): {dst} — {len(final)} rows")
print(f"✅ Sensitivity (15-min):   {dst_15m} — {len(sensitivity)} rows")
print(f"\nReconciliation summary:")
print(f"  Original rows:                     {len(rows)}")
print(f"  Excluded (generation failure):     {len(excluded)}")
print(f"  Moved to sensitivity (non-5-min):  {len(sensitivity)}")
print(f"  Dropped (kept only latest 5/method): {len(primary) - len(excluded) - len(final)}")
print(f"  Final reconciled rows:             {len(final)}")
