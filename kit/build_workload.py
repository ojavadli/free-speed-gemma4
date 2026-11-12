#!/usr/bin/env python3
"""Builds workload W1 (single-turn repair edits) for the 129 public dev tasks.

Source A (preferred): --tasks tasks.jsonl from the competition data
  (fields used: instance_id, repo, base_commit, patch, problem_statement).
Source B (fallback, no Kaggle data needed): --github task_dates.csv
  (task ids like fastapi_14851); the patch and a PR-derived statement come from public git history.

Each row: {"id","task","repo","kind":"edit","split":"tune"|"test","messages":[...],"max_tokens":512,"meta":{...}}
Split: 12 tasks with the smallest sha1(task id) are "tune"; the rest are "test". Never report tune rows.
"""
import argparse, csv, hashlib, json, os, re, subprocess, sys, urllib.request

REPOS = {"fastapi": "fastapi/fastapi", "rich": "Textualize/rich", "requests": "psf/requests", "httpx": "encode/httpx"}
SYSTEM = (
    "You are a coding agent fixing a bug in a Python repository. You get the issue and the relevant source excerpt. "
    "Reply with one or more edit blocks and nothing else. Each block has exactly this form:\n"
    "<<<<<<< SEARCH\n(exact lines copied from the excerpt)\n=======\n(replacement lines)\n>>>>>>> REPLACE\n"
    "Copy the SEARCH lines exactly, including indentation. Include at least 3 unchanged context lines around each change."
)


def sh(cmd, cwd=None, check=True):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if check and r.returncode != 0:
        raise RuntimeError("%s failed: %s" % (" ".join(cmd), r.stderr.strip()[:300]))
    return r.stdout


