# FREE SPEED: master prompt for Cursor (Grok)

You are the sole engineer and writer on a research paper that must be submitted today. Read this whole file before you run anything. Then execute it from top to bottom without stopping.

## 0. Mission

**Project name:** FREE SPEED.
**Claim to test and, if the data support it, to publish:** a Gemma 4 coding agent on a 24 GB MacBook produces the same output faster when it uses Gemma 4's own multi-token-prediction (MTP) drafters and prompt-lookup (n-gram) drafting. Same model, same prompts, same patches, less time.
**Venue:** Kaggle, "Google - The Gemma 4 Developer Agent Paper Track" (judges: Google DeepMind). Five equally weighted criteria: Novelty, Quality (generalizes beyond the competition), Relevance (software engineering and agentic learning), Verifiability, Clarity. Limit 3,000 words.
**Authors:** Anni Zimina, Orkhan Javadli. No company affiliation anywhere, no disclosure line.
**Why this can win:** three competition entries proved the agent's time budget is spent generating tokens; none made tokens cheaper. Google ships an MTP drafter with every Gemma 4 model and says it is lossless. A scan of all 171 public notebooks in this track on 12 Nov found zero that use speculative decoding (one mentions it as a hypothetical, one filters the drafter files out). You will deliver the first measurement inside a coding-agent loop, with a byte-identity check, a stacking result (MTP plus prompt lookup), a breakdown by agent step type, and a harness anyone can rerun.

**Hard deadline:** Thu 12 Nov 2026, 15:59 Pacific (23:59 UTC). OJ must click Submit on Kaggle by 14:30 Pacific. Your handoff to OJ is due at **13:50 Pacific**. An unsubmitted draft counts as nothing, so a smaller finished paper beats a larger unfinished one.

## 1. Operating contract (non-negotiable)

1. **Never stop and never ask OJ a question.** If something fails, use the failure playbook (section 13), take the listed fallback, write one line in `STATUS.md`, and continue. The only time you end your turn is after the handoff message in section 14.
2. **Keep `STATUS.md` current.** It holds a checklist of every numbered step below with a timestamp (`date "+%H:%M"`) when done, plus a short log of decisions. If your context is ever truncated or you are restarted, first reread this file and `STATUS.md`, then resume at the first unchecked step.
3. **Check the clock before every phase** with `date "+%H:%M"`. If you are behind a gate in section 2, apply the cut list there. Never extend a deadline.
4. **No invented numbers.** Every number in the paper comes from `results/claims.json` through `kit/fill_paper.py`, or from `env/*.json`, or from a source you opened today and cite. Numbers from `kit/mock_server.py` or `_selftest/` are fake by design and must never appear anywhere.
5. **Report what you measure.** If drafting is slower or outputs differ, that goes in the paper as measured. Do not drop prompts, rerun until it looks better, or tune on the test split.
6. **Long commands run in the background.** Any command that can take more than 90 seconds is started as `nohup caffeinate -i <command> > logs/<name>.log 2>&1 &` (write `.venv/bin/python` instead of `python3` in background commands) and then polled with `tail -n 5 logs/<name>.log` every 2 to 4 minutes. Never block the terminal on a long foreground command.
7. **While a benchmark run is in progress, do only light work:** edit text, verify citations on the web, read logs. No downloads, compiles, pip installs, other models, or CPU-heavy scripts, because they distort timings.
8. **One model server at a time.** Before any run: `pgrep -fl llama-server` must be empty (kill leftovers with `pkill -f llama-server`), and no Ollama model may be loaded (`ollama ps`; `ollama stop <name>` for each).
9. **Do not change the logic of files in `kit/`** unless a bug stops a run. If you must, make the smallest fix, rerun `bash kit/selftest.sh`, and log the change in `DEVIATIONS.md`.
10. **Do not publish competition content.** Never commit or upload `workloads/`, `results/raw/`, `results/tune/`, `results/smoke/`, `cache/`, `repos/`, `work/`, `models/`, or any `tasks.jsonl`. The public artifacts are code, `ANALYSIS_PLAN.md`, `release/records.csv` (hashes and timings only), tables, figures and the paper.
11. **Style for everything a human will read:** plain words, no em dashes, no hype words, define every term on first use.
12. Commit to local git after every phase (`git add -A && git commit -qm "<phase>"`), respecting `.gitignore`.

