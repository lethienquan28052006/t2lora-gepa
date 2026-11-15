"""Compare two sharded safetensors checkpoints tensor by tensor."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import torch
from safetensors import safe_open


def _keys_and_hashes(files: list[Path]) -> dict[str, str]:
    out: dict[str, str] = {}
    for path in files:
        with safe_open(str(path), framework="pt") as handle:
            for key in handle.keys():
                tensor = handle.get_tensor(key)
                out[key] = hashlib.sha256(
                    tensor.contiguous().view(torch.uint8).numpy().tobytes()
                ).hexdigest()
    return out


def compare_checkpoints(a_files: list[Path], b_files: list[Path]) -> dict:
    a = _keys_and_hashes(a_files)
    b = _keys_and_hashes(b_files)
    shared = sorted(set(a) & set(b))
    return {
        "shared": shared,
        "only_a": sorted(set(a) - set(b)),
        "only_b": sorted(set(b) - set(a)),
        "differing": [key for key in shared if a[key] != b[key]],
        "n_tensors_a": len(a),
        "n_tensors_b": len(b),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--a", nargs="+", required=True, help="reference safetensors files")
    parser.add_argument("--b", nargs="+", required=True, help="candidate safetensors files")
    args = parser.parse_args(argv)

    result = compare_checkpoints([Path(p) for p in args.a], [Path(p) for p in args.b])
    print(f"tensors: {result['n_tensors_a']} vs {result['n_tensors_b']}, "
          f"shared {len(result['shared'])}")
    print(f"identical: {not (result['only_a'] or result['only_b'] or result['differing'])}")
    for label in ("only_a", "only_b", "differing"):
        if result[label]:
            print(f"{label}: {result[label][:10]}")
    return 0 if not (result["only_a"] or result["only_b"] or result["differing"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
