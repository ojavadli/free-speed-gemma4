#!/usr/bin/env python3
"""Lists candidate GGUF files on Hugging Face for a Gemma 4 size: the target model and its MTP drafter.
Usage: python3 kit/find_models.py 12B     (also E4B, E2B, 31B). Needs: pip install huggingface_hub
Prints repo, file and size so you can choose by the rules in the master prompt. Network errors are not fatal."""
import sys
from huggingface_hub import HfApi

def main():
    size = sys.argv[1]
    api = HfApi()
    seen, rows = set(), []
    fixed = ["google/gemma-4-%s-it-qat-q4_0-gguf" % size, "unsloth/gemma-4-%s-it-qat-GGUF" % size,
             "bartowski/gemma-4-%s-it-GGUF" % size, "ggml-org/gemma-4-%s-it-GGUF" % size,
             "ggml-org/gemma-4-%s-it-qat-GGUF" % size, "lmstudio-community/gemma-4-%s-it-GGUF" % size]
    found = []
    for q in ("gemma-4-%s gguf" % size, "gemma-4-%s assistant" % size, "gemma-4-%s mtp" % size, "mtp-gemma-4-%s" % size):
        try:
            found += [m.id for m in api.list_models(search=q, limit=40)]
        except Exception as e:
            print("search failed for %r: %s" % (q, e))
    for repo in fixed + found:
        if repo in seen:
            continue
        seen.add(repo)
        try:
            info = api.model_info(repo, files_metadata=True)
        except Exception:
            continue
        for s in info.siblings or []:
            fn = s.rfilename
            if not fn.lower().endswith(".gguf") or "mmproj" in fn.lower():
                continue
            low = (repo + "/" + fn).lower()
            role = "DRAFTER" if ("mtp" in low or "assistant" in low or "drafter" in low) else "TARGET"
            rows.append((role, repo, fn, (s.size or 0) / 1e9, getattr(info, "downloads", 0) or 0))
    rows.sort(key=lambda r: (r[0], not r[1].startswith("google/"), -r[4]))
    for r in rows:
        print("%-8s %-58s %-52s %6.2f GB  dl=%d" % r)
    if not rows:
        print("no GGUF candidates found; see the fallback rules in the master prompt")

if __name__ == "__main__":
    main()
