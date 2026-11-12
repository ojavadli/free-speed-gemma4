#!/usr/bin/env python3
"""Records workload W2: real multi-step agent trajectories with the BASELINE server (greedy decoding).

A minimal tool-using agent (search, read_file, edit_file, submit) works on a checkout of the repository at
the task's base commit. Every model request is saved with its full message history, so bench.py can replay
the exact same steps under every decoding config. Tool outputs are capped at 5,000 characters.

Start the baseline server yourself is NOT needed: this script launches it from configs.json.
"""
import argparse, fnmatch, json, os, re, subprocess, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fs_common import append_jsonl, http_json, load_cfg, server_for, chat_payload, parse_chat, read_jsonl
from build_workload import ensure_clone, github_task, REPOS, sh

SYSTEM = (
    "You are a software engineer fixing a bug in the Python repository in the current directory. "
    "Work step by step with tools. Reply with exactly ONE tool call per turn, as a JSON object inside a ```json code block, e.g.\n"
    "```json\n{\"tool\": \"search\", \"args\": {\"pattern\": \"def render\", \"glob\": \"*.py\"}}\n```\n"
    "Tools:\n"
    "- search(pattern, glob=\"*.py\"): regex search; returns up to 40 hits as path:line: text.\n"
    "- read_file(path, start=1, end=start+120): returns numbered lines.\n"
    "- edit_file(path, old, new): replaces the exact string old (it must occur once in the file) with new.\n"
    "- submit(): call when the fix is complete.\n"
    "Rules: one tool call per reply. Find the faulty code, make a minimal fix with edit_file, then submit. Do not edit tests."
)
CAP = 5000


def safe(root, path):
    p = os.path.realpath(os.path.join(root, path))
    if not p.startswith(os.path.realpath(root) + os.sep):
        raise ValueError("path outside the repository")
    return p


def tool_search(root, pattern, glob="*.py"):
    try:
        rx = re.compile(pattern)
    except re.error as e:
        return "bad regex: %s" % e
    hits, nfiles = [], 0
    for dp, dn, fns in os.walk(root):
        dn[:] = [d for d in dn if d not in (".git", "node_modules", "__pycache__", ".venv")]
        for fn in fns:
            if not fnmatch.fnmatch(fn, glob):
                continue
            nfiles += 1
            if nfiles > 6000:
                break
            fp = os.path.join(dp, fn)
            try:
                for i, line in enumerate(open(fp, encoding="utf-8", errors="replace"), 1):
                    if rx.search(line):
                        hits.append("%s:%d: %s" % (os.path.relpath(fp, root), i, line.rstrip()[:160]))
                        if len(hits) >= 40:
                            return "\n".join(hits)
            except OSError:
                pass
    return "\n".join(hits) if hits else "no matches"


def tool_read(root, path, start=1, end=None):
    lines = open(safe(root, path), encoding="utf-8", errors="replace").read().splitlines()
    start = max(1, int(start)); end = int(end) if end else start + 120
    return "\n".join("%d: %s" % (i, lines[i - 1]) for i in range(start, min(len(lines), end) + 1)) or "(empty range)"


def tool_edit(root, path, old, new):
    p = safe(root, path)
    text = open(p, encoding="utf-8", errors="replace").read()
    c = text.count(old)
    if c != 1:
        return "edit failed: old string occurs %d times (must be exactly 1)" % c
    open(p, "w", encoding="utf-8").write(text.replace(old, new, 1))
    return "edit applied to %s" % path


