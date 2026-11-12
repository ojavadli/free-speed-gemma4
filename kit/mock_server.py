#!/usr/bin/env python3
"""Tiny fake llama-server for the kit self-test only. Never use its numbers in the paper."""
import hashlib, json, sys
from http.server import BaseHTTPRequestHandler, HTTPServer

ARGS = sys.argv[1:]
PORT = int(ARGS[ARGS.index("--port") + 1]) if "--port" in ARGS else 8089
SPEC = ARGS[ARGS.index("--spec-type") + 1] if "--spec-type" in ARGS else "none"
MS = 40.0
if "draft-mtp" in SPEC: MS *= 0.62
if "ngram" in SPEC: MS *= 0.80
DIVERGE = "--mock-diverge" in ARGS


class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _send(self, obj, code=200):
        b = json.dumps(obj).encode()
        self.send_response(code); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        self._send({"status": "ok"})
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        msgs = body.get("messages") or [{"role": "user", "content": body.get("prompt", "")}]
        key = hashlib.sha256(json.dumps(msgs, sort_keys=True).encode()).hexdigest()
        h = int(key[:8], 16)
        n_assist = sum(1 for m in msgs if m["role"] == "assistant")
        if "Tools:" in msgs[0].get("content", ""):
            calls = ['{"tool": "search", "args": {"pattern": "def ", "glob": "*.py"}}',
                     '{"tool": "read_file", "args": {"path": "setup.py", "start": 1, "end": 20}}',
                     '{"tool": "submit", "args": {}}']
            content = "```json\n%s\n```" % calls[min(n_assist, 2)]
            reasoning = "thinking " * (5 + h % 20)
        else:
            content = "<<<<<<< SEARCH\n" + "line %d\n" % h * (3 + h % 9) + "=======\nfixed\n>>>>>>> REPLACE"
            reasoning = ""
        if DIVERGE and h % 7 == 0:
            content += "\n# diverged"
        n = len((reasoning + content).split())
        ms = n * MS * (1 + ((h >> 8) % 100) / 1000.0)
        timings = {"prompt_n": 100 + h % 50, "prompt_ms": 50.0, "predicted_n": n, "predicted_ms": ms,
                   "predicted_per_second": n / ms * 1000}
        if SPEC != "none":
            timings.update({"draft_n": n, "draft_n_accepted": int(n * 0.7)})
        if self.path.endswith("/completion"):
            self._send({"content": content, "tokens": list(range(n)), "timings": timings, "stop_type": "eos"})
        else:
            self._send({"choices": [{"message": {"role": "assistant", "content": content, "reasoning_content": reasoning},
                                     "finish_reason": "stop"}], "usage": {"completion_tokens": n}, "timings": timings})

HTTPServer(("127.0.0.1", PORT), H).serve_forever()
