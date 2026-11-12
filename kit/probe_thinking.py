#!/usr/bin/env python3
"""Finds request settings that switch Gemma 4 thinking ON and OFF on this llama-server build.
Writes env/req_think.json and env/req_nothink.json and prints what it saw. Launches the baseline server itself."""
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fs_common import http_json, load_cfg, server_for, chat_payload, parse_chat

Q = [{"role": "system", "content": "You are a careful engineer."},
     {"role": "user", "content": "A function returns len(x)-1 for an empty list and a later index lookup crashes. "
                                 "Work out the cause, then state the fix in one sentence."}]
THINK = [{"chat_template_kwargs": {"enable_thinking": True}}, {"_system_prefix": "<|think|>"}, {}]
NOTHINK = [{"chat_template_kwargs": {"enable_thinking": False}}, {}]

def has_thought(content, reasoning):
    return len(reasoning) > 40 or "<|channel>" in content or content.lstrip().lower().startswith("thought")

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--cfg", default="configs.json"); ap.add_argument("--target", required=True)
    a = ap.parse_args()
    srv, _ = server_for(load_cfg(a.cfg), a.target, "baseline")
    srv.start(); os.makedirs("env", exist_ok=True); chosen = {}
    try:
        for name, cands, want in (("think", THINK, True), ("nothink", NOTHINK, False)):
            for extra in cands:
                try:
                    c, r, fin, t, u = parse_chat(http_json("http://127.0.0.1:%d/v1/chat/completions" % srv.port, chat_payload(Q, 400, extra), 300))
                except Exception as e:
                    print("%-8s %-55s ERROR %s" % (name, json.dumps(extra), e)); continue
                th = has_thought(c, r)
                print("%-8s %-55s reasoning_chars=%d content_chars=%d thought=%s n=%s | %r" %
                      (name, json.dumps(extra), len(r), len(c), th, t.get("predicted_n"), (r or c)[:70]))
                if name not in chosen and th == want and (c.strip() or r.strip()):
                    chosen[name] = extra
        for name in ("think", "nothink"):
            if name in chosen:
                json.dump(chosen[name], open("env/req_%s.json" % name, "w"))
                print("WROTE env/req_%s.json = %s" % (name, json.dumps(chosen[name])))
            else:
                print("NO WORKING SETTING for %s: see the failure playbook" % name)
    finally:
        srv.stop()

if __name__ == "__main__":
    main()
