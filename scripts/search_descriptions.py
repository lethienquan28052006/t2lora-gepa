"""Search task descriptions with GEPA, generate adapters with the frozen T2L, compare to the
shipped description.

    python scripts/search_descriptions.py --tasks winogrande,gsm8k --budget 300

Each GEPA candidate is a task description. It is turned into a LoRA by the hypernetwork
(~0.04s once the worker is warm), loaded into the running vLLM server, and scored on a
minibatch of the train split. The final description's adapter is then scored on the test set
with the same 3-shot prompt every other arm uses.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import yaml

from t2lgepa.client import VLLMClient
from t2lgepa.config import Config, load_config
from t2lgepa.data import make_splits
from t2lgepa.desc_search import AdapterWorker, DescriptionAdapter, LoRARegistry, adapter_name
from t2lgepa.gepa_arm import MeteredMetric
from t2lgepa.prompts import three_shot
from t2lgepa.runner import run_arm
from t2lgepa.scoring import score
from t2lgepa.t2l import lora_module_name

DESCRIPTIONS = Path("configs/task_descriptions.yaml")


def seeded_description(task: str) -> str:
    return yaml.safe_load(DESCRIPTIONS.read_text())[task]


def search_task(
    task: str,
    cfg: Config,
    client: VLLMClient,
    worker: AdapterWorker,
    base_url: str,
    budget: int,
    minibatch: int,
    out_dir: Path,
    pareto_size: int = 300,
    seed: int = 0,
) -> dict:
    from gepa import optimize

    splits = make_splits(task, cache_dir=cfg.cache_dir)
    demos = splits.train[:3]
    pareto = splits.pareto[:pareto_size]
    train = splits.train

    cache: dict[str, tuple[str, Path]] = {}

    def make_adapter(description: str):
        name = adapter_name(description)
        if name not in cache:
            path = worker.generate(description)
            cache[name] = (name, path)
        return cache[name]

    metric = MeteredMetric(score, budget)

    def reflect(prompt: str) -> str:
        return client.generate([prompt], model=cfg.model_id, temperature=1.0,
                               max_tokens=1024)[0].text

    adapter = DescriptionAdapter(
        client=client, cfg=cfg, metric=metric, make_adapter=make_adapter,
        registry=LoRARegistry(base_url), train_demos=demos, reflect=reflect,
    )

    result = optimize(
        seed_candidate={"instruction": seeded_description(task)},
        trainset=train,
        valset=pareto,
        adapter=adapter,
        reflection_lm=reflect,
        max_metric_calls=max(1, budget - len(pareto)),
        skip_perfect_score=False,
        seed=seed,
        reflection_minibatch_size=minibatch,
    )

    best = result.best_candidate["instruction"].strip()
    name, path = make_adapter(best)
    summary = run_arm(
        "desc_search", task, seed, client,
        lambda ex: three_shot(ex, demos), name, cfg,
        results_dir=out_dir, adapter_path=path,
    )
    record = {
        "task": task,
        "seed_description": seeded_description(task),
        "best_description": best,
        "pareto_score": float(result.val_aggregate_scores[result.best_idx]),
        "test_score": summary.score,
        "test_n": summary.n,
        "metric_calls": metric.calls,
        "candidates": len(cache),
        "adapter": name,
    }
    (out_dir / f"desc_search_{task}_s{seed}.json").write_text(json.dumps(record, indent=2))
    return record


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/mistral.yaml")
    parser.add_argument("--tasks", default="winogrande,gsm8k")
    parser.add_argument("--budget", type=int, default=300)
    parser.add_argument("--pareto", type=int, default=300)
    parser.add_argument("--minibatch", type=int, default=30)
    parser.add_argument("--base-url", default="http://localhost:8010")
    parser.add_argument("--out", default="/data/quan.lt/temp/t2l-mistral/results")
    parser.add_argument("--candidates", default="/data/quan.lt/temp/t2l-mistral/candidates")
    parser.add_argument("--t2l-python", default="/data/quan.lt/temp/t2l-mistral/venv-t2l/bin/python")
    args = parser.parse_args(argv)

    cfg = load_config(args.config)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    client = VLLMClient(args.base_url, cfg.model_id,
                        adapters=[lora_module_name(t) for t in cfg.tasks])
    client.assert_ready()

    worker = AdapterWorker(
        checkpoint=str(Path(cfg.t2l_checkpoint) / "hypermod.pt"),
        out_dir=args.candidates, python=args.t2l_python,
    )
    worker.start()
    try:
        for task in args.tasks.split(","):
            record = search_task(task, cfg, client, worker, args.base_url,
                                 args.budget, args.minibatch, out_dir,
                                 pareto_size=args.pareto)
            print(json.dumps({k: record[k] for k in
                              ("task", "test_score", "pareto_score", "candidates",
                               "metric_calls")}), flush=True)
    finally:
        worker.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
