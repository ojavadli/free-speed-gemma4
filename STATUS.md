# FREE SPEED status

Start: 04:15 Pacific, 2026-11-12.

Clock at start: 04:15. Gates are not shifted. G1 is 05:45.

## Checklist

- [x] A1 setup folders, git, gitignore (04:15)
- [x] A2 machine facts (04:16) M4 Pro, 24 GB, macOS 15.5, AC Power, 51 GB free, low power mode not set
- [x] A3 python venv (04:16) numpy 2.0.2
- [x] A4 selftest (04:17) SELFTEST PASS, then _selftest removed. Mock numbers are not for the paper.
- [x] A5 llama-server (04:18) /opt/homebrew/bin/llama-server 0.9.0 build 12110 commit cd959bae9. Help lists draft-mtp and ngram types.
- [x] A6 flag mapping (04:18) see below
- [x] B1 find models (04:18) logs/find_12b.log and logs/find_e4b.log
- [x] B2 download models (04:34) four GGUFs on disk. SHA-256 in env/models.json
- [x] B3 drafter fallback not needed. Official Google QAT repos had no MTP GGUF, so Unsloth QAT Q4_0 MTP files were used (same quantization family).
- [x] B4 configs.json (04:34) paths set. Flag names match the help text.
- [x] C1 smoke 12B (04:37) 12/12 ok. Baseline about 29 tok/s. MTP about 48 to 54 tok/s with draft counts in timings. Stack starts with --spec-type ngram-mod,draft-mtp and also reports draft counts. ngram-mod did not print draft acceptance in timings or the server log on these three short prompts, and its speed matched baseline.
- [x] C2 fix failing configs (04:37) stacking with ngram-mod,draft-mtp starts. No flag fix needed.
- [x] C3 smoke E4B (04:38) 12/12 ok. Baseline about 62 tok/s. MTP about 88 to 106 tok/s on the 200-token prompts.
- [x] C4 thinking probe (04:39) ON is chat_template_kwargs enable_thinking true. OFF is enable_thinking false. Default empty request thinks.
- [x] C5 req_sampling.json (04:39)
- [x] C6 commit G1 (04:39) smoke passed well before 05:45.
- [x] D1 tasks.jsonl (04:34) not found. kaggle CLI is not installed. Used the git fallback.
- [x] D2 build W1 (04:34) 127 rows, 11 tune, 116 test. Skipped httpx_3672 (merge-base failed). First 48 test rows: fastapi 22, rich 20, requests 6. Prompts contain an issue and a code excerpt. Source: public git history.
- [x] D3 W2 task ids (04:34) env/w2_tasks.txt: fastapi_15745,fastapi_14791,rich_2725,rich_3064,requests_6757,requests_7315,fastapi_15763,fastapi_14786
- [x] E1 tuning configs (04:39) ngram_simple, ngram_mod, ngram_k4v, mtp_n2, mtp_n3, mtp_n4 added for 12B.
- [x] E2 tune run (05:53) 77/77 finished under the GPU cap and context 8192. Baseline about 15.2 tok/s on the tuning split.
- [x] E3 pick winners (05:54) n-gram: ngram-map-k4v (only 100 percent identity, speedup 1.49). MTP draft length 4 (100 percent identity, speedup 2.05). ngram-simple was faster but identical on 10 of 11, so it was not selected.
- [x] E4 freeze plan G2 (05:54) commit da9abcac0dd72cec7a62ab960590f265576d28cc. Before the 06:20 gate.
- [x] F1 W1 12B (07:50) deadline reached cleanly. 147 rows kept in results/raw/W1_12b.jsonl. First-block sanity check at 06:28 paired and measured identity. Nothing was changed after seeing numbers.
- [x] F2 W2 record and replay (09:41) recording stopped at 08:30 with 53 steps. Replay deadline kept 123 of 152 rows. baseline_rerun dropped on W2 only.
- [x] F3 W1 E4B (10:09) limit 24, all 96 calls finished.
- [x] F4 W1s sampling (10:35) deadline reached at 30 of 40 calls. Used ngram because no config was lossless.
- [x] F5 optional e2b_draft cut. No E2B weights on disk.
- [x] G1 analyze (10:35) results/claims.json, release/records.csv, figures.
- [x] G2 projection (10:36) Many Labs clone. speedup_used 3.078 is the E4B MTP point estimate, labelled an upper bound in the paper.
- [x] G3 QA (10:36) ok_false 0. length share 15.2 percent. rerun speedup 1.46, outside 0.95 to 1.05. order position 0 mean 17.7 tok/s vs position 3 mean 12.3 tok/s. Two differing prompts inspected.
- [x] G4 BEST and H (10:36) No config is lossless. Closest 12B edit config is ngram, speedup 1.24, identity 96.9 percent, interval includes 1. E4B MTP speedup 3.08, interval 2.26 to 4.56, identity 91.7 percent.
- [x] G5 cover (10:36) figures/cover.png states the E4B result and that the text is not always the same.
- [x] H1 title (10:37) question-mark title, because BEST is not lossless.
- [x] H2 fill paper (10:38) fill_paper.py exit 0. 2761 words.
- [x] H3 citations opened 12 Nov 2026. See env/sources_opened.md. Two Kaggle notebooks were not re-opened today, so their exact percentages were removed from the paper.
- [x] H4 quality bar (10:38) em dash 0, GROK 0, no unfilled braces, 2761 words.
- [x] H5 read-through (10:38)
- [x] I1 README and LICENSE (10:37)
- [x] I2 notebook (10:37) printed ALL PAPER NUMBERS REPRODUCED.
- [x] I3 git hygiene (10:37) no workloads, raw results, tasks.jsonl, or gguf tracked.
- [x] I4 GitHub (10:37) https://github.com/ojavadli/free-speed-gemma4
- [x] I5 Kaggle notebook skipped. kaggle CLI is not installed. Manual steps are in SUBMISSION/README.md.
- [x] I6 refill paper (10:38) repo URL is in the paper.
- [x] I7 SUBMISSION pack (10:38)
- [x] I8 final commit and push. Handoff is early relative to 13:00.

## Flag mapping (A6, from env/llama_server_help.txt)

- draft model path: `-md` / `--spec-draft-model` / `--model-draft`
- draft GPU layers: `-ngld` / `--spec-draft-ngl` / `--gpu-layers-draft`
- draft length: `--spec-draft-n-max` (default 3)
- speculative type: `--spec-type` comma-separated. This build lists none, draft-simple, draft-eagle3, draft-mtp, draft-dflash, draft-dspark, ngram-simple, ngram-map-k, ngram-map-k4v, ngram-mod, ngram-cache
- n-gram tuning: `--spec-ngram-mod-n-min`, `--spec-ngram-mod-n-max`, `--spec-ngram-mod-n-match`, and the `*-size-n` / `*-size-m` / `*-min-hits` flags per n-gram type
- flash attention: `-fa on` / `--flash-attn on`
- reasoning: `--reasoning on|off|auto`, `--reasoning-budget N`, `--reasoning-format FORMAT`

configs.example.json flag names match this binary. No rename needed.

## Log

- 04:15 Unzipped freespeed_kit.zip into RESEARCH/freespeed. Working root is that folder so git init does not touch the rest of the research tree.
