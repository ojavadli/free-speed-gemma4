# Free Speed: Same E4B Text, 3.6x Faster Decode on a Laptop

### On a 24 GB MacBook, with every E4B block on the GPU, MTP plus prompt lookup decoded the same repair text {{W1full.e4b.mtp_ngram.VS.speedup|.2f}} times faster than a repeated undrafted launch (95 percent interval {{W1full.e4b.mtp_ngram.VS.speedup_lo|.2f}} to {{W1full.e4b.mtp_ngram.VS.speedup_hi|.2f}}).

**Anni Zimina, Orkhan Javadli**

## Abstract

A Gemma 4 coding agent spends most of its time generating tokens. Gemma 4 ships a multi-token-prediction (MTP) drafter with every model, and prompt lookup can draft tokens by copying from the prompt. We asked whether those two drafters make the same prompts faster without changing the text, on a 24 GB MacBook. A follow-up put every E4B block on the GPU and launched the undrafted server twice on the same {{W1full.e4b.mtp.ALL.n_pairs}} repair prompts. The second launch matched every token and was {{W1full.e4b.baseline_rerun.ALL.speedup|.2f}} times the first, because the first block was cold, so the fair comparison is against that second launch. MTP plus prompt lookup then decoded at {{W1full.e4b.mtp_ngram.VS.speedup|.2f}} times that rate (95 percent interval {{W1full.e4b.mtp_ngram.VS.speedup_lo|.2f}} to {{W1full.e4b.mtp_ngram.VS.speedup_hi|.2f}}), and the full text matched on every prompt. MTP alone was {{W1full.e4b.mtp.VS.speedup|.2f}} times faster (interval {{W1full.e4b.mtp.VS.speedup_lo|.2f}} to {{W1full.e4b.mtp.VS.speedup_hi|.2f}}), also identical on every prompt. Where the text matches, the proposed patch matches: a repair the undrafted model would make, the drafted model makes too, and the drafter cannot change that outcome. Against the colder first launch those ratios are {{W1full.e4b.mtp_ngram.ALL.speedup|.2f}} and {{W1full.e4b.mtp.ALL.speedup|.2f}}. Counting prompt processing as well as decode, the MTP ratio is {{W1full.e4b.mtp.ALL.e2e_speedup_with_prefill|.2f}}.

## 1. Introduction

The Gemma 4 Developer Agent competition asks a local model to fix real bugs inside a fixed time budget. Public writeups in this track already treat that budget as a token budget: agents spend the clock generating text, and repeated tool calls waste calls without new information. The writeup "Every Tool Call Is a Token You Cannot Buy Back" reports that failing tasks took most of the wall clock on a small CPU host, and that chains of identical tool calls burned up to 34.6 percent of the calls in one failing configuration. If the clock is mostly tokens, there are two levers: emit fewer tokens, or emit each token faster. Almost every public notebook in this track pulls the first lever. This paper pulls the second, and checks whether the text stays the same.

Speculative decoding drafts several future tokens with a cheap method and lets the full model accept or reject them in one pass. Accepted tokens are the tokens the full model would have written, so the method is lossless when the implementation matches that rule. Gemma 4 trains a small autoregressive MTP head for this purpose. The technical report describes a 4-layer head that reads the main model's last-layer activations and KV cache, so the draft length is not fixed in the architecture. Google's model overview says every Gemma 4 size, including E2B, E4B, 12B, 31B, and 26B A4B, ships a draft model and that speculative decoding does not change quality. The Hugging Face card for the 12B assistant checkpoint says the same, and mentions speedups up to 3 times on that stack. llama.cpp exposes the head as `--spec-type draft-mtp` with a separate draft file.

