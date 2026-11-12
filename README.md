# Free Speed?

A laptop measurement of Gemma 4's shipped multi-token-prediction drafter and of prompt-lookup drafting, inside coding-agent prompts.

On this machine (Apple M4 Pro, 24 GB, context 8192):

- Full GPU, every E4B block: the fair comparison is against the second undrafted launch, which matched every token. MTP plus prompt lookup was 3.60 times faster (95 percent interval 3.09 to 4.32) on 24 of 24 prompts. MTP alone was 3.07 times faster (interval 2.73 to 3.52), also identical on all 24.
- Against the colder first launch those ratios are 3.97 and 3.38. The second launch itself was 1.10 times the first (interval 1.01 to 1.21).
- The capped 12B runs did not clear the same bar. A second undrafted 12B launch changed speed by 1.46 times with identical text.

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
