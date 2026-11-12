<!--
GROK: this is the paper skeleton. Rules:
1. Replace every token BEST with the name of the best lossless config (ANALYSIS_PLAN.md section 4), then run
   python3 kit/fill_paper.py paper/PAPER_TEMPLATE.md results/claims.json paper/PAPER.md
   It must exit 0. Numbers come only from {{...}} placeholders.
2. Every [GROK: ...] note is an instruction. Follow it, then delete it. No bracket notes may remain.
3. If an experiment did not run, delete its sentences and table rows and add one line to Limitations.
4. No em dashes. No company affiliation. Final text under 2,900 words (the limit is 3,000).
5. Delete this comment block.
-->

# [GROK: title by the title rule in the master prompt, section 11]

### [GROK: subtitle by the subtitle rule]

**Anni Zimina, Orkhan Javadli**

## Abstract

Three entries in this competition showed that a Gemma 4 coding agent spends most of its wall-clock budget generating tokens. None of them made a token cheaper. Gemma 4 ships a small multi-token-prediction (MTP) drafter with every model, built for speculative decoding, and no public entry we could find used it. We measure what that drafter, prompt-lookup (n-gram) drafting, and the two stacked together do to a Gemma 4 coding agent on a 24 GB MacBook. On {{W2.12b.BEST.ALL.n_pairs}} recorded agent steps from {{W2.12b.BEST.ALL.n_clusters}} repair trajectories, the best setting decodes Gemma 4 12B {{W2.12b.BEST.ALL.speedup|.2f}} times faster (95% CI {{W2.12b.BEST.ALL.speedup_lo|.2f}} to {{W2.12b.BEST.ALL.speedup_hi|.2f}}) and returns byte-identical output on {{W2.12b.BEST.ALL.identity_rate|pct}} of steps, against {{W1.12b.baseline_rerun.ALL.identity_rate|pct}} when the unmodified baseline is simply run twice. On {{W1.12b.BEST.ALL.n_pairs}} single-turn repair edits the speedup is {{W1.12b.BEST.ALL.speedup|.2f}} times for 12B and {{W1.e4b.BEST.ALL.speedup|.2f}} times for E4B. [GROK: one sentence on which step type gains most and which gains least, with the two numbers.] The speedup needs no training, no prompt change and no second GPU. We release the harness, per-step records and a CPU notebook that rebuilds every number.

## 1. Introduction

The Gemma 4 Developer Agent competition asks for an agent that fixes real bugs offline on consumer hardware inside a fixed time budget. Public analyses from participants agree on where that budget goes. [GROK: cite, with the exact figure from each source after you open it: "The Budget Is a Token Budget" (generation share of wall clock), "Gemma 4: A 16384 Output Cap Refuses Long Prompts" (model calls as a share of agent time), and "Every Tool Call Is a Token You Cannot Buy Back". Two sentences.] If time is tokens, there are two ways to get more work from the same budget: generate fewer tokens, or generate each token faster. Almost all agent engineering in this competition does the first. This paper does the second, and does it without changing what the model writes.

Speculative decoding drafts several tokens cheaply and lets the full model verify them in one batched pass. Accepted tokens are exactly the tokens the model would have produced, so quality is unchanged by construction. Gemma 4 is unusual in shipping an official drafter head for every model size. Coding agents are also an unusually good fit for a second kind of drafting: much of what an agent emits is copied from its own context, such as file paths, the lines it is about to replace, and tool-call boilerplate. A drafter that looks up the continuation of the last few tokens in the prompt costs nothing and is right whenever the model copies.

Contributions:

1. The first measurement, to our knowledge, of Gemma 4's MTP drafters inside a coding-agent loop, with step-level pairing and a byte-identity check against the undrafted model.
2. A comparison of four drafting options on the same prompts: the official MTP drafter, prompt lookup, both stacked, and [GROK: keep "a small Gemma 4 model used as a classic draft model" only if e2b_draft ran].
3. A breakdown by agent step type that shows where drafting pays and where it does not.
4. A reusable harness (one command per experiment, resumable, block-randomized against thermal drift) and released per-step records.

## 2. Setup

**Hardware and software.** [GROK: one sentence from env/machine.json: MacBook Pro, Apple M4 Pro, 24 GB unified memory; llama.cpp build id; Metal backend; AC power.] All layers of the target and the drafter run on the GPU. Flash attention on, one slot, context [GROK: the -c value in configs.json], KV cache at default precision.

**Models.** Gemma 4 12B and E4B, quantization-aware-trained 4-bit GGUF files [GROK: exact file names and SHA-256 prefixes from env/models.json]. Both are on the competition's list of allowed models. Each is paired with its own MTP drafter [GROK: file names and sizes].

**Decoding configs.** `baseline`: no drafting. `mtp`: the official drafter, draft length [GROK: frozen value]. `ngram`: prompt-lookup drafting from the token history, no extra model [GROK: frozen type and flags]. `mtp_ngram`: both. `baseline_rerun`: the baseline launched a second time as a noise control. [GROK: add e2b_draft if it ran.] Greedy decoding unless stated.

