#!/usr/bin/env bash
# Kit self-test with a fake server. Proves the harness, pairing, analysis and paper fill work end to end.
# Run from the project root:  bash kit/selftest.sh   (takes under 1 minute; uses ./_selftest only)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; T="$ROOT/_selftest"; rm -rf "$T"; mkdir -p "$T/workloads" "$T/repos"; cd "$T"
PORT="${SELFTEST_PORT:-8189}"
cat > configs.json <<JSON
{"llama_server": "python3 $ROOT/kit/mock_server.py", "port": $PORT,
 "targets": {"12b": {"base_args": ["-m", "fake.gguf"], "configs": {
   "baseline": {"server_args": ["--spec-type", "none"]},
   "baseline_rerun": {"server_args": ["--spec-type", "none"]},
   "mtp": {"server_args": ["--spec-type", "draft-mtp"]},
   "mtp_ngram": {"server_args": ["--spec-type", "ngram-mod,draft-mtp", "--mock-diverge"]}}}}}
JSON
python3 - <<PY
import json
with open("workloads/W1_edit.jsonl","w") as f:
    for i in range(23):
        f.write(json.dumps({"id":"t%d#edit"%i,"task":"t%d"%i,"kind":"edit","split":"tune" if i<3 else "test",
          "messages":[{"role":"system","content":"edit"},{"role":"user","content":"issue %d"%i}],"max_tokens":64})+"\n")
PY
python3 "$ROOT/kit/bench.py" --target 12b --configs baseline,baseline_rerun,mtp,mtp_ngram --workload workloads/W1_edit.jsonl \
  --split test --out results/raw/W1.jsonl --tag W1 --block-size 6 > bench1.log
# resume must do nothing new
python3 "$ROOT/kit/bench.py" --target 12b --configs baseline,mtp --workload workloads/W1_edit.jsonl --split test \
  --out results/raw/W1.jsonl --tag W1 --block-size 6 | grep -q "already_done=40/40"
# tiny git repo for the agent recorder
mkdir -p repos/rich && cd repos/rich && git init -q && printf 'def a():\n    return 1\n' > setup.py && git add . \
  && git -c user.email=a@b -c user.name=t commit -qm init && SHA=$(git rev-parse HEAD) && cd "$T"
printf '{"instance_id":"rich_1","repo":"Textualize/rich","base_commit":"%s","patch":"","problem_statement":"bug"}\n' "$SHA" > tasks.jsonl
python3 "$ROOT/kit/agent_record.py" --target 12b --tasks tasks.jsonl --task-ids rich_1 --out workloads/W2_agent.jsonl > rec.log
python3 "$ROOT/kit/bench.py" --target 12b --configs baseline,mtp --workload workloads/W2_agent.jsonl \
  --out results/raw/W2.jsonl --tag W2 > bench2.log
python3 "$ROOT/kit/analyze.py" > analyze.log; cat analyze.log
printf 'Speedup {{W1.12b.mtp.ALL.speedup|.2f}}x, identical {{W1.12b.mtp.ALL.identity_rate|pct}}, n={{W1.12b.mtp.ALL.n_pairs}}.\n' > tpl.md
python3 "$ROOT/kit/fill_paper.py" tpl.md results/claims.json out.md && cat out.md
python3 - <<PY
import json,csv
c=json.load(open("results/claims.json"))
assert c["W1.12b.mtp.ALL.n_pairs"]==20, c["W1.12b.mtp.ALL.n_pairs"]
assert abs(c["W1.12b.mtp.ALL.speedup"]-1/0.62)<0.02, c["W1.12b.mtp.ALL.speedup"]
assert c["W1.12b.mtp.ALL.identity_rate"]==1.0
assert c["W1.12b.baseline_rerun.ALL.identity_rate"]==1.0
assert c["W1.12b.mtp_ngram.ALL.identity_rate"]<1.0
assert c["W2.12b.mtp.ALL.n_pairs"]==3
assert sum(1 for _ in csv.reader(open("release/records.csv")))>80
print("SELFTEST PASS")
PY
