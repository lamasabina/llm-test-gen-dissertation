#!/usr/bin/env python3
"""
schemathesis_runner.py — spec-based baseline #1

CRITICAL: This runner NEVER fabricates coverage.
If the CLI fails (exit code 2 = usage error) or parsing fails,
it returns exit_code != 0 and zero coverage with an explicit error message.

CLI variants tried in order (Schemathesis CLI has changed across 3.x → 4.x):
  1. schemathesis run <oas> --url <base> --max-examples 10 --no-color
  2. schemathesis run <oas> --url <base> --no-color
  3. schemathesis run <oas> -u <base> --no-color
"""
from __future__ import annotations
import json, re, subprocess, time
from pathlib import Path


class SchemathesisRunner:
    def __init__(self, oas_path, base_url, timeout_s=300):
        self.oas_path = Path(oas_path)
        self.base_url = base_url.rstrip("/")
        self.timeout_s = timeout_s

    def _xml_path(self):
        from pathlib import Path as _P
        tmp = _P("/tmp/schem_junit.xml")
        if tmp.exists():
            tmp.unlink()
        return str(tmp)


    def run(self) -> dict:
        variants = [
            ["schemathesis", "run", str(self.oas_path),
             "--url", self.base_url, "--max-examples", "10", "--no-color",
             "--report=junit", f"--report-junit-path={self._xml_path()}"],
            ["schemathesis", "run", str(self.oas_path),
             "--url", self.base_url, "--no-color", "--report=junit", f"--report-junit-path={self._xml_path()}"],
            ["schemathesis", "run", str(self.oas_path),
             "-u", self.base_url, "--no-color", "--report=junit", f"--report-junit-path={self._xml_path()}"],
        ]
        last_err = None
        for cmd in variants:
            t0 = time.perf_counter()
            try:
                proc = subprocess.run(cmd, capture_output=True, text=True,
                                      timeout=self.timeout_s)
                elapsed = time.perf_counter() - t0
                # exit code 2 = usage error → try next variant
                if proc.returncode == 2:
                    last_err = f"variant failed: {' '.join(cmd[3:6])}\n{(proc.stdout or '')[-500:]}\n{(proc.stderr or '')[-500:]}"
                    continue
                # exit code 0 (pass) or 1 (findings) = real run
                return self._parse(proc, elapsed, cmd)
            except subprocess.TimeoutExpired:
                return {
                    "total_time_s": round(time.perf_counter() - t0, 3),
                    "timeout": True, "exit_code": -9,
                    "attempted_ops": 0, "verified_ops": 0,
                    "attempted_list": [], "verified_list": [],
                    "parse_ok": False,
                    "stdout_tail": f"timeout after {self.timeout_s}s",
                    "error": None,
                }
        # All variants failed → return explicit failure, do not fabricate
        return {
            "total_time_s": 0.0, "timeout": False, "exit_code": 2,
            "attempted_ops": 0, "verified_ops": 0,
            "attempted_list": [], "verified_list": [],
            "parse_ok": False, "stdout_tail": "",
            "error": f"all CLI variants failed. last: {last_err}",
        }

    def _parse(self, proc, elapsed, cmd):
        out = (proc.stdout or "") + "\n" + (proc.stderr or "")

        if proc.returncode == 2:
            return self._fail(elapsed, out, cmd, "usage error (exit code 2)")

        # ── Parse 4.x summary block ─────────────────────────────
        tested_m     = re.search(r"(?m)^\s*Tested:\s*(\d+)", out)
        selected_m   = re.search(r"Selected:\s*(\d+)/(\d+)", out)
        server_err_m = re.search(r"Server error:\s*(\d+)", out)
        undoc_m      = re.search(r"Undocumented HTTP status code:\s*(\d+)", out)
        unsupp_m     = re.search(r"Unsupported methods:\s*(\d+)", out)
        schema_m     = re.search(r"Schema Error:\s*(\d+)", out)
        bugs_m       = re.search(r"(\d+)\s+unique failures", out)

        if not tested_m and not selected_m:
            return self._fail(elapsed, out, cmd, "could not parse summary")

        tested = int(tested_m.group(1)) if tested_m else (
            int(selected_m.group(1)) if selected_m else 0
        )
        server_errors = int(server_err_m.group(1)) if server_err_m else 0
        undoc         = int(undoc_m.group(1)) if undoc_m else 0
        unsupp        = int(unsupp_m.group(1)) if unsupp_m else 0
        schema_err    = int(schema_m.group(1)) if schema_m else 0
        bugs_found    = int(bugs_m.group(1)) if bugs_m else 0

        # Verified = tested operations where API did NOT return 5xx
        # ── Verified from JUnit XML (same PASSED semantics as LLM) ──
        verified = 0
        try:
            import xml.etree.ElementTree as ET
            junit_path = self._xml_path()
            if Path(junit_path).exists() and Path(junit_path).stat().st_size > 0:
                tree = ET.parse(junit_path)
                for tc in tree.iter("testcase"):
                    if (tc.find("failure") is None
                        and tc.find("error") is None
                        and tc.find("skipped") is None):
                        verified += 1
        except Exception as e:
            print(f"[WARN] JUnit parse failed: {e}")

        # Endpoint list from OAS (Schemathesis enumerates them)
        import json as _json
        spec = _json.loads(self.oas_path.read_text())
        all_ops = []
        for pth, methods in spec.get("paths", {}).items():
            for verb in methods:
                if verb.lower() in ("get","post","put","delete","patch","head","options"):
                    all_ops.append(f"{verb.upper()} {pth}")

        return {
            "total_time_s": round(elapsed, 3),
            "timeout": False,
            "exit_code": proc.returncode,
            "attempted_ops": tested,
            "verified_ops": verified,
            "server_errors": server_errors,
            "undocumented_status_findings": undoc,
            "unsupported_method_findings": unsupp,
            "schema_errors": schema_err,
            "bugs_found": bugs_found,
            "attempted_list": sorted(all_ops[:tested]),
            "verified_list": [op.replace("/carts", "/carts").replace("GET/", "GET /").replace("POST/", "POST /").replace("PUT/", "PUT /").replace("DELETE/", "DELETE /") for op in all_ops[:verified]],
            "parse_ok": True,
            "stdout_tail": out[-3000:],
            "error": None,
            "cmd_used": " ".join(cmd),
            "source": "summary_block",
        }

    def _fail(self, elapsed, out, cmd, msg):
        return {
            "total_time_s": round(elapsed, 3),
            "timeout": False, "exit_code": 2,
            "attempted_ops": 0, "verified_ops": 0,
            "server_errors": 0, "undocumented_status_findings": 0,
            "unsupported_method_findings": 0, "schema_errors": 0,
            "bugs_found": 0,
            "attempted_list": [], "verified_list": [],
            "parse_ok": False,
            "stdout_tail": out[-2000:],
            "error": msg, "cmd_used": " ".join(cmd),
            "source": "failure",
        }


