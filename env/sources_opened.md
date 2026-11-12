# Sources opened on 12 Nov 2026

These notes are for the paper. Numbers in the paper still come only from claims.json or env json.

- Gemma 4 Technical Report, arXiv 2607.02770, section 2.6 "Multi-Token Prediction Drafter". The report says every model is trained with a small autoregressive MTP drafter head for speculative decoding. The head uses the last-layer activations and token embeddings, a separate embedder, and a 4-layer Transformer that cross-attends to the main model's KV cache, so there is no MTP prefill and the draft length is not fixed. The drafter width is 256 for E2B and E4B, and 1024 for 26B-A4B and 31B. E2B and E4B replace the full vocabulary projection with a top-k over token clusters, cutting the final multiply from d by 262,000 to d by 4,096. Cite https://arxiv.org/abs/2607.02770

- Google AI for Developers, Gemma 4 model overview, opened at https://ai.google.dev/gemma/docs/core on 12 Nov 2026. It says all Gemma 4 models (E2B, E4B, 12B, 31B, and 26B A4B) include a dedicated draft model for speculative decoding, with faster inference and no quality loss. The same page's speculative-decoding row names the drafter files `{model-name}-qat-q4_0-unquantized-assistant`.

- Hugging Face card https://huggingface.co/google/gemma-4-12B-it-assistant opened 12 Nov 2026. It says the card is for the MTP drafters, that the draft model predicts several tokens and the target verifies them in parallel, and that this gives decoding speedups up to 3x with the same quality as standard generation.

- llama.cpp pull request 23398, "llama : add Gemma4 MTP", https://github.com/ggml-org/llama.cpp/pull/23398 opened 12 Nov 2026. The discussion shows `llama-server` runs Gemma 4 MTP with `--spec-type draft-mtp` and a separate draft GGUF (`-md` / `--spec-draft-model`). Comments use `--spec-draft-n-max` of 2, 3, or 4.

- Li, Chen, Hu, and Xia, "An Empirical Study of Speculative Decoding on Software Engineering Tasks", arXiv 2604.26469, PACMSE / ISSTA 2026, https://arxiv.org/abs/2604.26469 opened 12 Nov 2026. Abstract: speculative decoding can speed software-engineering tasks, but the gain depends on the model and the task. Model-based drafters fit code generation better. Model-free methods fit repository repair and editing better, helped by how often code repeats itself. Agentic loops can get stuck repeating themselves, which distorts speed measurements. Difference from this paper: that study does not measure Gemma 4's shipped MTP drafter inside one agent's recorded steps on a laptop, and it does not check byte identity against a second baseline launch.

- Leviathan, Kalman, and Matias, "Fast Inference from Transformers via Speculative Decoding", ICML 2023. Not re-opened as a PDF this session. Do not invent page numbers. The Gemma report cites it as the speculative-decoding method. If a page is not opened, cite only through the Gemma report or drop the direct citation.

- Chen et al., speculative sampling, 2023, and Li et al., EAGLE, 2024: named by the master prompt. Cite them only if a page is opened before the paper is filled. The 2026 empirical study cites both as the draft-and-verify line of work.