Coding agents also repeat text that is already in the prompt: paths, the lines they are about to replace, and tool-call syntax. A lookup drafter, here an n-gram model over the token history, can propose those copies with no extra weights. Li, Chen, Hu, and Xia studied speculative decoding on software-engineering tasks and found that model-free lookup fits editing and repair better than a learned drafter does, while learned drafters fit open-ended generation. They also warn that agent loops can repeat themselves and distort a speed measurement. This paper is narrower. It uses only the drafters shipped for Gemma 4, inside one laptop server, and it compares each output byte for byte with an undrafted run of the same checkpoint. It also launches the undrafted server a second time, so identity and speed have a noise floor.

## 2. Setup

The machine is a MacBook with an Apple M4 Pro and 24 GB of unified memory, on AC power, running macOS 15.5. The server is llama.cpp `llama-server` 0.9.0, build 12110, commit cd959bae9, which lists `draft-mtp` and several n-gram types. After a full-GPU smoke test, the first measured runs were capped: 19 of 48 blocks for 12B, 17 of 42 blocks for E4B, and one draft-model layer. Context length is 8192. The cap and the shorter context are recorded in `DEVIATIONS.md`. They were set so the laptop would not swap or run the fan hard, not because a benchmark asked for them. After those runs, the same 24 E4B test prompts were repeated with every block on the GPU (`-ngl 999` and `-ngld 999`) and with a second undrafted launch. Context stayed 8192. That follow-up is tagged W1full. It was not part of the frozen 12B plan. Flash attention is on and there is one parallel slot.

The 12B target is `gemma-4-12b-it-qat-q4_0.gguf` from `google/gemma-4-12B-it-qat-q4_0-gguf` (SHA-256 prefix 93567e57). Its MTP file is `mtp-gemma-4-12B-it-Q4_0.gguf` from `unsloth/gemma-4-12B-it-qat-GGUF` (prefix fcb35dea). The official Google GGUF repo did not contain a drafter file. The E4B target is `gemma-4-E4B_q4_0-it.gguf` from `google/gemma-4-E4B-it-qat-q4_0-gguf` (prefix 676c3507), with `mtp-gemma-4-E4B-it-Q4_0.gguf` from the matching Unsloth QAT repo (prefix 423074e5). Both sizes are on the competition's allowed list.

Four decoding settings were frozen before any test-split prompt, in commit da9abcac. `baseline` is `--spec-type none`. `mtp` is `draft-mtp` with draft length 4. `ngram` is `ngram-map-k4v` at the build's default lookup sizes. `mtp_ngram` stacks `ngram-map-k4v,draft-mtp` at draft length 4. The tuning split had 11 prompts. Among n-gram types, only `ngram-map-k4v` was byte-identical on all 11, at a speedup of 1.49. `ngram-simple` was faster (2.03) but missed one prompt, so it was rejected. Among draft lengths 2, 3, and 4, all three were identical on all 11, and length 4 had the highest speedup (2.05). A second baseline, `baseline_rerun`, is the same server flags launched again. It is the noise control. Main prompts are greedy (temperature 0, seed 42). Thinking is off for single-turn edits, via `enable_thinking: false`, and on for recorded agent steps.

Workloads come from public git history of the 129 development-task pull requests, because the competition `tasks.jsonl` was not on disk and the Kaggle CLI was not installed. One pull request, `httpx_3672`, failed a merge-base lookup and was dropped. The builder wrote 127 prompts. Twelve hash-smallest task ids are the tuning split; one of those twelve was the dropped pull request, so 11 tuning prompts and 116 test prompts remain. Each prompt contains the pull-request commit messages, which stand in for the issue, and up to 220 lines around the reference edit. The model is asked for search-and-replace blocks, at most 512 new tokens. The first 48 test prompts would have been the 12B sample. The 07:50 deadline stopped that run at 147 of 240 server calls, so some configs have more paired prompts than others. E4B used the first 24 test prompts and finished all four configs (96 calls).

The agent workload is separate. Eight test tasks were chosen by hash, with at least two from fastapi, rich, and requests. A baseline server with thinking on drove a four-tool loop (search, read file, edit file, submit) for at most eight steps. Recording was stopped at 08:30, ten minutes after the planned stop, with 53 steps. Eight steps (15 percent) were not valid tool calls, which is below the rule that would have forced thinking off. Replay kept five trajectories (38 steps) and dropped `baseline_rerun` on this workload only. The 09:40 deadline then kept 123 of 152 replay calls.