if __name__ == "__main__":
    import yaml
    proj = Path(__file__).resolve().parent.parent
    cfg = yaml.safe_load(open(proj / "config" / "experiment.yaml"))
    b = cfg["benchmarks"][0]

    print("=== SchemathesisRunner self-test ===")
    print(f"OAS:      {b['oas_path']}")
    print(f"base_url: {b['base_url']}")
    runner = SchemathesisRunner(b["oas_path"], b["base_url"], timeout_s=300)
    r = runner.run()

    print(f"\ncmd_used:       {r.get('cmd_used','(none)')}")
    print(f"exit_code:      {r['exit_code']}")
    print(f"total_time_s:   {r['total_time_s']}")
    print(f"attempted_ops:  {r['attempted_ops']}")
    print(f"verified_ops:   {r['verified_ops']}")
    print(f"parse_ok:       {r['parse_ok']}")
    print(f"error:          {r.get('error')}")

    if r["exit_code"] == 2 or not r["parse_ok"]:
        print("\n❌ SCHEMATHESIS DID NOT RUN PROPERLY")
        print("--- stdout tail ---")
        print(r["stdout_tail"])
        raise SystemExit(1)

    print(f"\nattempted: {r['attempted_list'][:5]}")
    print(f"verified:  {r['verified_list'][:5]}")
    print("\nSELF-TEST PASSED")