**Workloads.** W1 has one repair prompt per public development task: the issue text and up to 220 lines of the file the reference fix touches, with the model asked for search-and-replace edit blocks (thinking off, at most 512 new tokens). W2 is an agent loop with four tools (search, read file, edit file, submit) on a checkout of each task's base commit, thinking on, tool outputs capped at 5,000 characters as in the competition harness. We record trajectories once with the baseline, then replay every recorded request under every config, so each step is compared on exactly the same context. If every step's output is identical, the whole trajectory and its final patch are identical, because the tools are deterministic.

**Design.** Twelve tasks, fixed by hash before any run, were used to choose the n-gram type and the draft length and are excluded from all results. Each config gets its own server launch per block of prompts, and config order rotates across blocks. The analysis plan was committed before the first test-split run [GROK: commit hash].

**Metrics.** Decode speedup is the ratio of tokens per second, pooled over paired prompts, with a 95% interval from 2,000 bootstrap resamples of tasks. Identity is the share of prompts whose full output (thinking plus answer) matches the baseline byte for byte, with a Wilson interval.

## 3. Results

### 3.1 Same output, faster

[GROK: insert figures/fig_speedup.png here with a one-line caption.]

| Workload | Model | Config | Prompts | Identical to baseline | Speedup (95% CI) | Draft acceptance |
|---|---|---|---|---|---|---|
| W1 edit | 12B | baseline_rerun | {{W1.12b.baseline_rerun.ALL.n_pairs}} | {{W1.12b.baseline_rerun.ALL.identity_rate|pct}} | {{W1.12b.baseline_rerun.ALL.speedup|.2f}} ({{W1.12b.baseline_rerun.ALL.speedup_lo|.2f}} to {{W1.12b.baseline_rerun.ALL.speedup_hi|.2f}}) | n/a |
| W1 edit | 12B | mtp | {{W1.12b.mtp.ALL.n_pairs}} | {{W1.12b.mtp.ALL.identity_rate|pct}} | {{W1.12b.mtp.ALL.speedup|.2f}} ({{W1.12b.mtp.ALL.speedup_lo|.2f}} to {{W1.12b.mtp.ALL.speedup_hi|.2f}}) | {{W1.12b.mtp.ALL.accept_rate|pct}} |
| W1 edit | 12B | ngram | {{W1.12b.ngram.ALL.n_pairs}} | {{W1.12b.ngram.ALL.identity_rate|pct}} | {{W1.12b.ngram.ALL.speedup|.2f}} ({{W1.12b.ngram.ALL.speedup_lo|.2f}} to {{W1.12b.ngram.ALL.speedup_hi|.2f}}) | {{W1.12b.ngram.ALL.accept_rate|pct}} |
| W1 edit | 12B | mtp_ngram | {{W1.12b.mtp_ngram.ALL.n_pairs}} | {{W1.12b.mtp_ngram.ALL.identity_rate|pct}} | {{W1.12b.mtp_ngram.ALL.speedup|.2f}} ({{W1.12b.mtp_ngram.ALL.speedup_lo|.2f}} to {{W1.12b.mtp_ngram.ALL.speedup_hi|.2f}}) | {{W1.12b.mtp_ngram.ALL.accept_rate|pct}} |
| W2 agent | 12B | mtp | {{W2.12b.mtp.ALL.n_pairs}} | {{W2.12b.mtp.ALL.identity_rate|pct}} | {{W2.12b.mtp.ALL.speedup|.2f}} ({{W2.12b.mtp.ALL.speedup_lo|.2f}} to {{W2.12b.mtp.ALL.speedup_hi|.2f}}) | {{W2.12b.mtp.ALL.accept_rate|pct}} |
| W2 agent | 12B | ngram | {{W2.12b.ngram.ALL.n_pairs}} | {{W2.12b.ngram.ALL.identity_rate|pct}} | {{W2.12b.ngram.ALL.speedup|.2f}} ({{W2.12b.ngram.ALL.speedup_lo|.2f}} to {{W2.12b.ngram.ALL.speedup_hi|.2f}}) | {{W2.12b.ngram.ALL.accept_rate|pct}} |
| W2 agent | 12B | mtp_ngram | {{W2.12b.mtp_ngram.ALL.n_pairs}} | {{W2.12b.mtp_ngram.ALL.identity_rate|pct}} | {{W2.12b.mtp_ngram.ALL.speedup|.2f}} ({{W2.12b.mtp_ngram.ALL.speedup_lo|.2f}} to {{W2.12b.mtp_ngram.ALL.speedup_hi|.2f}}) | {{W2.12b.mtp_ngram.ALL.accept_rate|pct}} |
| W1 edit | E4B | mtp | {{W1.e4b.mtp.ALL.n_pairs}} | {{W1.e4b.mtp.ALL.identity_rate|pct}} | {{W1.e4b.mtp.ALL.speedup|.2f}} ({{W1.e4b.mtp.ALL.speedup_lo|.2f}} to {{W1.e4b.mtp.ALL.speedup_hi|.2f}}) | {{W1.e4b.mtp.ALL.accept_rate|pct}} |
| W1 edit | E4B | ngram | {{W1.e4b.ngram.ALL.n_pairs}} | {{W1.e4b.ngram.ALL.identity_rate|pct}} | {{W1.e4b.ngram.ALL.speedup|.2f}} ({{W1.e4b.ngram.ALL.speedup_lo|.2f}} to {{W1.e4b.ngram.ALL.speedup_hi|.2f}}) | {{W1.e4b.ngram.ALL.accept_rate|pct}} |
| W1 edit | E4B | mtp_ngram | {{W1.e4b.mtp_ngram.ALL.n_pairs}} | {{W1.e4b.mtp_ngram.ALL.identity_rate|pct}} | {{W1.e4b.mtp_ngram.ALL.speedup|.2f}} ({{W1.e4b.mtp_ngram.ALL.speedup_lo|.2f}} to {{W1.e4b.mtp_ngram.ALL.speedup_hi|.2f}}) | {{W1.e4b.mtp_ngram.ALL.accept_rate|pct}} |

