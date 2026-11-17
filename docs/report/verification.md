# Weight verification: mirror vs. official Gemma-2-2B-it

The run uses `unsloth/gemma-2-2b-it` because `google/gemma-2-2b-it` is gated. Once an HF
token with the license accepted was available, both checkpoints were compared tensor by
tensor (sha256 over each tensor's bytes, via `safe_open`, so nothing is loaded twice).

```
uv run --extra verify python -m t2lgepa.verify \
  --a ~/.cache/huggingface/hub/models--google--gemma-2-2b-it/snapshots/*/model-00001-of-00002.safetensors \
      ~/.cache/huggingface/hub/models--google--gemma-2-2b-it/snapshots/*/model-00002-of-00002.safetensors \
  --b ~/.cache/huggingface/hub/models--unsloth--gemma-2-2b-it/snapshots/*/model.safetensors
```

Output:

```
tensors: 288 vs 288, shared 288
identical: True
```

Conclusion: the mirror is bit-identical to the official checkpoint. The only differences
are packaging (one shard instead of two) and metadata (`_name_or_path`, `unsloth_version`).
No result in this report depends on the choice of repository.

Tokenizer comparison was not repeated tensor by tensor; `tokenizer.model`, `tokenizer.json`,
`special_tokens_map.json` and the chat template are the standard Gemma-2 files.