## 2. Clock, gates and cut list (Pacific time)

| Gate | Time | Must be true |
|---|---|---|
| G1 | 05:45 | llama-server with `draft-mtp` works; 12B and E4B targets and drafters load; smoke test passes |
| G2 | 06:20 | workloads built; tuning done; `ANALYSIS_PLAN.md` frozen and committed |
| F1 | 07:50 | W1 on 12B finished (deadline passed to the script) |
| F2 | 09:40 | W2 recorded and replayed on 12B |
| F3 | 10:15 | W1 on E4B finished |
| F4 | 10:35 | W1s sampling check finished |
| F5 | 11:00 | optional `e2b_draft` run; **all experiments stop at 11:00 no matter what** |
| G3 | 11:30 | analysis, figures, `claims.json`, QA checks done |
| G4 | 13:00 | `paper/PAPER.md` complete, under 2,900 words, fill script exits 0 |
| G5 | 13:50 | repo, notebook, cover image, `SUBMISSION/` pack done; handoff message sent |

If you start late or fall behind, do not shift the gates. Cut in this order, logging each cut in `STATUS.md`: (1) F5 `e2b_draft`, (2) F4 sampling, (3) reduce W1 E4B to `--limit 24`, (4) reduce W2 to 5 trajectories, (5) drop `baseline_rerun` from W2 (keep it in W1), (6) reduce W1 12B to `--limit 32`. Never cut: W1 12B with `baseline`, `baseline_rerun`, `mtp`, `ngram`, `mtp_ngram`; the analysis; the paper; the handoff.

Every `bench.py` call below carries `--deadline HH:MM`. The script stops cleanly at that time and everything already measured is kept. Runs are resumable: the same command continues where it stopped.

## 3. Project layout and the kit

Work in one folder (the folder open in Cursor). Expected content at the start:

```
CURSOR_MASTER_PROMPT.md   this file
kit/                      tested harness (stdlib + numpy + matplotlib)
  bench.py                paired benchmark: one server launch per (block, config), rotated order, resumable
  agent_record.py         records real agent trajectories with the baseline server (workload W2)
  build_workload.py       builds W1 from tasks.jsonl, or from public git history if Kaggle data is missing
  analyze.py              pairing, identity, speedups, bootstrap CIs, tables, figures, claims.json, release/records.csv
  fill_paper.py           fills {{claim}} placeholders; exits 1 on any missing key
  project.py              upper-bound projection from the Many Labs pooled outcomes
  make_notebook.py        builds the CPU-only Kaggle notebook with records embedded
  probe_thinking.py       finds request settings that switch Gemma 4 thinking on and off
  find_models.py          lists GGUF candidates on Hugging Face
  mock_server.py, selftest.sh   fake server and end-to-end self-test (fake numbers, never for the paper)
configs.example.json      template for configs.json
ANALYSIS_PLAN.md          pre-registration; you fill 3 lines and freeze it
paper/PAPER_TEMPLATE.md   paper skeleton with claim placeholders
task_dates.csv            the 129 public dev task ids with PR dates
```

If `kit/` is missing: look for `freespeed_kit.zip` in the current folder, `~/Downloads` and `~/Desktop` (`mdfind -name freespeed_kit.zip`), unzip it here, and continue. If it cannot be found anywhere, rebuild the scripts from the descriptions above and section 9, then continue.

`configs.json` structure (targets, each with `base_args` and named `configs` holding `server_args` and optional `request`) is shown in `configs.example.json`. `bench.py` launches `llama_server + base_args + server_args + --host 127.0.0.1 --port <port>`.

## 4. Phase A: setup (target 20 minutes)

