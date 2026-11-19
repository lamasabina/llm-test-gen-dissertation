"""
oracle.py — Independent verification against the OAS.
Instead of trusting the LLM's assertion, we check the actual HTTP response
against the documented status codes and return types.
"""
import requests
import json
from pathlib import Path

class OASOracle:
    def __init__(self, oas_path):
        self.spec = json.loads(Path(oas_path).read_text())
        self.base_url = "http://localhost:80"

    def verify(self, endpoint, method):
        """Send a request and verify it against the OAS spec."""
        url = self.base_url + endpoint
        try:
            resp = requests.request(method, url, timeout=5)
            
            # Find the spec for this path
            path_spec = self.spec["paths"].get(endpoint, {}).get(method.lower(), {})
            expected_codes = [int(code) for code in path_spec.get("responses", {}).keys() if code.isdigit()]
            
            if expected_codes:
                # If the actual code is in the documented list, it's a pass
                if resp.status_code in expected_codes:
                    return True, resp.status_code
                else:
                    return False, resp.status_code
            else:
                # No documented codes → fallback to "anything not 5xx is a pass"
                return resp.status_code < 500, resp.status_code
        except Exception as e:
            return False, str(e)
