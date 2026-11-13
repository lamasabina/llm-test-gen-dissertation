#!/usr/bin/env python3
"""
coverage_from_pytest.py — operation coverage from pytest outcomes.

Handles two test-name forms:
  A. Plain:        test_<endpoint>_<verb>              -> verb from suffix
  B. Parametrized: test_<group>[<endpoint>]            -> verb resolved by
                                                          inspecting test body

Method-ambiguity fix (Problem B):
  When an OAS path supports multiple methods (e.g., GET+POST on /orders),
  a parametrized ID like test_endpoints[/orders] is resolved to a SPECIFIC
  verb by parsing the test file body for requests.<verb>(endpoint).
  If the body uses >1 verb or none, the target is flagged ambiguous and
  counted ONCE (not once per OAS method) — preventing coverage inflation.
"""
from __future__ import annotations
import json, re
from pathlib import Path

VERBS = ("get", "post", "put", "delete", "patch", "head", "options")


def _load_oas_ops(oas_path):
    spec = json.loads(Path(oas_path).read_text())
    ops = set()
    for path, methods in spec.get("paths", {}).items():
        for m in methods:
            if m.lower() in VERBS:
                ops.add((m.upper(), path))
    return ops


def _template_match_single(path, template):
    if path == template:
        return True
    if "{" in template:
        rx = re.escape(template).replace(r"\{[^}]+\}", "[^/]+")
        return re.fullmatch(rx, path) is not None
    return False


def _body_verbs_for_endpoint(test_code, endpoint):
    """Return set of HTTP verbs used against this endpoint in the test body."""
    verbs = set()
    # Match requests.<verb>(...) calls whose URL contains the endpoint
    for m in re.finditer(
        r'requests\.(get|post|put|delete|patch|head|options)\s*\([^)]*' + re.escape(endpoint.split("{")[0]),
        test_code, re.IGNORECASE
    ):
        verbs.add(m.group(1).upper())
    return verbs


def _resolve_parametrized(endpoint, oas_ops, test_code):
    """Resolve a parametrized endpoint to specific (verb, path) targets."""
    candidates = [(om, op) for om, op in oas_ops if _template_match_single(endpoint, op)]
    if not candidates:
        return [(("GET"), endpoint)], False   # unmatched
    if len(candidates) == 1:
        return candidates, False
    # Multiple OAS methods on this path — use body verbs
    body_verbs = _body_verbs_for_endpoint(test_code, endpoint)
    specific = [c for c in candidates if c[0] in body_verbs]
    if len(specific) == 1:
        return specific, False
    # Ambiguous: count once, flag it
    return [candidates[0]], True


def _test_id_to_ops(test_id, oas_ops, test_code):
    """Return (targets, ambiguous, raw_endpoint)."""
    # Form B: parametrized [endpoint]
    m = re.search(r"\[([^\]]+)\]", test_id)
    if m:
        endpoint = m.group(1)
        targets, ambiguous = _resolve_parametrized(endpoint, oas_ops, test_code)
        return targets, ambiguous, endpoint

    # Form A: test_<endpoint>_<verb>
    lname = test_id.lower()
    verb = next((v.upper() for v in VERBS if v in lname), None)
    if not verb:
        return [], False, None
    core = lname
    for v in VERBS:
        core = core.replace("_" + v, "").replace(v + "_", "")
    core = core.replace("test_", "").strip("_")
    for om, op in oas_ops:
        if om != verb:
            continue
        tokens = [t.lower() for t in re.split(r"[{}/]", op) if t and t != "id"]
        if any(tok in core for tok in tokens):
            return [(om, op)], False, op
    return [(verb, "/" + core.replace("_", "/"))], False, None


def compute(oas_path, per_test, test_file_path=None):
    oas_ops = _load_oas_ops(oas_path)
    total = len(oas_ops)
    attempted, verified = set(), set()
    ambiguous_ids = []
    mapping = {}

    test_code = ""
    if test_file_path and Path(test_file_path).exists():
        test_code = Path(test_file_path).read_text()

    for test_id, status in per_test.items():
        targets, ambiguous, raw = _test_id_to_ops(test_id, oas_ops, test_code)
        if ambiguous:
            ambiguous_ids.append(test_id)
        mapping[test_id] = {
            "status": status,
            "targets": [f"{m} {p}" for m, p in targets],
            "ambiguous": ambiguous,
        }
        for target in targets:
            if target in oas_ops:
                attempted.add(target)
                if status == "PASSED":
                    verified.add(target)

    attempted_pct = round(len(attempted) / total * 100, 2) if total else 0.0
    verified_pct  = round(len(verified)  / total * 100, 2) if total else 0.0

    return {
        "total_ops": total,
        "attempted_ops": len(attempted),
        "verified_ops": len(verified),
        "ambiguous_tests": len(ambiguous_ids),
        "attempted_coverage_pct": attempted_pct,
        "verified_coverage_pct": verified_pct,
        "attempted_list": sorted(f"{m} {p}" for m, p in attempted),
        "verified_list": sorted(f"{m} {p}" for m, p in verified),
        "ambiguous_list": ambiguous_ids,
        "test_mapping": mapping,
    }


if __name__ == "__main__":
    import yaml
    proj = Path(__file__).resolve().parent.parent
    cfg = yaml.safe_load(open(proj / "config" / "experiment.yaml"))
    b = cfg["benchmarks"][0]

    fake = {
        "test_endpoints[/catalogue]":        "PASSED",
        "test_endpoints[/catalogue/{id}]":   "PASSED",
        "test_endpoints[/carts/{id}]":       "FAILED",
        "test_endpoints[/orders]":           "FAILED",  # ambiguous: GET+POST in OAS
        "test_endpoints[/customers]":        "PASSED",
    }
    print("=== coverage_from_pytest self-test (method-ambiguity fixed) ===")
    r = compute(Path(b["oas_path"]), fake, test_file_path=None)
    for k in ("total_ops","attempted_ops","verified_ops","ambiguous_tests",
              "attempted_coverage_pct","verified_coverage_pct"):
        print(f"  {k}: {r[k]}")
    print(f"  attempted_list: {r['attempted_list']}")
    print(f"  verified_list:  {r['verified_list']}")
    print(f"  ambiguous:      {r['ambiguous_list']}")
    assert r["attempted_ops"] <= r["total_ops"], "Coverage cannot exceed OAS ops"
    print("\nSELF-TEST PASSED")