A1. Create `STATUS.md` with the step checklist (A1 to I8) and the start time. `mkdir -p env logs models results/raw results/tune results/smoke workloads SUBMISSION`. `git init -q` if needed. Write `.gitignore`:
```
models/
repos/
work/
cache/
workloads/
results/raw/
results/tune/
results/smoke/
data/
_selftest/
logs/
ext/
*.gguf
tasks.jsonl
__pycache__/
.venv/
```
A2. Machine facts into `env/machine.json`: `sysctl -n machdep.cpu.brand_string`, `sysctl -n hw.memsize`, `sw_vers -productVersion`, `system_profiler SPDisplaysDataType | grep -i -E "chipset|cores"`, `pmset -g batt | head -1` (must say AC Power; if it says Battery, write a loud line in `STATUS.md`, continue, and note it in the paper's Limitations), `pmset -g | grep -i lowpowermode` (if 1, note it), `df -g . | tail -1` (need 25 GB free; if less, skip the optional E2B download).
A3. Python: `python3 -m venv .venv && source .venv/bin/activate && pip -q install numpy matplotlib huggingface_hub`. Use this venv for every python command. If venv creation fails, use `pip install --user`.
A4. Self-test the kit: `bash kit/selftest.sh` must print `SELFTEST PASS`. Then `rm -rf _selftest`. If port 8189 is busy, `SELFTEST_PORT=8191 bash kit/selftest.sh`.
A5. llama.cpp: `which llama-server || brew install llama.cpp`. Then `llama-server --version 2>&1 | head -3` and `llama-server --help 2>&1 | grep -i -A3 "spec-type"`. The help text must list `draft-mtp` and at least one `ngram-` type. If it does not: `brew upgrade llama.cpp`; if still missing, build from source in the background:
```
git clone --depth 1 https://github.com/ggml-org/llama.cpp ext/llama.cpp
cmake -S ext/llama.cpp -B ext/llama.cpp/build -DCMAKE_BUILD_TYPE=Release
cmake --build ext/llama.cpp/build -j --target llama-server
```
and set `"llama_server": "ext/llama.cpp/build/bin/llama-server"` in `configs.json`. Save the full help text to `env/llama_server_help.txt` and the version to `env/machine.json`.
A6. **Read `env/llama_server_help.txt` and write down the exact flag names this build uses** for: draft model path (`-md` / `--spec-draft-model` / `--model-draft`), draft GPU layers (`-ngld` / `--spec-draft-ngl`), draft length (`--spec-draft-n-max`), speculative type list (`--spec-type`, comma-separated), n-gram tuning flags (`--spec-ngram-*`), flash attention (`-fa on` or `--flash-attn on`), reasoning controls (`--reasoning-budget`, `--reasoning-format`). Flag names changed during 2026; the ones in `configs.example.json` match recent builds but **the help text of your binary is the authority**. Put the mapping in `STATUS.md`.

## 5. Phase B: models (target 25 minutes, downloads in the background)

You need four files, plus one optional:

| Key | What | Rule for choosing |
|---|---|---|
| TARGET_12B | Gemma 4 12B instruction-tuned, QAT, 4-bit GGUF, about 7 GB | first existing of: a `.gguf` in `google/gemma-4-12B-it-qat-q4_0-gguf`; `gemma-4-12B-it-qat-UD-Q4_K_XL.gguf` in `unsloth/gemma-4-12B-it-qat-GGUF`; `gemma-4-12B-it-Q4_0.gguf` in `bartowski/gemma-4-12B-it-GGUF` |
| MTP_12B | the MTP drafter ("assistant") for 12B as GGUF, about 0.1 to 0.3 GB | a GGUF whose repo or file name contains `mtp` or `assistant` and `12B`; prefer one in the same repo as the target, then the most downloaded |
| TARGET_E4B | Gemma 4 E4B QAT 4-bit GGUF | same rules with `E4B` |
| MTP_E4B | the MTP drafter for E4B | same rules with `E4B` |
| TARGET_E2B (optional) | Gemma 4 E2B QAT 4-bit GGUF, only for the optional `e2b_draft` config | download only if disk and time allow, never during a benchmark run |

B1. Run `python3 kit/find_models.py 12B` and `python3 kit/find_models.py E4B`. Pick by the rules. Text-only use: ignore `mmproj` files.
B2. Download with `hf download <repo> <file> --local-dir models/` (older CLI name: `huggingface-cli download`). Run downloads in the background and poll. If a repo is gated (401/403), take the next candidate. Record repo, file, size and `shasum -a 256` of each file in `env/models.json`.
B3. If no drafter GGUF exists for a size: check whether the target repo documents `--spec-type draft-mtp` without a separate drafter file (some target GGUFs embed the head); test it. If that fails, convert the official checkpoint (`google/gemma-4-<SIZE>-it-assistant`) with `convert_hf_to_gguf.py` from the llama.cpp source tree. If that also fails within 15 minutes, drop `mtp` and `mtp_ngram` for that size, keep `ngram`, and for 12B promote `e2b_draft` to a required config.
B4. `cp configs.example.json configs.json` and replace the four model paths and any flag names that differ on your build (A6).

## 6. Phase C: capability probe and smoke tests (target 15 minutes)

C1. Smoke run on 12B (needs a tiny workload; create `workloads/smoke.jsonl` with 3 rows of the form `{"id":"s1","task":"s1","kind":"edit","messages":[{"role":"user","content":"Write a Python function that reverses a list, then show the same function again with a docstring."}],"max_tokens":200}`):
```
python3 kit/bench.py --target 12b --configs baseline,mtp,ngram,mtp_ngram --workload workloads/smoke.jsonl \
  --out results/smoke/12b.jsonl --tag SMOKE --block-size 3
```
Run it in the background and poll. Then inspect `results/smoke/12b.jsonl` and `logs/server_12b_*.log`:
- every row has `"ok": true`, `predicted_n` > 0 and a `timings_raw` object;
- for `mtp` rows, `timings_raw` shows draft counts above zero (`draft_n`, `draft_n_accepted`). If the server does not report draft counts in `timings`, confirm drafting from the server log (it prints draft or acceptance statistics) and note in `STATUS.md` that acceptance will be read from logs;
- the 12B baseline speed is above 8 tokens per second. If it is lower, the model is not fully on the GPU or memory is swapping: check `sysctl vm.swapusage`, reduce `-c` to 8192 in `base_args`, close nothing of OJ's but stop Ollama models, and retry once.
C2. If a config fails to start, read its log, fix the flags using the help text, and retry. For the stacked config try `--spec-type ngram-mod,draft-mtp` and the reverse order; keep the one that starts and reports drafts. If stacking is not supported on this build, drop `mtp_ngram` everywhere and log it.
C3. Same smoke run for `e4b` with `baseline,mtp,ngram,mtp_ngram`.
C4. Thinking switch: `python3 kit/probe_thinking.py --target 12b`. It writes `env/req_think.json` and `env/req_nothink.json`. If no ON setting works, add the server flag your build offers for reasoning (from A6) to a copy `configs_think.json` and use `--cfg configs_think.json` for W2; if nothing works, run W2 with thinking off and say so in the paper. If thinking cannot be switched OFF, use `{}` for W1 and say so.
C5. Write `env/req_sampling.json` = the content of `env/req_nothink.json` plus `"temperature": 1.0, "top_k": 64, "top_p": 0.95, "seed": 1234`.
C6. Commit. Gate G1.

## 7. Phase D: workloads (target 15 minutes)

D1. Find the competition tasks file. In order: `mdfind -name tasks.jsonl | head`; `find ~/Documents ~/Downloads ~/swebench-agents -name tasks.jsonl -maxdepth 6 2>/dev/null | head`; `kaggle competitions download -c gemma-4-developer-agent -f tasks.jsonl -p data/` (unzip if needed). A valid file has 129 lines with keys `instance_id, repo, base_commit, patch, problem_statement`. Copy it to `data/tasks.jsonl` (git-ignored).
D2. Build W1:
- with the file: `python3 kit/build_workload.py --tasks data/tasks.jsonl --out workloads/W1_edit.jsonl`
- without it (fallback, uses public git history only): `python3 kit/build_workload.py --github task_dates.csv --out workloads/W1_edit.jsonl` (clones four repositories, takes a few minutes; run in the background). State in the paper which source was used. With the fallback the "issue" text is the pull request's commit messages.
Expect about 110 to 129 rows, 12 of them `"split": "tune"`. Rows are in hash order, so `--limit 48` on the test split is a random sample across the four repositories; print the repository counts of those 48 rows into `STATUS.md`. Print three user prompts and read them to confirm they contain an issue and a code excerpt.
D3. Choose the 8 W2 task ids by the rule in `ANALYSIS_PLAN.md` section 2 (test split, smallest sha1 of the task id, at least 2 each from fastapi, rich and requests where possible). Save them to `env/w2_tasks.txt` as one comma-separated line.

## 8. Phase E: tuning on the tuning split, then freeze (target 25 minutes, hard stop 06:20)

E1. In `configs.json` under target `12b`, add tuning-only configs: `ngram_simple`, `ngram_mod`, `ngram_k4v` (the three n-gram types your build lists, default parameters) and `mtp_n2`, `mtp_n3`, `mtp_n4` (draft length 2, 3, 4).
E2. Run on the 12 tuning prompts:
```
python3 kit/bench.py --target 12b --configs baseline,ngram_simple,ngram_mod,ngram_k4v,mtp_n2,mtp_n3,mtp_n4 \
  --workload workloads/W1_edit.jsonl --split tune --out results/tune/12b.jsonl --tag TUNE \
  --request-file env/req_nothink.json --block-size 12 --deadline 06:15
python3 kit/analyze.py --raw results/tune --out results/tune_out --release results/tune_out/release --figs results/tune_out/figs
```
E3. Pick the n-gram type and the MTP draft length with the highest speedup among those whose identity rate on the tuning split is 100% (or the highest identity if none reaches 100%). Set `ngram`, `mtp` and `mtp_ngram` for **both** targets to the winners. If tuning did not finish by 06:15, use `ngram-mod` and draft length 2.
E4. Fill the three FROZEN lines in `ANALYSIS_PLAN.md`, commit, and write the commit hash in `STATUS.md`. From now on `configs.json` does not change. Gate G2.

## 9. Phase F: main experiments

Run each command in the background with `nohup caffeinate -i ... &`, poll, and move to the next when the log says `finished` or `deadline reached`. Between runs confirm `pgrep -fl llama-server` is empty.

F1. **W1, 12B (the result that must exist).**
```
python3 kit/bench.py --target 12b --configs baseline,baseline_rerun,mtp,ngram,mtp_ngram \
  --workload workloads/W1_edit.jsonl --split test --limit 48 --out results/raw/W1_12b.jsonl --tag W1 \
  --request-file env/req_nothink.json --block-size 8 --deadline 07:50
```
After the first block completes (about 10 minutes), run `python3 kit/analyze.py` once as a sanity check (it is light) and confirm rows pair up and identity is being measured. Do not change anything based on the numbers.

F2. **W2, 12B agent trajectories.** Record, then replay:
```
python3 kit/agent_record.py --target 12b --tasks data/tasks.jsonl --task-ids "$(cat env/w2_tasks.txt)" \
  --out workloads/W2_agent.jsonl --max-steps 8 --max-tokens 768 --request-file env/req_think.json
python3 kit/bench.py --target 12b --configs baseline,mtp,ngram,mtp_ngram,baseline_rerun \
  --workload workloads/W2_agent.jsonl --out results/raw/W2_12b.jsonl --tag W2 \
  --request-file env/req_think.json --deadline 09:40
```
(omit `--tasks` if you used the git fallback; add `--cfg configs_think.json` to both if C4 required it). Recording must end by 08:20: if it is still running then, stop it (`pkill -f agent_record.py; pkill -f llama-server`) and replay what exists. Every row is one completed step, so a trajectory that was cut short is still valid for replay. Check `workloads/W2_agent.jsonl`: if more than half of the steps have `"kind": "invalid"`, the model is not following the tool format; in that case rerecord once with `env/req_nothink.json` and report W2 as "thinking off".

F3. **W1, E4B.**
```
python3 kit/bench.py --target e4b --configs baseline,mtp,ngram,mtp_ngram \
  --workload workloads/W1_edit.jsonl --split test --limit 48 --out results/raw/W1_e4b.jsonl --tag W1 \
  --request-file env/req_nothink.json --block-size 8 --deadline 10:15
```

F4. **W1s, sampling check on 12B.** Let BEST be the best lossless config so far (rule in `ANALYSIS_PLAN.md` section 4, from a fresh `python3 kit/analyze.py`).
```
python3 kit/bench.py --target 12b --configs baseline,BEST --workload workloads/W1_edit.jsonl --split test --limit 20 \
  --out results/raw/W1s_12b.jsonl --tag W1s --request-file env/req_sampling.json --block-size 10 --deadline 10:35
```

F5. **Optional, only if the clock shows before 10:35 and TARGET_E2B is on disk:** rerun F1's command with `--configs baseline,e2b_draft --deadline 11:00` (same `--out` and `--tag W1`; the baseline rows already exist, so only `e2b_draft` runs). Because this config is measured later than its baseline, say so in the paper next to its number.

At 11:00: `pkill -f bench.py; pkill -f llama-server`. Experiments are over.

## 10. Phase G: analysis and QA (30 minutes)

G1. `python3 kit/analyze.py` writes `results/tables/summary.csv`, `results/tables/pairs.csv`, `results/claims.json`, `release/records.csv`, `figures/*.png`.
G2. Projection. `git clone --depth 1 https://github.com/yuvrajtiwary-bitmesraece/gemma4-many-labs ext/many-labs` then, with H = the headline speedup:
```
python3 kit/project.py --attempts ext/many-labs/data/derived/attempts.csv --tasks ext/many-labs/results/tables/tasks.csv \
  --speedup H --out results/projection.json
```
Merge its keys into `results/claims.json` (prefix kept as is). If the clone fails, delete section 3.5's projection sentences.
G3. QA checks, each logged in `STATUS.md` with pass or fail and the number:
- request errors: count rows with `"ok": false` in `results/raw/*.jsonl`; report the count in the paper if above zero;
- noise floor: `W1.12b.baseline_rerun.ALL.speedup` should be within 0.95 to 1.05; if not, timing noise is high: say so and rely on the bootstrap intervals;
- pairing: `n_pairs` for each config equals the number of baseline rows it could pair with, or you know why not;
- order effect: from `release/records.csv`, mean tokens per second of `baseline` by `order_pos`; report if position changes speed by more than 5%;
- truncation: share of rows with `finish` = `length`; report it;
- identity: for every drafted config compare `identity_rate` with the `baseline_rerun` rate; list the ids that differ and inspect two of them in `results/raw` so that section 3.3 of the paper is written from what you saw.
G4. Choose BEST by the rule in `ANALYSIS_PLAN.md` section 4. Compute H and write both in `STATUS.md`.
G5. Make `figures/cover.png`, 1120 x 560 pixels, white background: large text "Same patch. {H}x faster." and a small line "Gemma 4 12B coding agent, 24 GB MacBook, byte-identical output on {identity}% of steps". Numbers from claims. Commit. Gate G3.

## 11. Phase H: the paper (90 minutes)

H1. Title rule (H rounded down to one decimal):
- H at least 1.25 and BEST is lossless: **"Free Speed: Same Gemma 4 Patches, {H}x Faster on a Laptop"**
- otherwise: **"Free Speed? Where Gemma 4's Drafters Help a Coding Agent and Where They Do Not"**
Subtitle rule: "Gemma 4's own drafters and prompt lookup cut a coding agent's decode time by {round(100*(1-1/H))}% with identical output on {identity}% of steps, on a 24 GB MacBook." Adjust the wording to what was measured.
H2. Copy `paper/PAPER_TEMPLATE.md` to `paper/PAPER_WORK.md`, replace every `BEST` token with the config name, resolve every `[GROK: ...]` note, then `python3 kit/fill_paper.py paper/PAPER_WORK.md results/claims.json paper/PAPER.md`. It must exit 0. If a key is missing because an experiment was cut, delete that row or sentence in `PAPER_WORK.md` and add a Limitations line; never type a number to fill a gap. Replace any `nan%` acceptance cell with "not reported" and say in Setup that this build does not report draft counts for that config.
H3. Citations: open every source before citing it (web search, then the page). Required reading for the introduction and related work, with what to extract:
- Gemma 4 Technical Report, arXiv 2607.02770, section 2.6 "Multi-Token Prediction Drafter";
- Google AI for Developers, Gemma 4 model overview (all models include a draft model for speculative decoding);
- the Hugging Face card `google/gemma-4-12B-it-assistant`;
- llama.cpp pull request 23398 "llama: add Gemma4 MTP" and the llama.cpp speculative decoding documentation;
- Leviathan, Kalman, Matias, "Fast Inference from Transformers via Speculative Decoding", ICML 2023; Chen et al., "Accelerating Large Language Model Decoding with Speculative Sampling", 2023; Li et al., EAGLE, 2024;
- "An Empirical Study of Speculative Decoding on Software Engineering Tasks", arXiv 2604.26469 (read the abstract and state the difference: this paper measures Gemma 4's shipped drafters inside an agent loop on a laptop with byte-identity checks);
- competition notebooks on Kaggle: "The Budget Is a Token Budget" (xingling666), "Gemma 4: A 16384 Output Cap Refuses Long Prompts" (dariushafshar), "Hardware decode physics, the 12-call cliff..." (pablodiegoo); the GitHub repo `yosh95/g4-developer-agent-paper` ("Every Tool Call Is a Token You Cannot Buy Back"); `yuvrajtiwary-bitmesraece/gemma4-many-labs`;
- SWE-bench (Jimenez et al., 2024) and SWE-agent (Yang et al., 2024).
Drop any item you cannot open. Never cite from memory.
H4. Quality bar before you call the paper done:
- the abstract states the question, the setup in one clause, the headline number with its interval, the identity rate next to the rerun control, and one limitation;
- every table cell and every number in prose is produced by the fill script or copied from `env/*.json`;
- section 5 lists every cut and every deviation in `DEVIATIONS.md`;
- no sentence claims more than the data: say "decode speedup", not "agent speedup", unless you measured wall clock of full trajectories; say "byte-identical output on X% of steps", not "always identical", unless X is 100;
- word count of `paper/PAPER.md` is at most 2,900 (`wc -w`); cut related work and setup detail first;
- no em dashes (`grep -c "$(printf '\xe2\x80\x94')" paper/PAPER.md` prints 0), no `[GROK` (`grep -c "GROK" paper/PAPER.md` prints 0), no `{{`.
H5. Read the finished paper once from top to bottom as a judge would, fix unclear sentences, rerun the fill script, commit. Gate G4.

## 12. Phase I: release and submission pack (50 minutes)

I1. `README.md`: what the project shows (three lines with the headline numbers from claims), how to rerun (the commands from sections 6 to 10), what is and is not released and why, license Apache-2.0. Add `LICENSE` (Apache-2.0 text).
I2. `python3 kit/make_notebook.py release/records.csv results/claims.json notebook/free_speed_reproduce.ipynb "<paper title>: reproduce every number"`. Test it and confirm it prints `ALL PAPER NUMBERS REPRODUCED`:
```
python3 - <<'PY'
import json, matplotlib; matplotlib.use("Agg")
nb = json.load(open("notebook/free_speed_reproduce.ipynb")); g = {}
for c in nb["cells"]:
    if c["cell_type"] == "code": exec("".join(c["source"]), g)
PY
```
I3. `git status --short` and `git ls-files | grep -E "workloads|results/raw|tasks.jsonl|\.gguf"` must show nothing tracked from the forbidden list (rule 10). Commit.
I4. GitHub: if `gh auth status` succeeds, `gh repo create free-speed-gemma4 --public --source . --push` (if the name is taken, append `-paper`). Record the URL. If `gh` is not authenticated, skip and put the three commands for OJ in `SUBMISSION/README.md`.
I5. Kaggle notebook: if `kaggle kernels list --mine` works, create `notebook/kernel-metadata.json` (`"id": "<kaggle username>/free-speed-reproduce"`, `"title"`, `"code_file": "free_speed_reproduce.ipynb"`, `"language": "python"`, `"kernel_type": "notebook"`, `"is_private": false`, `"enable_gpu": false`, `"enable_internet": false`, `"competition_sources": ["gemma-4-developer-agent-paper"]`) and `kaggle kernels push -p notebook`. Record the URL. If the CLI is not set up, skip and add manual upload steps to `SUBMISSION/README.md`.
I6. Put the repo and notebook URLs into `paper/PAPER_WORK.md`, refill, recheck H4's greps and word count.
I7. Build `SUBMISSION/`: `TITLE.txt`, `SUBTITLE.txt`, `BODY.md` (the paper without the title, subtitle and author lines, images referenced by their GitHub raw URLs if the repo is public, otherwise list the image files to upload by hand), `cover.png`, `fig_speedup.png`, `fig_by_kind.png`, `LINKS.txt`, and `README.md` with the exact manual steps for OJ:
  1. kaggle.com/competitions/gemma-4-developer-agent-paper, Join Hackathon (both authors), merge into one team.
  2. Writeups, New Writeup. Paste title, subtitle, body; upload the cover image and figures; add the GitHub and notebook links under Project Links.
  3. Click **Submit** and confirm the page shows "Submitted". Deadline 15:59 Pacific; do it by 14:30.
I8. Final commit and push. Gate G5. Then send the handoff message (section 14).

## 13. Failure playbook

| Problem | Do this, then continue |
|---|---|
| `brew` missing or `brew install llama.cpp` fails | build from source (A5) |
| help text has no `draft-mtp` even after upgrade and source build | drop `mtp` and `mtp_ngram`; make `e2b_draft` (classic draft model) and `ngram` the study; retitle around prompt lookup and small-model drafting |
| Hugging Face download fails or is gated | next candidate repo; then `llama-server -hf <repo>:<quant>` to let llama.cpp fetch it and copy the file from its cache |
| drafter fails to load with the target ("requires ctx_other", shape mismatch) | drafter and target sizes or builds do not match: try the drafter from the same repo family as the target; then the other target candidate; then B3 |
| server exits with out-of-memory or the machine swaps | `-c 8192`; stop Ollama models; for `e2b_draft` skip the config |
| a server start hangs past 10 minutes | `pkill -f llama-server`, check the log, fix the flag, rerun the same bench command (it resumes) |
| `bench.py` rows show `ok: false` for one config | read `logs/server_<target>_<config>.log`, fix the config's flags **only if still before the freeze (E4)**; after the freeze, report the config as failed on this build |
| draft counts missing from `timings` | acceptance comes from the server log; if not available, write "not reported" in the table |
| thinking cannot be switched | see C4 |
| Kaggle data not found | git fallback (D2) and say so in the paper |
| agent replies are not valid tool calls | F2 fallback (thinking off); if still invalid for most steps, cut W2, make W1 the headline, say so in the abstract |
| speedup below 1 for every config | this is the result: use the second title, explain with acceptance rates and step types, and keep every other part of the plan |
| outputs differ from baseline more than the rerun control | report it, analyze first-difference positions (3.3), and do not call that config lossless |
| `fill_paper.py` lists missing keys | delete those rows or sentences, add a Limitations line |
| `gh` or `kaggle` CLI not authenticated | skip, document the manual steps in `SUBMISSION/README.md` |
| you are past a gate | apply the cut list in section 2 |
| anything not listed | choose the option that keeps the paper truthful and on time, log one line, continue |

## 14. Handoff message (your final output, by 13:50)

End your work with exactly this structure, filled in:

```
FREE SPEED: READY TO SUBMIT
Title: ...
Headline: 12B decodes {H}x faster (95% CI ...), identical output on ...% of steps (rerun control ...%)
Paper: SUBMISSION/BODY.md (N words)   Cover: SUBMISSION/cover.png
Repo: <url or "not pushed: run the 3 commands in SUBMISSION/README.md">
Notebook: <url or "upload notebook/free_speed_reproduce.ipynb by hand">
What was cut: ...
What OJ must do now (3 steps, by 14:30 Pacific): join + team, paste Writeup, click Submit and check "Submitted".
```

## 15. Facts checked on 12 Nov 2026 (use, but verify on your build)

- Google's Gemma 4 overview: all Gemma 4 models (E2B, E4B, 12B, 31B, 26B A4B) include a dedicated draft model for speculative decoding. The technical report (arXiv 2607.02770, section 2.6) describes the MTP drafter head.
- llama.cpp runs these drafters with `--spec-type draft-mtp` plus the drafter file as the draft model. Recent builds list `--spec-type none,draft-simple,draft-eagle3,draft-mtp,draft-dflash,draft-dspark,ngram-simple,ngram-map-k,ngram-map-k4v,ngram-mod,ngram-cache` as a comma-separated list, `--spec-draft-n-max` (default 3), `--spec-draft-n-min`, `--spec-draft-p-min`, `-ngld`, and `--spec-ngram-*` tuning flags. Older flag names (`--draft-max`, `--draft-min`) were removed.
- Public reports say `--parallel 1` and flash attention matter for speculative decoding, and that for the Gemma 4 head a draft length of 2 often beats 3 and 4 because acceptance falls with depth.
- Official GGUF repos follow the pattern `google/gemma-4-<SIZE>-it-qat-q4_0-gguf`; `unsloth/gemma-4-12B-it-qat-GGUF` documents `--spec-type draft-mtp --spec-draft-n-max 4`.
- Public dev set: 129 tasks (fastapi 67, rich 48, requests 13, httpx 1). Allowed competition models: 31B, 12B, E4B, E2B (QAT 4-bit).
- Many Labs pooled record: 15,112 attempts, 14 labs; `tasks.csv` has `audit_status` (67 tasks are `valid`); `attempts.csv` has columns `task, y, model` with models `31B`, `E4B`, `E2B`.

Start now with step A1.
