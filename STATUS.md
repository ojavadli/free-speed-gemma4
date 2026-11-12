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
- [ ] E2 tune run (04:48 restarted) full-GPU partial run discarded. GPU cap: 12B -ngl 19 of 48, E4B -ngl 17 of 42, drafter -ngld 1. Baseline under the cap is about 15 to 17 tok/s. Deadline 06:15.
- [ ] E3 pick winners
- [ ] E4 freeze plan G2
- [ ] F1 W1 12B
- [ ] F2 W2 record and replay
- [ ] F3 W1 E4B
- [ ] F4 W1s sampling
- [ ] F5 optional e2b_draft
- [ ] G1 analyze
- [ ] G2 projection
- [ ] G3 QA
- [ ] G4 BEST and H
- [ ] G5 cover
- [ ] H1 title
- [ ] H2 fill paper
- [ ] H3 citations
- [ ] H4 quality bar
- [ ] H5 read-through G4
- [ ] I1 README and LICENSE
- [ ] I2 notebook
- [ ] I3 git hygiene
- [ ] I4 GitHub
- [ ] I5 Kaggle notebook
- [ ] I6 refill paper
- [ ] I7 SUBMISSION pack
- [ ] I8 final commit G5

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