def parse_patch(patch):
    """{path: [(old_start, old_len), ...]} for files that exist before the fix."""
    files, cur, old_null = {}, None, False
    for line in patch.splitlines():
        if line.startswith("--- "):
            old_null = line[4:].strip() == "/dev/null"
        elif line.startswith("+++ "):
            p = line[4:].strip().split("\t")[0]
            p = p[2:] if p.startswith("b/") else p
            cur = None if (p == "/dev/null" or old_null) else p
            if cur:
                files.setdefault(cur, [])
        elif line.startswith("@@") and cur:
            m = re.match(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", line)
            if m:
                files[cur].append((int(m.group(1)), int(m.group(2) or 1)))
    return {k: v for k, v in files.items() if v}


def is_test(path):
    b = os.path.basename(path)
    return ("/tests/" in "/" + path or b.startswith("test_") or b.endswith("_test.py")
            or path.startswith(("docs/", "docs_src/", "examples/")))


def pick_file(files):
    cand = [(sum(l for _, l in h), p) for p, h in files.items() if p.endswith(".py") and not is_test(p)]
    if not cand:
        cand = [(sum(l for _, l in h), p) for p, h in files.items() if p.endswith(".py")]
    return max(cand)[1] if cand else None


def excerpt(text, hunks, pad=40, cap=220):
    lines = text.splitlines()
    n = len(lines)
    lo = max(1, min(s for s, _ in hunks) - pad)
    hi = min(n, max(s + l for s, l in hunks) + pad)
    if hi - lo + 1 > cap:
        s, l = hunks[0]
        lo = max(1, s - 60)
        hi = min(n, lo + cap - 1)
    return lo, hi, "\n".join(lines[lo - 1:hi])


def fetch_raw(repo, sha, path, cache):
    fn = os.path.join(cache, hashlib.sha1(("%s@%s:%s" % (repo, sha, path)).encode()).hexdigest() + ".txt")
    if os.path.exists(fn):
        return open(fn, encoding="utf-8", errors="replace").read()
    url = "https://raw.githubusercontent.com/%s/%s/%s" % (repo, sha, path)
    with urllib.request.urlopen(url, timeout=60) as r:
        txt = r.read().decode("utf-8", errors="replace")
    os.makedirs(cache, exist_ok=True)
    open(fn, "w", encoding="utf-8").write(txt)
    return txt


def ensure_clone(repo, root):
    d = os.path.join(root, repo.split("/")[1])
    if not os.path.isdir(os.path.join(d, ".git")):
        os.makedirs(root, exist_ok=True)
        sh(["git", "clone", "--quiet", "--filter=blob:none", "https://github.com/%s" % repo, d])
    return d


def github_task(repo, num, root):
    """Reconstructs (base_commit, patch, statement) for PR `num` from public git history only."""
    d = ensure_clone(repo, root)
    sh(["git", "fetch", "--quiet", "origin", "+refs/pull/%d/head:refs/pr/%d" % (num, num)], cwd=d)
    head = sh(["git", "rev-parse", "refs/pr/%d" % num], cwd=d).strip()
    main = sh(["git", "rev-parse", "origin/HEAD"], cwd=d).strip()
    mb = sh(["git", "merge-base", head, main], cwd=d).strip()
    if mb != head:  # squash or rebase merge: PR head is not in main's history
        base, tip = mb, head
    else:  # merged with a merge commit: find the first main commit that contains the PR head
        chain = sh(["git", "rev-list", "--first-parent", "%s..%s" % (head, main)], cwd=d).split()
        chain.reverse()  # oldest first
        lo, hi = 0, len(chain) - 1
        def contains(c):
            return subprocess.run(["git", "merge-base", "--is-ancestor", head, c], cwd=d).returncode == 0
        while lo < hi:
            mid = (lo + hi) // 2
            if contains(chain[mid]):
                hi = mid
            else:
                lo = mid + 1
        tip = chain[lo]
        base = sh(["git", "rev-parse", tip + "^1"], cwd=d).strip()
    patch = sh(["git", "diff", base, tip], cwd=d)
    msgs = sh(["git", "log", "--format=%s%n%b", "%s..%s" % (base, tip)], cwd=d).strip()
    return base, patch, msgs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", default="")
    ap.add_argument("--github", default="")
    ap.add_argument("--out", default="workloads/W1_edit.jsonl")
    ap.add_argument("--cache", default="cache/files")
    ap.add_argument("--repos", default="repos")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()

    tasks = []
    if a.tasks:
        for line in open(a.tasks, encoding="utf-8"):
            if line.strip():
                t = json.loads(line)
                tasks.append({"id": t["instance_id"], "repo": t["repo"], "base": t["base_commit"],
                              "patch": t["patch"], "issue": t.get("problem_statement") or "", "src": "tasks.jsonl"})
    elif a.github:
        ids = [r["task"] for r in csv.DictReader(open(a.github))]
        for tid in ids[:a.limit or None]:
            name, num = tid.rsplit("_", 1)
            try:
                base, patch, msg = github_task(REPOS[name], int(num), a.repos)
                tasks.append({"id": tid, "repo": REPOS[name], "base": base, "patch": patch, "issue": msg, "src": "github"})
            except Exception as e:
                print("[workload] skip %s: %s" % (tid, e))
    else:
        sys.exit("give --tasks or --github")
    if a.limit:
        tasks = tasks[:a.limit]

    order = sorted(tasks, key=lambda t: hashlib.sha1(t["id"].encode()).hexdigest())
    tune = {t["id"] for t in order[:12]}
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    kept, skipped = 0, 0
    with open(a.out, "w", encoding="utf-8") as f:
        for t in order:  # sha1 order: --limit N on the test split is a hash-random sample across repositories
            try:
                files = parse_patch(t["patch"])
                path = pick_file(files)
                if not path:
                    skipped += 1; continue
                text = fetch_raw(t["repo"], t["base"], path, a.cache)
                lo, hi, ex = excerpt(text, files[path])
                if not ex.strip():
                    skipped += 1; continue
                user = ("Repository: %s\nFile: %s\n\nIssue:\n%s\n\nSource excerpt (lines %d-%d of %s):\n```python\n%s\n```\n"
                        "Write the edit blocks." % (t["repo"], path, t["issue"].strip()[:2500], lo, hi, path, ex))
                row = {"id": t["id"] + "#edit", "task": t["id"], "repo": t["repo"], "kind": "edit",
                       "split": "tune" if t["id"] in tune else "test",
                       "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}],
                       "max_tokens": 512, "meta": {"path": path, "lines": [lo, hi], "source": t["src"]}}
                f.write(json.dumps(row, ensure_ascii=False) + "\n"); kept += 1
            except Exception as e:
                skipped += 1
                print("[workload] skip %s: %s" % (t["id"], e))
    print("[workload] wrote %d rows to %s (skipped %d; tune=%d)" % (kept, a.out, skipped, len(tune)))


if __name__ == "__main__":
    main()
