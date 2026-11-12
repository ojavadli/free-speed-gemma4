#!/usr/bin/env python3
"""FREE SPEED analysis: pairs every config with the baseline on the same prompt.

Writes results/tables/summary.csv, results/tables/pairs.csv, results/claims.json,
release/records.csv (no model text, safe to publish) and figures/*.png.
Headline speedup = ratio of tokens per second (config / baseline) over paired prompts.
Intervals: 2,000 bootstrap resamples of clusters (tasks). Identity: Wilson 95% interval.
"""
import argparse, csv, glob, hashlib, json, math, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fs_common import read_jsonl

BASE = "baseline"


def full_text(r):
    return (r.get("reasoning") or "") + "\n<<<ANSWER>>>\n" + (r.get("content") or "")


def identical(a, b):
    if a.get("tokens") and b.get("tokens"):
        return a["tokens"] == b["tokens"]
    return full_text(a) == full_text(b)


def first_diff(a, b):
    n = min(len(a), len(b))
    for i in range(n):
        if a[i] != b[i]:
            return i
    return n


def wilson(k, n):
    if n == 0:
        return (float("nan"), float("nan"))
    z, p = 1.96, k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def _by_cluster(pairs):
    d = {}
    for p in pairs:
        d.setdefault(p["cluster"], []).append(bool(p["identical"]))
    return d


def tps_ratio(pairs):
    bn = sum(p["b_n"] for p in pairs); bms = sum(p["b_ms"] for p in pairs)
    cn = sum(p["c_n"] for p in pairs); cms = sum(p["c_ms"] for p in pairs)
    if not (bn and bms and cn and cms):
        return float("nan")
    return (cn / cms) / (bn / bms)


