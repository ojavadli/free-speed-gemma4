#!/usr/bin/env python3
"""Fills {{claim.key}} or {{claim.key|.2f}} or {{claim.key|pct}} placeholders from results/claims.json.
Exits 1 and lists every missing key, so no number in the paper is typed by hand."""
import json, re, sys

def main():
    tpl, claims_path, out = sys.argv[1], sys.argv[2], sys.argv[3]
    claims = json.load(open(claims_path))
    text = open(tpl, encoding="utf-8").read()
    missing = []
    def rep(m):
        key, fmt = m.group(1).strip(), (m.group(2) or "").strip()
        if key not in claims:
            missing.append(key); return m.group(0)
        v = claims[key]
        if fmt == "pct":
            return "%.1f%%" % (100 * float(v))
        if fmt:
            return format(float(v), fmt)
        return str(v)
    text = re.sub(r"\{\{\s*([^}|]+?)\s*(?:\|\s*([^}]+?)\s*)?\}\}", rep, text)
    open(out, "w", encoding="utf-8").write(text)
    words = len(re.findall(r"\S+", text))
    print("[fill] wrote %s, %d words" % (out, words))
    if missing:
        print("[fill] MISSING KEYS:\n  " + "\n  ".join(sorted(set(missing)))); sys.exit(1)

if __name__ == "__main__":
    main()
