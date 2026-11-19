import sys
import datetime
sys.path.insert(0, "scripts")
from experiment_runner import ExperimentRunner

def log(msg):
    print(msg)
    with open("live_proof.txt", "a") as f:
        f.write(msg + "\n")

log("="*70)
log(f"LIVE EXPERIMENT EXECUTION LOG - {datetime.datetime.now()}")
log("="*70)

r = ExperimentRunner()

# 1. Run fresh LLM Zero-Shot to prove variance
log("\n[ACTION] Running 3 fresh LLM zero-shot experiments to prove variance...")
for rep in range(11, 14):
    log(f"\n--- LLM Zero-Shot Rep {rep} ---")
    row = r.run_one(method="llm_zero_shot", benchmark="sock-shop", budget_min=5, rep=rep)
    log(f"Generated in {row['generation_time_s']}s | Tokens: {row['prompt_tokens']}+{row['completion_tokens']} | Coverage: {row['api_operation_coverage_pct']}%")

# 2. Run fresh LLM Few-Shot
log("\n[ACTION] Running 1 fresh LLM few-shot experiment...")
log(f"\n--- LLM Few-Shot Rep 11 ---")
row = r.run_one(method="llm_few_shot", benchmark="sock-shop", budget_min=5, rep=11)
log(f"Generated in {row['generation_time_s']}s | Tokens: {row['prompt_tokens']}+{row['completion_tokens']} | Coverage: {row['api_operation_coverage_pct']}%")

# 3. Run Schemathesis with 15-minute budget
log("\n[ACTION] Running Schemathesis with a 15-MINUTE budget (Rep 2)...")
log("(This proves we CAN run extended budgets; it will fuzz deeper)")
log(f"\n--- Schemathesis 15-min Budget ---")
row = r.run_one(method="schemathesis", benchmark="sock-shop", budget_min=15, rep=2)
log(f"Executed in {row['generation_time_s']}s | Attempted: {row['api_operation_coverage_pct']}% | Verified: {row['verified_coverage_pct']}%")

log("\n" + "="*70)
log("LIVE PROOF COMPLETE. Data appended to results/raw/results.csv")
log("="*70)