[GROK: three to five sentences reading the table. State the baseline speed in tokens per second from claims (base_tps), the best config's speed (cfg_tps), and what the baseline_rerun row says about noise. In W2, {{W2.12b.BEST.ALL.clusters_all_identical_rate|pct}} of trajectories had every step identical. If any config is slower than baseline, say so plainly.]

### 3.2 Where drafting pays inside an agent

[GROK: insert figures/fig_by_kind.png. Report W2 speedup of BEST for navigate, edit and submit steps from claims keys W2.12b.BEST.navigate.speedup, W2.12b.BEST.edit.speedup, W2.12b.BEST.submit.speedup (use only kinds that exist, with n_pairs). Explain the pattern in two or three sentences using acceptance rates and the mean thinking share (mean_think_share). Do not speculate beyond the numbers.]

### 3.3 When outputs differ

[GROK: if any drafted config has identity below the baseline_rerun rate, report how many prompts differ, where the first difference falls (median first_diff_frac from results/tables/pairs.csv), and show that the same happens between two baseline launches if it does. If all are identical, say so in one sentence and delete the rest of this note.]

### 3.4 Sampling

[GROK: W1s result in two sentences: identity rate and speedup at temperature 1.0 with a fixed seed, from keys W1s.12b.BEST.ALL.*. Delete the section if W1s did not run.]

### 3.5 What the time buys

At the measured W2 speedup, 100 agent steps save {{W2.12b.BEST.ALL.gen_seconds_saved_per_100_steps|.0f}} seconds of generation on this laptop. [GROK: one sentence converting the speedup into extra generated tokens per hour at the measured tokens per second.] As an upper bound on what that could be worth, we use the pooled public record of 15,112 agent attempts on the development set (Many Labs, One Benchmark). [GROK: from results/projection.json report the single-attempt rate and the oracle rate at the measured speedup for 31B and E4B on valid tasks, and state in the same sentence that this assumes the saved time funds further independent attempts and a perfect choice among them, so it is a ceiling, not a prediction.]

## 4. Related work

[GROK: 180 to 230 words. Verify each item by opening it; drop anything you cannot verify. Speculative decoding (Leviathan et al., 2023; Chen et al., 2023). EAGLE-style drafter heads (Li et al., 2024). The Gemma 4 Technical Report, section 2.6, and the Gemma 4 assistant model cards. Prompt lookup decoding (Saxena, 2023). llama.cpp speculative decoding documentation and the pull request that added Gemma 4 MTP. "An Empirical Study of Speculative Decoding on Software Engineering Tasks" (arXiv 2604.26469): say how this paper differs after reading its abstract. Public measurements of Gemma 4 drafters on chat prompts and small GPUs: say that ours is a coding-agent loop with step-level identity checks and stacking with prompt lookup. The competition entries cited in the introduction, Many Labs, SWE-bench and SWE-agent.]

## 5. Limitations

One laptop, one inference engine, two model sizes. The 31B model does not fit in 24 GB of unified memory, so the competition's main model is not measured here; the method and harness apply unchanged. W2 uses our own minimal agent loop, not the competition harness, and {{W2.12b.BEST.ALL.n_clusters}} trajectories. Step replay measures decoding on the baseline's contexts; it does not measure end-to-end resolution, which identical outputs leave unchanged by construction. Speedups depend on hardware and on how much of the output is copied from context. [GROK: add any experiment that was cut, and the power state if the laptop was on battery.]

## 6. Recommendations

For anyone running a Gemma 4 agent locally: [GROK: the exact llama-server flags of BEST in one code line]. For benchmark organizers: the drafters ship next to the models, and the serving stack used for scoring supports speculative decoding, so enabling it would give every entrant more steps inside the same time budget without changing any agent's output. [GROK: keep the second sentence only if you verified in vLLM documentation that MTP or n-gram speculative decoding is supported, and cite it.]

## Reproducibility

Code, the frozen analysis plan, per-step records without model text and the CPU notebook: [GROK: repo URL and notebook URL]. Every number above is filled from `results/claims.json` by script.

## References

[GROK: numbered list, each with a URL you opened today.]