def parse_call(content):
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.S)
    raw = m.group(1) if m else None
    if raw is None:
        i, j = content.find("{"), content.rfind("}")
        raw = content[i:j + 1] if i >= 0 and j > i else None
    if raw is None:
        return None
    try:
        d = json.loads(raw)
        return d if isinstance(d, dict) and "tool" in d else None
    except json.JSONDecodeError:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cfg", default="configs.json")
    ap.add_argument("--target", required=True)
    ap.add_argument("--tasks", default="", help="competition tasks.jsonl (preferred)")
    ap.add_argument("--task-ids", required=True, help="comma list of task ids, e.g. rich_3521,fastapi_14851")
    ap.add_argument("--out", default="workloads/W2_agent.jsonl")
    ap.add_argument("--repos", default="repos"); ap.add_argument("--work", default="work")
    ap.add_argument("--max-steps", type=int, default=8)
    ap.add_argument("--max-tokens", type=int, default=768)
    ap.add_argument("--request-file", default="")
    a = ap.parse_args()
    extra = json.load(open(a.request_file)) if a.request_file else {}
    by_id = {}
    if a.tasks:
        for line in open(a.tasks, encoding="utf-8"):
            if line.strip():
                t = json.loads(line); by_id[t["instance_id"]] = t
    prev = read_jsonl(a.out)
    done_traj = {r["traj"] for r in prev if r.get("last")}
    if any(r["traj"] not in done_traj for r in prev):  # drop half-recorded trajectories before resuming
        keep = [r for r in prev if r["traj"] in done_traj]
        with open(a.out, "w", encoding="utf-8") as f:
            for r in keep:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    cfg = load_cfg(a.cfg)
    srv, c = server_for(cfg, a.target, "baseline")
    extra.update(c.get("request", {}))
    srv.start()
    try:
        for tid in [x.strip() for x in a.task_ids.split(",") if x.strip()]:
            if tid in done_traj:
                continue
            name, num = tid.rsplit("_", 1)
            try:
                if tid in by_id:
                    repo, base, issue = by_id[tid]["repo"], by_id[tid]["base_commit"], by_id[tid].get("problem_statement") or ""
                    ensure_clone(repo, a.repos)
                else:
                    repo = REPOS[name]
                    base, _, issue = github_task(repo, int(num), a.repos)
                rdir = os.path.join(a.repos, repo.split("/")[1])
                wdir = os.path.abspath(os.path.join(a.work, tid))
                if not os.path.isdir(wdir):
                    os.makedirs(a.work, exist_ok=True)
                    sh(["git", "worktree", "add", "--force", "--detach", wdir, base], cwd=rdir)
                else:
                    sh(["git", "checkout", "--quiet", "--force", base], cwd=wdir); sh(["git", "clean", "-fdq"], cwd=wdir)
            except Exception as e:
                print("[record] skip %s: %s" % (tid, e), flush=True)
                continue
            messages = [{"role": "system", "content": SYSTEM},
                        {"role": "user", "content": "Issue to fix:\n%s\n\nStart by locating the faulty code." % issue.strip()[:2500]}]
            bad = 0
            for step in range(a.max_steps):
                snapshot = json.loads(json.dumps(messages))
                try:
                    r = http_json("http://127.0.0.1:%d/v1/chat/completions" % srv.port,
                                  chat_payload(messages, a.max_tokens, extra), 900)
                except Exception as e:
                    print("[record] %s step %d request failed: %s" % (tid, step, e), flush=True)
                    break
                content, reasoning, finish, timings, usage = parse_chat(r)
                call = parse_call(content)
                tool = call.get("tool") if call else "invalid"
                kind = {"search": "navigate", "read_file": "navigate", "edit_file": "edit", "submit": "submit"}.get(tool, "invalid")
                last = (tool == "submit") or step == a.max_steps - 1
                if call is None:
                    bad += 1; result = "Invalid reply. Reply with exactly one JSON tool call in a ```json block."
                    last = last or bad >= 2
                else:
                    args = call.get("args") or {}
                    try:
                        if tool == "search": result = tool_search(wdir, str(args.get("pattern", "")), str(args.get("glob", "*.py")))
                        elif tool == "read_file": result = tool_read(wdir, str(args.get("path", "")), args.get("start", 1), args.get("end"))
                        elif tool == "edit_file": result = tool_edit(wdir, str(args.get("path", "")), str(args.get("old", "")), str(args.get("new", "")))
                        elif tool == "submit": result = "submitted"
                        else: result = "unknown tool %r" % tool
                    except Exception as e:
                        result = "tool error: %s" % e
                append_jsonl(a.out, {"id": "%s#s%d" % (tid, step), "task": tid, "traj": tid, "step": step, "kind": kind,
                                     "messages": snapshot, "max_tokens": a.max_tokens, "last": bool(last),
                                     "recorded": {"content": content, "reasoning": reasoning,
                                                  "predicted_n": timings.get("predicted_n"), "predicted_ms": timings.get("predicted_ms")}})
                print("[record] %s step %d tool=%s n=%s" % (tid, step, tool, timings.get("predicted_n")), flush=True)
                if last:
                    break
                messages.append({"role": "assistant", "content": content})
                messages.append({"role": "user", "content": "TOOL RESULT:\n" + result[:CAP]})
            diff = subprocess.run(["git", "diff"], cwd=wdir, capture_output=True, text=True).stdout
            append_jsonl(os.path.join(os.path.dirname(a.out) or ".", "W2_final_diffs.jsonl"), {"task": tid, "diff_chars": len(diff), "diff": diff[:20000]})
    finally:
        srv.stop()


if __name__ == "__main__":
    main()
