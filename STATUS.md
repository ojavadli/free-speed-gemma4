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
- [ ] B1 find models
- [ ] B2 download models
- [ ] B3 drafter fallback if needed
- [ ] B4 configs.json
- [ ] C1 smoke 12B
- [ ] C2 fix failing configs
- [ ] C3 smoke E4B
- [ ] C4 thinking probe
- [ ] C5 req_sampling.json
- [ ] C6 commit G1
- [ ] D1 tasks.jsonl
- [ ] D2 build W1
- [ ] D3 W2 task ids
- [ ] E1 tuning configs
- [ ] E2 tune run
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