def boot_ci(pairs, B=2000, seed=0):
    by = {}
    for p in pairs:
        by.setdefault(p["cluster"], []).append(p)
    keys = sorted(by)
    if len(keys) < 2:
        return (float("nan"), float("nan"))
    arr = np.array([[sum(q["b_n"] for q in by[k]), sum(q["b_ms"] for q in by[k]),
                     sum(q["c_n"] for q in by[k]), sum(q["c_ms"] for q in by[k])] for k in keys], dtype=float)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(keys), size=(B, len(keys)))
    s = arr[idx].sum(axis=1)
    ok = (s[:, 0] > 0) & (s[:, 1] > 0) & (s[:, 2] > 0) & (s[:, 3] > 0)
    r = (s[ok, 2] / s[ok, 3]) / (s[ok, 0] / s[ok, 1])
    return (float(np.percentile(r, 2.5)), float(np.percentile(r, 97.5)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default="results/raw")
    ap.add_argument("--out", default="results")
    ap.add_argument("--release", default="release")
    ap.add_argument("--figs", default="figures")
    a = ap.parse_args()
    for d in (os.path.join(a.out, "tables"), a.release, a.figs):
        os.makedirs(d, exist_ok=True)

    recs = {}
    for path in sorted(glob.glob(os.path.join(a.raw, "*.jsonl"))):
        for r in read_jsonl(path):
            if r.get("ok") and r.get("predicted_n") and r.get("predicted_ms"):
                recs[(r["tag"], r["target"], r["config"], r["id"])] = r  # last write wins
    if not recs:
        sys.exit("no usable records under %s" % a.raw)

    pairs = []
    for (tag, target, config, rid), r in recs.items():
        if config == BASE:
            continue
        b = recs.get((tag, target, BASE, rid))
        if not b:
            continue
        ta, tb = full_text(r), full_text(b)
        same = identical(r, b)
        fd = -1 if same else first_diff(tb, ta)
        pairs.append({
            "tag": tag, "target": target, "config": config, "id": rid, "cluster": r.get("cluster", rid),
            "kind": r.get("kind", "na"), "identical": int(same),
            "first_diff_frac": -1.0 if same else round(fd / max(1, len(tb)), 4),
            "b_n": b["predicted_n"], "b_ms": b["predicted_ms"], "c_n": r["predicted_n"], "c_ms": r["predicted_ms"],
            "b_prompt_ms": b.get("prompt_ms") or 0.0, "c_prompt_ms": r.get("prompt_ms") or 0.0,
            "draft_n": r.get("draft_n") or 0, "draft_acc": r.get("draft_n_accepted") or 0,
            "speedup": (r["predicted_n"] / r["predicted_ms"]) / (b["predicted_n"] / b["predicted_ms"]),
            "think_share": round(len(b.get("reasoning") or "") / max(1, len(tb)), 3),
        })

    with open(os.path.join(a.out, "tables", "pairs.csv"), "w", newline="") as f:
        if pairs:
            w = csv.DictWriter(f, fieldnames=list(pairs[0].keys()))
            w.writeheader(); w.writerows(pairs)

    summary, claims = [], {}
    groups = sorted({(p["tag"], p["target"], p["config"]) for p in pairs})
    for (tag, target, config) in groups:
        G = [p for p in pairs if (p["tag"], p["target"], p["config"]) == (tag, target, config)]
        kinds = ["ALL"] + sorted({p["kind"] for p in G})
        for kind in kinds:
            P = G if kind == "ALL" else [p for p in G if p["kind"] == kind]
            if not P:
                continue
            n, k = len(P), sum(p["identical"] for p in P)
            lo, hi = wilson(k, n)
            sp = tps_ratio(P); slo, shi = boot_ci(P)
            ident = [p for p in P if p["identical"]]
            sp_id = tps_ratio(ident) if ident else float("nan")
            dn, da = sum(p["draft_n"] for p in P), sum(p["draft_acc"] for p in P)
            e2e_b = sum(p["b_ms"] + p["b_prompt_ms"] for p in P); e2e_c = sum(p["c_ms"] + p["c_prompt_ms"] for p in P)
            row = {
                "tag": tag, "target": target, "config": config, "kind": kind, "n_pairs": n,
                "n_clusters": len({p["cluster"] for p in P}),
                "n_identical": k, "identity_rate": k / n, "identity_lo": lo, "identity_hi": hi,
                "speedup": sp, "speedup_lo": slo, "speedup_hi": shi, "speedup_identical_only": sp_id,
                "median_prompt_speedup": float(np.median([p["speedup"] for p in P])),
                "share_slower": float(np.mean([p["speedup"] < 1.0 for p in P])),
                "base_tps": sum(p["b_n"] for p in P) / sum(p["b_ms"] for p in P) * 1000,
                "cfg_tps": sum(p["c_n"] for p in P) / sum(p["c_ms"] for p in P) * 1000,
                "accept_rate": (da / dn) if dn else float("nan"),
                "e2e_speedup_with_prefill": (e2e_b / e2e_c) if e2e_c else float("nan"),
                "clusters_all_identical_rate": float(np.mean([all(v) for v in _by_cluster(P).values()])),
                "mean_think_share": float(np.mean([p["think_share"] for p in P])),
                "gen_seconds_saved_per_100_steps": (sum(p["b_ms"] - p["c_ms"] for p in ident) / max(1, len(ident))) / 10.0,
            }
            summary.append(row)
            for key, val in row.items():
                if key not in ("tag", "target", "config", "kind"):
                    claims["%s.%s.%s.%s.%s" % (tag, target, config, kind, key)] = val

    with open(os.path.join(a.out, "tables", "summary.csv"), "w", newline="") as f:
        if summary:
            w = csv.DictWriter(f, fieldnames=list(summary[0].keys()))
            w.writeheader(); w.writerows(summary)
    # baseline determinism control: any config named baseline_rerun is compared like the others,
    # so its identity_rate is the noise floor for "identical output".
    counts = {}
    for (tag, target, config, rid) in recs:
        counts["%s.%s.%s.n_records" % (tag, target, config)] = counts.get("%s.%s.%s.n_records" % (tag, target, config), 0) + 1
    claims.update(counts)
    with open(os.path.join(a.out, "claims.json"), "w") as f:
        json.dump(claims, f, indent=1, sort_keys=True)

    with open(os.path.join(a.release, "records.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["tag", "target", "config", "id", "cluster", "kind", "block", "order_pos", "predicted_n", "predicted_ms",
                    "prompt_n", "prompt_ms", "draft_n", "draft_n_accepted", "finish", "text_sha256", "text_len"])
        for (tag, target, config, rid), r in sorted(recs.items()):
            t = full_text(r)
            w.writerow([tag, target, config, rid, r.get("cluster", rid), r.get("kind", "na"), r.get("block", ""),
                        r.get("order_pos", ""), r["predicted_n"], round(r["predicted_ms"], 2), r.get("prompt_n", 0),
                        round(r.get("prompt_ms") or 0.0, 2), r.get("draft_n") or 0, r.get("draft_n_accepted") or 0,
                        r.get("finish", ""), hashlib.sha256(t.encode()).hexdigest(), len(t)])

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        allrows = [s for s in summary if s["kind"] == "ALL" and not s["config"].startswith("baseline")]
        if allrows:
            fig, ax = plt.subplots(figsize=(max(7, 0.9 * len(allrows) + 3), 4.2))
            labels = ["%s\n%s\n%s" % (s["tag"], s["target"], s["config"]) for s in allrows]
            y = [s["speedup"] for s in allrows]
            err = [[max(0, s["speedup"] - s["speedup_lo"]) if s["speedup_lo"] == s["speedup_lo"] else 0 for s in allrows],
                   [max(0, s["speedup_hi"] - s["speedup"]) if s["speedup_hi"] == s["speedup_hi"] else 0 for s in allrows]]
            ax.bar(range(len(y)), y, yerr=err, capsize=3, color="#3b6fb6")
            ax.axhline(1.0, color="k", lw=1, ls="--")
            ax.set_xticks(range(len(y))); ax.set_xticklabels(labels, fontsize=7)
            ax.set_ylabel("Decode speedup vs baseline (tokens/s ratio)")
            ax.set_title("Same model, same prompts: speedup with 95% bootstrap CI")
            fig.tight_layout(); fig.savefig(os.path.join(a.figs, "fig_speedup.png"), dpi=180); plt.close(fig)
        kr = [s for s in summary if s["kind"] != "ALL" and not s["config"].startswith("baseline")]
        if kr:
            fig, ax = plt.subplots(figsize=(max(7, 0.7 * len(kr) + 3), 4.2))
            ax.bar(range(len(kr)), [s["speedup"] for s in kr], color="#2a9d8f")
            ax.axhline(1.0, color="k", lw=1, ls="--")
            ax.set_xticks(range(len(kr)))
            ax.set_xticklabels(["%s\n%s\n%s\n%s" % (s["tag"], s["target"], s["config"], s["kind"]) for s in kr], fontsize=6)
            ax.set_ylabel("Decode speedup"); ax.set_title("Speedup by agent step type")
            fig.tight_layout(); fig.savefig(os.path.join(a.figs, "fig_by_kind.png"), dpi=180); plt.close(fig)
        if pairs:
            fig, ax = plt.subplots(figsize=(6.5, 4.2))
            for (tag, target, config) in groups:
                if config.startswith("baseline"):
                    continue
                v = np.sort([p["speedup"] for p in pairs if (p["tag"], p["target"], p["config"]) == (tag, target, config)])
                ax.plot(v, np.arange(1, len(v) + 1) / len(v), label="%s %s %s" % (tag, target, config))
            ax.axvline(1.0, color="k", lw=1, ls="--"); ax.set_xlabel("Per-prompt speedup"); ax.set_ylabel("Share of prompts")
            ax.legend(fontsize=6); ax.set_title("Distribution of per-prompt speedups")
            fig.tight_layout(); fig.savefig(os.path.join(a.figs, "fig_ecdf.png"), dpi=180); plt.close(fig)
    except Exception as e:  # figures are optional; tables and claims are already written
        print("[analyze] figures skipped: %s" % e)

    print("[analyze] pairs=%d groups=%d claims=%d" % (len(pairs), len(groups), len(claims)))
    for s in summary:
        if s["kind"] == "ALL":
            print("  %-12s %-5s %-14s n=%3d identical=%5.1f%% speedup=%.2fx [%.2f, %.2f] accept=%.2f base=%.1f tok/s" %
                  (s["tag"], s["target"], s["config"], s["n_pairs"], 100 * s["identity_rate"], s["speedup"],
                   s["speedup_lo"], s["speedup_hi"], s["accept_rate"], s["base_tps"]))


if __name__ == "__main__":
    main()
