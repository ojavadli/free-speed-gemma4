# FREE SPEED: analysis plan (frozen before any test-split run)

Fill the three FROZEN lines in section 5, commit this file, and record the commit hash in STATUS.md
before the first run on the test split. Later changes go in DEVIATIONS.md with a timestamp and a reason.

## 1. Question
Do Gemma 4's own multi-token-prediction (MTP) drafters and prompt-lookup (n-gram) drafting make a Gemma 4
coding agent faster on a 24 GB laptop without changing its output, and by how much in each kind of agent step?

## 2. Design
Paired, within-prompt. Every prompt is decoded by the same target model under every decoding config.
Greedy decoding (temperature 0) in the main experiments. One server launch per (block, config); config order
rotates across blocks so heat and background load are spread evenly. A second baseline launch
(`baseline_rerun`) measures the noise floor of both identity and speed.

- W1 (edit): one repair prompt per public dev task, thinking off, max 512 new tokens. 12 tasks with the smallest
  sha1(task id) are the tuning split and are never reported. Rows are written in sha1 order, so the test set
  (the first 48 test-split rows) is a hash-random sample across the four repositories.
- W2 (agent): 8 multi-step trajectories recorded with the baseline server (thinking on), then every recorded
  request is replayed under each config. Task ids are the 8 test-split tasks with the smallest sha1(task id)
  that are not in the tuning split, at least 2 per repository where possible.
- W1s (sampling): 20 test prompts at temperature 1.0, top-k 64, top-p 0.95, fixed seed, baseline vs the best config.

## 3. Outcomes
- Primary: decode speedup = (tokens per second under the config) / (tokens per second under baseline), pooled over
  paired prompts; 95% interval from 2,000 bootstrap resamples of tasks.
- Co-primary: identity rate = share of prompts whose full output (thinking plus answer) is byte-identical to
  baseline; Wilson 95% interval. Reported next to the `baseline_rerun` identity rate.
- Secondary: speedup by step type (navigate, edit, submit), draft acceptance rate, share of prompts that got slower,
  share of W2 trajectories in which every step is identical, speedup under sampling.

## 4. Rules
- Tuning (drafting type, draft length) uses the tuning split only.
- A config counts as lossless if its identity rate is at least the `baseline_rerun` identity rate minus 2 points.
- Headline number H = W2 12B speedup of the best lossless config. If W2 did not finish, H = the W1 12B value and
  the paper says so in the abstract.
- A speedup below 1 is reported as measured. No prompt is dropped except for request errors, which are counted.
- Projection of extra resolved tasks is labelled an upper bound (oracle choice among attempts) and is never the headline.

## 5. Frozen choices (fill before the test split)
- FROZEN n-gram type and flags: ngram-map-k4v, default n-gram parameters. On the tuning split this was the only n-gram type with a 100 percent identity rate (11 of 11). ngram-simple was faster (speedup 2.03) but identical on 10 of 11, so it was not selected.
- FROZEN MTP draft length (--spec-draft-n-max): 4. All three lengths were identical on 11 of 11. Length 4 had the highest speedup (2.05), ahead of length 2 (1.60) and length 3 (0.68).
- FROZEN llama.cpp build, model files and SHA-256: llama-server 0.9.0, build 12110, commit cd959bae9. GPU cap: 12B -ngl 19 of 48 blocks, E4B -ngl 17 of 42, drafter -ngld 1, context 8192. TARGET_12B google/gemma-4-12B-it-qat-q4_0-gguf gemma-4-12b-it-qat-q4_0.gguf sha256 93567e57a8fe10b23569b9d9ec38cd005deedf71e29477c421a4b83f418a538b. MTP_12B unsloth/gemma-4-12B-it-qat-GGUF MTP/mtp-gemma-4-12B-it-Q4_0.gguf sha256 fcb35dea42c71333db904cee11baac525c9ef872818ee3753f6cb156f3c6f4f6. TARGET_E4B google/gemma-4-E4B-it-qat-q4_0-gguf gemma-4-E4B_q4_0-it.gguf sha256 676c35070db6dbe52f93e9c864ee0fba4eddea94b9c875d9cb10daff453fbaee. MTP_E4B unsloth/gemma-4-E4B-it-qat-GGUF MTP/mtp-gemma-4-E4B-it-Q4_0.gguf sha256 423074e537504b4f9ec5eafed5c639fac82c96631626efccacdd3c4039b20605.
