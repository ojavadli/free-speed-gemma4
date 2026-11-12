# Free Speed?

A laptop measurement of Gemma 4's shipped multi-token-prediction drafter and of prompt-lookup drafting, inside coding-agent prompts.

On this machine (Apple M4 Pro, 24 GB, 19 of 48 blocks on the GPU, context 8192):

- E4B with the MTP drafter decoded paired repair prompts 3.08 times faster than the undrafted server (95 percent interval 2.26 to 4.56) and matched the text on 91.7 percent of 24 prompts.
- 12B prompt lookup matched on 96.9 percent of 32 prompts. The speed ratio was 1.24, and the interval includes 1.
- A second launch of undrafted 12B matched every token and still changed speed by 1.46 times (interval 0.92 to 2.52). That is outside the pre-registered noise band of 0.95 to 1.05.

## Rerun

The timed runs need llama.cpp `llama-server` 0.9.0 or newer with `draft-mtp`, the four GGUF files named in `env/models.json`, and `configs.json`. They are not in this repository. With those files in place:

```
python3 kit/bench.py --target e4b --configs baseline,mtp,ngram,mtp_ngram \
  --workload workloads/W1_edit.jsonl --split test --limit 24 \
  --out results/raw/W1_e4b.jsonl --tag W1 --request-file env/req_nothink.json \
  --block-size 8
python3 kit/analyze.py
```

`workloads/` and `results/raw/` are local. They are not published, because the prompts are derived from repository history used for this study and the raw files contain model text.

## What is released

Code under `kit/`, the frozen `ANALYSIS_PLAN.md`, `release/records.csv` (hashes and timings, no model text), figures, and `paper/PAPER.md`. The CPU notebook `notebook/free_speed_reproduce.ipynb` rebuilds the summary table from `release/records.csv`.

## What is not released

Model weights, prompt text, raw generations, cloned repositories, and caches. See `.gitignore`.

## License

Apache-2.0. See `LICENSE`.
