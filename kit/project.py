#!/usr/bin/env python3
"""Projection, clearly labelled as an upper bound: if a speedup s lets an agent make more attempts in the
same wall-clock budget, how many more public dev tasks could be resolved with oracle selection among attempts?
Uses the Many Labs pooled outcomes (Apache-2.0): attempts.csv (task, y, model) and tasks.csv (audit_status)."""
import argparse, csv, json, math

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--attempts", required=True); ap.add_argument("--tasks", required=True)
    ap.add_argument("--speedup", type=float, required=True); ap.add_argument("--out", required=True)
    a = ap.parse_args()
    valid = {r["task"] for r in csv.DictReader(open(a.tasks)) if r.get("audit_status") == "valid"}
    out = {"speedup_used": a.speedup}
    for model in ("31B", "E4B"):
        per = {}
        for r in csv.DictReader(open(a.attempts)):
            if r.get("model") == model and r["task"] in valid:
                try: per.setdefault(r["task"], []).append(float(r["y"]))
                except ValueError: pass
        p = [sum(v) / len(v) for v in per.values() if v]
        if not p: continue
        def rate(k): return sum(1 - (1 - x) ** k for x in p) / len(p)
        k0, frac = int(math.floor(a.speedup)), a.speedup - math.floor(a.speedup)
        proj = (1 - frac) * rate(max(1, k0)) + frac * rate(max(1, k0) + 1) if a.speedup >= 1 else rate(1)
        out["proj.%s.n_valid_tasks" % model] = len(p)
        out["proj.%s.single_attempt_rate" % model] = rate(1)
        out["proj.%s.two_attempt_oracle_rate" % model] = rate(2)
        out["proj.%s.rate_at_measured_speedup_oracle" % model] = proj
    json.dump(out, open(a.out, "w"), indent=1, sort_keys=True)
    print(json.dumps(out, indent=1, sort_keys=True))

if __name__ == "__main__":
    main()
