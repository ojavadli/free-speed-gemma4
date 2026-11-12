#!/usr/bin/env python3
"""FREE SPEED: paired decoding benchmark against llama-server.

For every block of prompts, each decoding config gets its own server launch, in an order
rotated per block (so heat and background load are spread evenly over configs).
Each (config, prompt) row is appended to --out at once, so a crash loses nothing and
--out is resumable: rows already present with ok=true are skipped.

Workload rows (JSONL): {"id", "task", "kind", "messages" | "prompt", "max_tokens"?, "traj"?, "split"?}
"""
import argparse, datetime, hashlib, json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fs_common import (read_jsonl, append_jsonl, http_json, load_cfg, server_for,
                       chat_payload, parse_chat)


def deadline_epoch(hhmm):
    if not hhmm:
        return None
    h, m = [int(x) for x in hhmm.split(":")]
    now = datetime.datetime.now()
    return now.replace(hour=h, minute=m, second=0, microsecond=0).timestamp()


def one_request(port, row, max_tokens, extra, timeout):
    mt = int(row.get("max_tokens") or max_tokens)
    if "messages" in row:
        payload = chat_payload(row["messages"], mt, extra)
        t0 = time.time()
        r = http_json("http://127.0.0.1:%d/v1/chat/completions" % port, payload, timeout)
        wall = (time.time() - t0) * 1000
        content, reasoning, finish, timings, usage = parse_chat(r)
        tokens = None
    else:
        payload = {"prompt": row["prompt"], "n_predict": mt, "temperature": 0, "seed": 42,
                   "stream": False, "cache_prompt": True, "return_tokens": True}
        payload.update(extra or {})
        t0 = time.time()
        r = http_json("http://127.0.0.1:%d/completion" % port, payload, timeout)
        wall = (time.time() - t0) * 1000
        content, reasoning = r.get("content") or "", ""
        finish = r.get("stop_type") or ("length" if r.get("stopped_limit") else "stop")
        timings, usage, tokens = r.get("timings") or {}, {}, r.get("tokens")
    pn = timings.get("predicted_n") or usage.get("completion_tokens") or 0
    pms = timings.get("predicted_ms")
    if pms is None:  # server without timings: fall back to wall time
        pms = wall
    return {
        "content": content, "reasoning": reasoning, "finish": finish, "tokens": tokens,
        "wall_ms": wall, "predicted_n": pn, "predicted_ms": pms,
        "prompt_n": timings.get("prompt_n") or usage.get("prompt_tokens") or 0,
        "prompt_ms": timings.get("prompt_ms") or 0.0,
        "draft_n": timings.get("draft_n"), "draft_n_accepted": timings.get("draft_n_accepted"),
        "timings_raw": timings,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cfg", default="configs.json")
    ap.add_argument("--target", required=True)
    ap.add_argument("--configs", required=True, help="comma list; must include baseline")
    ap.add_argument("--workload", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--tag", required=True, help="experiment name, e.g. W1_main")
    ap.add_argument("--split", default="", help="keep only rows with this split")
    ap.add_argument("--limit", type=int, default=0, help="keep only the first N rows (after split)")
    ap.add_argument("--block-size", type=int, default=10)
    ap.add_argument("--max-tokens", type=int, default=512)
    ap.add_argument("--request-file", default="", help="JSON merged into every request")
    ap.add_argument("--deadline", default="", help="local HH:MM; stop cleanly after this time")
    ap.add_argument("--timeout", type=int, default=900)
    a = ap.parse_args()

    cfg = load_cfg(a.cfg)
    names = [c.strip() for c in a.configs.split(",") if c.strip()]
    for n in names:
        if n not in cfg["targets"][a.target]["configs"]:
            sys.exit("config %r is not defined for target %r in %s" % (n, a.target, a.cfg))
    extra = {}
    if a.request_file:
        with open(a.request_file) as f:
            extra = json.load(f)
    rows = read_jsonl(a.workload)
    if a.split:
        rows = [r for r in rows if r.get("split") == a.split]
    if a.limit:
        rows = rows[:a.limit]
    if not rows:
        sys.exit("no workload rows")

    # blocks: one trajectory per block when rows carry "traj", else chunks of --block-size
    blocks, order = {}, []
    if any("traj" in r for r in rows):
        for r in rows:
            k = r.get("traj", r["id"])
            if k not in blocks:
                blocks[k] = []
                order.append(k)
            blocks[k].append(r)
    else:
        for i in range(0, len(rows), a.block_size):
            k = "b%04d" % (i // a.block_size)
            blocks[k] = rows[i:i + a.block_size]
            order.append(k)

    done = {(r["config"], r["id"]) for r in read_jsonl(a.out) if r.get("ok") and r.get("tag") == a.tag
            and r.get("target") == a.target}
    stop_at = deadline_epoch(a.deadline)
    total = len(rows) * len(names)
    n_done, t_start = len([1 for r in rows for n in names if (n, r["id"]) in done]), time.time()
    print("[bench] tag=%s target=%s rows=%d configs=%s already_done=%d/%d" %
          (a.tag, a.target, len(rows), names, n_done, total), flush=True)

    for bi, bk in enumerate(order):
        rot = names[bi % len(names):] + names[:bi % len(names)]
        for pos, name in enumerate(rot):
            todo = [r for r in blocks[bk] if (name, r["id"]) not in done]
            if not todo:
                continue
            if stop_at and time.time() > stop_at:
                print("[bench] deadline reached, stopping cleanly", flush=True)
                return
            srv, c = server_for(cfg, a.target, name)
            req_extra = dict(extra)
            req_extra.update(c.get("request", {}))
            try:
                srv.start()
            except Exception as e:
                print("[bench] SERVER START FAILED %s/%s: %s" % (a.target, name, e), flush=True)
                for r in todo:
                    append_jsonl(a.out, {"tag": a.tag, "target": a.target, "config": name, "id": r["id"],
                                         "ok": False, "error": "server_start: %s" % e, "ts": time.time()})
                continue
            try:
                try:  # warm up the Metal graph; not recorded
                    http_json("http://127.0.0.1:%d/v1/chat/completions" % srv.port,
                              chat_payload([{"role": "user", "content": "Say OK."}], 4), 120)
                except Exception:
                    pass
                for r in todo:
                    rec = {"tag": a.tag, "target": a.target, "config": name, "id": r["id"],
                           "cluster": r.get("task", r["id"]), "kind": r.get("kind", "na"),
                           "block": bk, "order_pos": pos, "ts": time.time(),
                           "prompt_sha": hashlib.sha256(json.dumps(r.get("messages", r.get("prompt")),
                                                                   sort_keys=True).encode()).hexdigest()[:16]}
                    for attempt in (1, 2):
                        try:
                            rec.update(one_request(srv.port, r, a.max_tokens, req_extra, a.timeout))
                            rec["ok"] = True
                            break
                        except Exception as e:
                            rec["ok"], rec["error"] = False, "%s: %s" % (type(e).__name__, e)
                            if srv.proc is None or srv.proc.poll() is not None:
                                try:
                                    srv.stop()
                                    srv.start()
                                except Exception:
                                    break
                    append_jsonl(a.out, rec)
                    if rec["ok"]:
                        done.add((name, r["id"]))
                    n_done += 1
                    el = time.time() - t_start
                    tps = (rec.get("predicted_n", 0) / rec["predicted_ms"] * 1000) if rec.get("predicted_ms") else 0
                    print("[bench] %d/%d %s %s ok=%s n=%s %.1f tok/s elapsed=%.0fm" %
                          (n_done, total, name, r["id"], rec["ok"], rec.get("predicted_n"), tps, el / 60), flush=True)
                    if stop_at and time.time() > stop_at:
                        break
            finally:
                srv.stop()
    print("[bench] finished tag=%s" % a.tag, flush=True)


if __name__ == "__main__":
    main()
