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
- FROZEN n-gram type and flags:
- FROZEN MTP draft length (--spec-draft-n-max):
- FROZEN llama.cpp build, model files and SHA-256:
