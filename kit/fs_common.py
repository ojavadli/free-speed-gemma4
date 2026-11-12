"""Shared helpers for the FREE SPEED kit. Standard library only."""
import json, os, shlex, socket, subprocess, time, urllib.request


def read_jsonl(path):
    rows = []
    if not os.path.exists(path):
        return rows
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                pass  # a half-written last line after a crash is skipped
    return rows


def append_jsonl(path, row):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())


def http_json(url, payload=None, timeout=900):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def port_open(port, host="127.0.0.1"):
    s = socket.socket()
    s.settimeout(0.5)
    try:
        s.connect((host, port))
        return True
    except OSError:
        return False
    finally:
        s.close()


class Server:
    """Launches one llama-server process and waits until /health is ok."""

    def __init__(self, binary, args, port, log_path):
        self.binary, self.args, self.port, self.log_path = binary, list(args), int(port), log_path
        self.proc, self.log = None, None

    def start(self, health_timeout=600):
        t0 = time.time()
        while port_open(self.port):  # a previous server is still shutting down
            if time.time() - t0 > 60:
                raise RuntimeError("port %d is busy" % self.port)
            time.sleep(1)
        cmd = shlex.split(self.binary) + self.args + ["--host", "127.0.0.1", "--port", str(self.port)]
        os.makedirs(os.path.dirname(self.log_path) or ".", exist_ok=True)
        self.log = open(self.log_path, "ab")
        self.log.write(("\n===== %s\n" % " ".join(cmd)).encode())
        self.log.flush()
        self.proc = subprocess.Popen(cmd, stdout=self.log, stderr=subprocess.STDOUT)
        t0 = time.time()
        while time.time() - t0 < health_timeout:
            if self.proc.poll() is not None:
                rc = self.proc.returncode
                self.stop()
                raise RuntimeError("server exited rc=%s, see %s" % (rc, self.log_path))
            try:
                h = http_json("http://127.0.0.1:%d/health" % self.port, timeout=5)
                if h.get("status", "ok") == "ok":
                    return self
            except Exception:
                pass
            time.sleep(1.0)
        self.stop()
        raise RuntimeError("server health timeout, see %s" % self.log_path)

    def stop(self):
        if self.proc is not None and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=30)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait(timeout=30)
        self.proc = None
        if self.log:
            self.log.close()
            self.log = None
        t0 = time.time()
        while port_open(self.port) and time.time() - t0 < 30:
            time.sleep(0.5)


def load_cfg(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def server_for(cfg, target, config_name, log_dir="logs"):
    t = cfg["targets"][target]
    c = t["configs"][config_name]
    args = list(t["base_args"]) + list(c.get("server_args", []))
    return Server(cfg["llama_server"], args, cfg.get("port", 8089),
                  os.path.join(log_dir, "server_%s_%s.log" % (target, config_name))), c


def chat_payload(messages, max_tokens, extra=None):
    extra = dict(extra or {})
    prefix = extra.pop("_system_prefix", "")  # e.g. "<|think|>" to switch Gemma 4 thinking on via the system turn
    if prefix:
        messages = [dict(m) for m in messages]
        if messages and messages[0]["role"] == "system":
            messages[0]["content"] = prefix + messages[0]["content"]
        else:
            messages.insert(0, {"role": "system", "content": prefix})
    p = {"messages": messages, "max_tokens": int(max_tokens), "temperature": 0, "seed": 42,
         "stream": False, "cache_prompt": True}
    p.update(extra)
    return p


def parse_chat(r):
    ch = (r.get("choices") or [{}])[0]
    msg = ch.get("message") or {}
    return (msg.get("content") or "", msg.get("reasoning_content") or "",
            ch.get("finish_reason"), r.get("timings") or {}, r.get("usage") or {})