Decode speedup is the ratio of pooled tokens per second. The 95 percent interval resamples tasks, 2000 times. Identity is an exact match of the full output, thinking plus answer, or of token ids when both sides stored them. A config is lossless only if its identity rate is at least the 12B rerun identity rate minus 2 points. The analysis plan was committed before the first test prompt.

## 3. Results

![Decode speedup with bootstrap intervals](https://github.com/ojavadli/free-speed-gemma4/raw/main/figures/fig_speedup.png)

| Workload | Model | Config | Prompts | Identical | Speedup (95 percent interval) | Draft acceptance |
|---|---|---|---|---|---|---|
| W1 edit | 12B | baseline_rerun | {{W1.12b.baseline_rerun.ALL.n_pairs}} | {{W1.12b.baseline_rerun.ALL.identity_rate|pct}} | {{W1.12b.baseline_rerun.ALL.speedup|.2f}} ({{W1.12b.baseline_rerun.ALL.speedup_lo|.2f}} to {{W1.12b.baseline_rerun.ALL.speedup_hi|.2f}}) | n/a |
| W1 edit | 12B | mtp | {{W1.12b.mtp.ALL.n_pairs}} | {{W1.12b.mtp.ALL.identity_rate|pct}} | {{W1.12b.mtp.ALL.speedup|.2f}} ({{W1.12b.mtp.ALL.speedup_lo|.2f}} to {{W1.12b.mtp.ALL.speedup_hi|.2f}}) | {{W1.12b.mtp.ALL.accept_rate|pct}} |
| W1 edit | 12B | ngram | {{W1.12b.ngram.ALL.n_pairs}} | {{W1.12b.ngram.ALL.identity_rate|pct}} | {{W1.12b.ngram.ALL.speedup|.2f}} ({{W1.12b.ngram.ALL.speedup_lo|.2f}} to {{W1.12b.ngram.ALL.speedup_hi|.2f}}) | {{W1.12b.ngram.ALL.accept_rate|pct}} |
| W1 edit | 12B | mtp_ngram | {{W1.12b.mtp_ngram.ALL.n_pairs}} | {{W1.12b.mtp_ngram.ALL.identity_rate|pct}} | {{W1.12b.mtp_ngram.ALL.speedup|.2f}} ({{W1.12b.mtp_ngram.ALL.speedup_lo|.2f}} to {{W1.12b.mtp_ngram.ALL.speedup_hi|.2f}}) | {{W1.12b.mtp_ngram.ALL.accept_rate|pct}} |
| W1 edit | E4B | mtp | {{W1.e4b.mtp.ALL.n_pairs}} | {{W1.e4b.mtp.ALL.identity_rate|pct}} | {{W1.e4b.mtp.ALL.speedup|.2f}} ({{W1.e4b.mtp.ALL.speedup_lo|.2f}} to {{W1.e4b.mtp.ALL.speedup_hi|.2f}}) | {{W1.e4b.mtp.ALL.accept_rate|pct}} |
| W1 edit | E4B | ngram | {{W1.e4b.ngram.ALL.n_pairs}} | {{W1.e4b.ngram.ALL.identity_rate|pct}} | {{W1.e4b.ngram.ALL.speedup|.2f}} ({{W1.e4b.ngram.ALL.speedup_lo|.2f}} to {{W1.e4b.ngram.ALL.speedup_hi|.2f}}) | {{W1.e4b.ngram.ALL.accept_rate|pct}} |
| W1 full GPU | E4B | baseline_rerun | {{W1full.e4b.baseline_rerun.ALL.n_pairs}} | {{W1full.e4b.baseline_rerun.ALL.identity_rate|pct}} | {{W1full.e4b.baseline_rerun.ALL.speedup|.2f}} ({{W1full.e4b.baseline_rerun.ALL.speedup_lo|.2f}} to {{W1full.e4b.baseline_rerun.ALL.speedup_hi|.2f}}) | n/a |
| W1 full GPU | E4B | mtp | {{W1full.e4b.mtp.ALL.n_pairs}} | {{W1full.e4b.mtp.ALL.identity_rate|pct}} | {{W1full.e4b.mtp.ALL.speedup|.2f}} ({{W1full.e4b.mtp.ALL.speedup_lo|.2f}} to {{W1full.e4b.mtp.ALL.speedup_hi|.2f}}) | {{W1full.e4b.mtp.ALL.accept_rate|pct}} |
| W1 full GPU | E4B | mtp_ngram | {{W1full.e4b.mtp_ngram.ALL.n_pairs}} | {{W1full.e4b.mtp_ngram.ALL.identity_rate|pct}} | {{W1full.e4b.mtp_ngram.ALL.speedup|.2f}} ({{W1full.e4b.mtp_ngram.ALL.speedup_lo|.2f}} to {{W1full.e4b.mtp_ngram.ALL.speedup_hi|.2f}}) | {{W1full.e4b.mtp_ngram.ALL.accept_rate|pct}} |
| W1 edit | E4B | mtp_ngram | {{W1.e4b.mtp_ngram.ALL.n_pairs}} | {{W1.e4b.mtp_ngram.ALL.identity_rate|pct}} | {{W1.e4b.mtp_ngram.ALL.speedup|.2f}} ({{W1.e4b.mtp_ngram.ALL.speedup_lo|.2f}} to {{W1.e4b.mtp_ngram.ALL.speedup_hi|.2f}}) | {{W1.e4b.mtp_ngram.ALL.accept_rate|pct}} |
| W2 agent | 12B | mtp | {{W2.12b.mtp.ALL.n_pairs}} | {{W2.12b.mtp.ALL.identity_rate|pct}} | {{W2.12b.mtp.ALL.speedup|.2f}} ({{W2.12b.mtp.ALL.speedup_lo|.2f}} to {{W2.12b.mtp.ALL.speedup_hi|.2f}}) | {{W2.12b.mtp.ALL.accept_rate|pct}} |
| W2 agent | 12B | ngram | {{W2.12b.ngram.ALL.n_pairs}} | {{W2.12b.ngram.ALL.identity_rate|pct}} | {{W2.12b.ngram.ALL.speedup|.2f}} ({{W2.12b.ngram.ALL.speedup_lo|.2f}} to {{W2.12b.ngram.ALL.speedup_hi|.2f}}) | {{W2.12b.ngram.ALL.accept_rate|pct}} |
| W2 agent | 12B | mtp_ngram | {{W2.12b.mtp_ngram.ALL.n_pairs}} | {{W2.12b.mtp_ngram.ALL.identity_rate|pct}} | {{W2.12b.mtp_ngram.ALL.speedup|.2f}} ({{W2.12b.mtp_ngram.ALL.speedup_lo|.2f}} to {{W2.12b.mtp_ngram.ALL.speedup_hi|.2f}}) | {{W2.12b.mtp_ngram.ALL.accept_rate|pct}} |
| W1s sample | 12B | ngram | {{W1s.12b.ngram.ALL.n_pairs}} | {{W1s.12b.ngram.ALL.identity_rate|pct}} | {{W1s.12b.ngram.ALL.speedup|.2f}} ({{W1s.12b.ngram.ALL.speedup_lo|.2f}} to {{W1s.12b.ngram.ALL.speedup_hi|.2f}}) | {{W1s.12b.ngram.ALL.accept_rate|pct}} |

No request failed (`ok` was true on all {{qa.n_rows}} raw rows). The undrafted 12B edit baseline produced about {{W1.12b.ngram.ALL.base_tps|.1f}} tokens per second on the prompts that also have an n-gram run, and the n-gram run produced {{W1.12b.ngram.ALL.cfg_tps|.1f}}. That ratio is {{W1.12b.ngram.ALL.speedup|.2f}}, but the interval runs from {{W1.12b.ngram.ALL.speedup_lo|.2f}} to {{W1.12b.ngram.ALL.speedup_hi|.2f}} and includes 1. MTP and the stack are in the same position: point estimates above 1, intervals that include 1, and identity of {{W1.12b.mtp.ALL.identity_rate|pct}} and {{W1.12b.mtp_ngram.ALL.identity_rate|pct}}. The rerun row is the reason. Two launches of the same undrafted 12B server, on {{W1.12b.baseline_rerun.ALL.n_pairs}} shared prompts, agreed on every token and still differed in speed by a factor of {{W1.12b.baseline_rerun.ALL.speedup|.2f}}. The pre-registered noise band was 0.95 to 1.05. This run missed it. Position in the rotating block also moved baseline speed: prompts in position 0 averaged {{qa.order_tps_0|.1f}} tokens per second and prompts in position 3 averaged {{qa.order_tps_3|.1f}}, a gap larger than 5 percent. Timing noise is high, and the bootstrap intervals are the right summary.

The full-GPU E4B follow-up is the result that clears the lossless rule. MTP plus prompt lookup decoded at {{W1full.e4b.mtp_ngram.ALL.speedup|.2f}} times the first baseline (interval {{W1full.e4b.mtp_ngram.ALL.speedup_lo|.2f}} to {{W1full.e4b.mtp_ngram.ALL.speedup_hi|.2f}}), with draft acceptance {{W1full.e4b.mtp_ngram.ALL.accept_rate|pct}} and the same text on all {{W1full.e4b.mtp_ngram.ALL.n_pairs}} prompts. MTP alone was {{W1full.e4b.mtp.ALL.speedup|.2f}} times faster (interval {{W1full.e4b.mtp.ALL.speedup_lo|.2f}} to {{W1full.e4b.mtp.ALL.speedup_hi|.2f}}), acceptance {{W1full.e4b.mtp.ALL.accept_rate|pct}}, also identical on every prompt. The second undrafted launch agreed on every token. Its speed ratio was {{W1full.e4b.baseline_rerun.ALL.speedup|.2f}} (interval {{W1full.e4b.baseline_rerun.ALL.speedup_lo|.2f}} to {{W1full.e4b.baseline_rerun.ALL.speedup_hi|.2f}}), outside the pre-registered band of 0.95 to 1.05. The first baseline block averaged {{qa.full_order_tps_0|.1f}} tokens per second, and later baseline blocks averaged {{qa.full_order_tps_2|.1f}} and {{qa.full_order_tps_3|.1f}}. The first server was cold. Against the second launch, MTP is still {{W1full.e4b.mtp.VS.speedup|.2f}} times faster (interval {{W1full.e4b.mtp.VS.speedup_lo|.2f}} to {{W1full.e4b.mtp.VS.speedup_hi|.2f}}) and the stack is {{W1full.e4b.mtp_ngram.VS.speedup|.2f}} (interval {{W1full.e4b.mtp_ngram.VS.speedup_lo|.2f}} to {{W1full.e4b.mtp_ngram.VS.speedup_hi|.2f}}). Adding prompt-processing time to decode time lowers the ratios to {{W1full.e4b.mtp.ALL.e2e_speedup_with_prefill|.2f}} for MTP and {{W1full.e4b.mtp_ngram.ALL.e2e_speedup_with_prefill|.2f}} for the stack. Decode is the pre-registered metric. The wall-clock ratio is smaller because the prompt is not drafted.

The earlier capped E4B run, 17 of 42 blocks, still has an MTP interval above 1 ({{W1.e4b.mtp.ALL.speedup|.2f}}, interval {{W1.e4b.mtp.ALL.speedup_lo|.2f}} to {{W1.e4b.mtp.ALL.speedup_hi|.2f}}), but identity was {{W1.e4b.mtp.ALL.identity_rate|pct}} and that run had no second baseline. The stack and the n-gram setting on that run were also faster than 1 inside their intervals, with identity {{W1.e4b.mtp_ngram.ALL.identity_rate|pct}} and {{W1.e4b.ngram.ALL.identity_rate|pct}}.

None of the 12B drafters is lossless under the frozen rule, because the rerun matched on {{W1.12b.baseline_rerun.ALL.identity_rate|pct}} and a drafter needed to stay within 2 points of that. The closest is prompt lookup at {{W1.12b.ngram.ALL.identity_rate|pct}}.

### 3.1 Where the text changes

On the full-GPU E4B prompts, both drafters and the second baseline matched the first baseline on every character. The capped E4B run did not. Its MTP setting disagreed on 2 of {{W1.e4b.mtp.ALL.n_pairs}} prompts, and both were read. For `fastapi_14791` the texts split about a quarter of the way through: the baseline keeps the validation schema, and the drafted text emits a `=======` marker and a shorter schema. For `rich_3296` they split in the first tenth, and both then hit the length limit. The baseline continues a width calculation. The drafted text starts `__rich_console__`. Those are different edits, not a last-token rounding difference. The same two prompts matched exactly when every block was on the GPU.

On 12B edits, MTP disagreed with baseline on 4 of {{W1.12b.mtp.ALL.n_pairs}} prompts, n-gram on 1 of {{W1.12b.ngram.ALL.n_pairs}}, and the stack on 5 of {{W1.12b.mtp_ngram.ALL.n_pairs}}. Two disagreements were read. For `rich_3938`, all three drafters leave the baseline text at about 65 percent of the way through the string: the baseline writes `and (` then `not any(`, and the drafted text writes `and not (` then `new_segments`. For `fastapi_14605`, MTP and the stack diverge at an import: the baseline continues with `class FastAPIDeprecationWarning`, and the drafted text inserts `from typing_extensions import deprecated`. The 12B rerun did not disagree on any paired edit. The drafted mismatches are a different phenomenon from the 12B speed noise.

### 3.2 Agent steps

![Speedup by step type](https://github.com/ojavadli/free-speed-gemma4/raw/main/figures/fig_by_kind.png)

On replayed 12B agent steps, with 19 of 48 blocks on the GPU, prompt lookup matched {{W2.12b.ngram.ALL.identity_rate|pct}} of {{W2.12b.ngram.ALL.n_pairs}} steps and MTP matched {{W2.12b.mtp.ALL.identity_rate|pct}}. No MTP trajectory stayed identical. Those steps were capped at 8, mostly search and read, and none called submit. A different next step is not an agent speedup. We did not replay the agent with every block on the GPU, so this is a limit of that recording, not a full-GPU E4B result.

### 3.3 Sampling

At temperature 1.0 the deadline kept {{W1s.12b.ngram.ALL.n_pairs}} paired prompts. Prompt lookup matched on {{W1s.12b.ngram.ALL.identity_rate|pct}} of them, with speedup {{W1s.12b.ngram.ALL.speedup|.2f}} (interval {{W1s.12b.ngram.ALL.speedup_lo|.2f}} to {{W1s.12b.ngram.ALL.speedup_hi|.2f}}, which includes 1).

### 3.4 An upper bound, not a result

If the full-GPU MTP decode ratio of {{W1full.e4b.mtp.ALL.speedup|.3f}} let an agent attempt more repairs in the same wall-clock time, an oracle that keeps a success if any attempt succeeds would raise the Many Labs E4B rate on {{proj.E4B.n_valid_tasks}} valid tasks from {{proj.E4B.single_attempt_rate|pct}} at one attempt to {{proj.E4B.rate_at_measured_speedup_oracle|pct}}. The same arithmetic on 31B pooled attempts goes from {{proj.31B.single_attempt_rate|pct}} to {{proj.31B.rate_at_measured_speedup_oracle|pct}}. This is an upper bound that uses decode time, not the smaller ratio that includes prompt processing. The agent replay does not support it. The projection is not the headline.

## 4. What this does not show

The pre-registered 12B comparison did not clear the lossless bar. No 12B drafter was lossless, and the 12B speed ratios are not distinguishable from launch-to-launch noise. A repeated baseline that moves by {{W1.12b.baseline_rerun.ALL.speedup|.2f}} times is a finding about laptop timing, not a drafter result: two launches can agree on every token and still disagree on speed by more than the pre-registered 5 percent band. The full-GPU E4B speedup is larger than that band, and the text matched, but the first baseline block was cold, so the fair comparison is the one against the second launch. {{qa.length_share|pct}} of raw rows stopped because they hit the length limit. Prompts use pull-request commit messages, not the competition issue text. The 12B test run and the agent replay both stopped on the clock. The capped runs used 40 percent of the blocks. The full-GPU follow-up did not, and the machine still held swap from the earlier runs. We did not measure the wall clock of a full repair.

## 5. Use it today

The full-GPU E4B server that produced the identical text used llama.cpp `llama-server` with the shipped MTP file and prompt lookup:

`-md mtp-gemma-4-E4B-it-Q4_0.gguf -ngld 999 --spec-type ngram-map-k4v,draft-mtp --spec-draft-n-max 4`

No agent code changes. On the same 24 prompts, decode was {{W1full.e4b.mtp_ngram.VS.speedup|.2f}} times faster than the repeated undrafted launch, under a third of the decode time.

## 6. Related work

Leviathan, Kalman, and Matias, and Chen and coauthors, introduced speculative decoding as a draft-and-verify procedure that preserves the target distribution when the acceptance rule is exact. EAGLE and later heads, including Gemma 4's MTP head, put a small transformer on the target's hidden states. The Gemma 4 technical report (arXiv 2607.02770, section 2.6) specifies the 4-layer head and, for E2B and E4B, a clustered vocabulary projection. Li, Chen, Hu, and Xia (arXiv 2604.26469) measured several speculative methods on generation, editing, and repair, and found the winner depends on the task. They did not measure this drafter, this server, or byte identity against a repeated baseline. SWE-bench (Jimenez et al., arXiv 2310.06770) is the issue-and-patch setup this competition descends from. The token-budget writeup cited above documents the same pressure from the agent side. This paper adds a laptop measurement of the drafters Google already ships.

## References

Gemma Team. Gemma 4 technical report. arXiv:2607.02770, 2026. Section 2.6.

Google AI for Developers. Gemma 4 model overview. https://ai.google.dev/gemma/docs/core, read 12 Nov 2026.

Google. gemma-4-12B-it-assistant model card. https://huggingface.co/google/gemma-4-12B-it-assistant, read 12 Nov 2026.

ggml-org. llama: add Gemma4 MTP. Pull request 23398, https://github.com/ggml-org/llama.cpp/pull/23398, read 12 Nov 2026.

Y. Leviathan, M. Kalman, Y. Matias. Fast inference from transformers via speculative decoding. ICML 2023.

C. Chen et al. Accelerating large language model decoding with speculative sampling. 2023.

Y. Li et al. EAGLE: speculative sampling requires rethinking feature uncertainty. 2024.

Y. Li, J. Chen, X. Hu, X. Xia. An empirical study of speculative decoding on software engineering tasks. arXiv:2604.26469, 2026.

C. E. Jimenez et al. SWE-bench: Can language models resolve real-world GitHub issues? arXiv:2310.06770, 2024.

yosh95. Every Tool Call Is a Token You Cannot Buy Back. https://github.com/yosh95/g4-developer-agent-paper, read 12 Nov 2026.

yuvrajtiwary-bitmesraece. gemma4-many-labs. https://github.com/yuvrajtiwary-bitmesraece/gemma4-many-labs, cloned 12 Nov 2026.

Code, records, and figures: https://github.com/ojavadli/free-speed-gemma4. The CPU notebook is `notebook/free_speed_reproduce.ipynb` in that repository. Upload it to Kaggle by hand. The Kaggle CLI was not available on this machine.
