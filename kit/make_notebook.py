#!/usr/bin/env python3
"""Builds notebook/free_speed_reproduce.ipynb: a CPU-only Kaggle notebook that embeds release/records.csv
(no model text, no competition data) and recomputes the paper's main table from it.
Identity is re-derived from text hashes; speedups from token counts and decode times."""
import base64, gzip, json, os, sys

def cell(kind, src):
    c = {"cell_type": kind, "metadata": {}, "source": src.splitlines(keepends=True)}
    if kind == "code":
        c.update({"outputs": [], "execution_count": None})
    return c

def main():
    rec = sys.argv[1] if len(sys.argv) > 1 else "release/records.csv"
    claims = sys.argv[2] if len(sys.argv) > 2 else "results/claims.json"
    out = sys.argv[3] if len(sys.argv) > 3 else "notebook/free_speed_reproduce.ipynb"
    title = sys.argv[4] if len(sys.argv) > 4 else "Free Speed: reproduce every number"
    blob = base64.b64encode(gzip.compress(open(rec, "rb").read())).decode()
    cl = json.load(open(claims))
    keep = {k: v for k, v in cl.items() if k.endswith((".ALL.speedup", ".ALL.identity_rate", ".ALL.n_pairs"))}
    code1 = ("import base64, gzip, io, csv, json\n"
             "BLOB = '''%s'''\n"
             "rows = list(csv.DictReader(io.StringIO(gzip.decompress(base64.b64decode(BLOB)).decode())))\n"
             "PAPER = json.loads('''%s''')\n"
             "print(len(rows), 'records')\n" % (blob, json.dumps(keep)))
    code2 = '''base = {(r["tag"], r["target"], r["id"]): r for r in rows if r["config"] == "baseline"}
groups = {}
for r in rows:
    if r["config"] == "baseline":
        continue
    b = base.get((r["tag"], r["target"], r["id"]))
    if b:
        groups.setdefault((r["tag"], r["target"], r["config"]), []).append((b, r))
table, bad = [], 0
for (tag, target, config), P in sorted(groups.items()):
    n = len(P)
    ident = sum(b["text_sha256"] == r["text_sha256"] for b, r in P) / n
    bn = sum(float(b["predicted_n"]) for b, r in P); bms = sum(float(b["predicted_ms"]) for b, r in P)
    cn = sum(float(r["predicted_n"]) for b, r in P); cms = sum(float(r["predicted_ms"]) for b, r in P)
    sp = (cn / cms) / (bn / bms)
    table.append((tag, target, config, n, ident, sp))
    key = "%s.%s.%s.ALL." % (tag, target, config)
    for name, val, tol in (("speedup", sp, 0.01), ("identity_rate", ident, 1e-9), ("n_pairs", n, 0)):
        if key + name in PAPER and abs(PAPER[key + name] - val) > tol:
            bad += 1; print("MISMATCH", key + name, PAPER[key + name], val)
print("%-8s %-5s %-16s %5s %10s %8s" % ("tag", "model", "config", "n", "identical", "speedup"))
for t in table:
    print("%-8s %-5s %-16s %5d %9.1f%% %7.2fx" % (t[0], t[1], t[2], t[3], 100 * t[4], t[5]))
print("ALL PAPER NUMBERS REPRODUCED" if bad == 0 else "%d MISMATCHES" % bad)
'''
    code3 = '''import matplotlib.pyplot as plt
show = [t for t in table if not t[2].startswith("baseline")]
plt.figure(figsize=(max(6, len(show)), 4))
plt.bar(range(len(show)), [t[5] for t in show]); plt.axhline(1, color="k", ls="--")
plt.xticks(range(len(show)), ["%s\\n%s\\n%s" % t[:3] for t in show], fontsize=7)
plt.ylabel("Decode speedup vs baseline"); plt.tight_layout(); plt.show()
'''
    nb = {"cells": [cell("markdown", "# %s\n\nCPU only, no model, no competition data. The embedded table has one row per "
                         "(experiment, model, decoding config, prompt): token counts, decode milliseconds and a SHA-256 of the "
                         "model output. The cells below rebuild the paper's main table and check it against the paper's numbers.\n" % title),
                    cell("code", code1), cell("code", code2), cell("code", code3)],
          "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                       "language_info": {"name": "python"}}, "nbformat": 4, "nbformat_minor": 5}
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    json.dump(nb, open(out, "w"), indent=1)
    print("[notebook] wrote %s (%d KB)" % (out, os.path.getsize(out) // 1024))

if __name__ == "__main__":
    main()
