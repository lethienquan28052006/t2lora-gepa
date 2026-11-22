import json

from t2lgepa.bundle import arm_of, build_manifest
from t2lgepa.data import Example

EX = Example(id="gsm8k:train:0", task="gsm8k", question="2+2?", answers=[], answer="4",
             rationale="2+2=4", split="train")
ARMS = ("base", "t2l_icl", "gepa_3shot", "t2l_gepa_opt")


def _summary(run_dir, arm, task="gsm8k", n=1000, score=0.5):
    (run_dir / f"{arm}_{task}_s0.jsonl").write_text(json.dumps({
        "arm": arm, "task": task, "seed": 0, "n": n, "score": score,
        "wall_seconds": 12.0, "generated_tokens": 345,
    }) + "\n")


def _manifest(run_dir, tasks=("gsm8k",), max_eval_items=1000):
    demos = {task: [EX, EX, EX] for task in tasks}
    return build_manifest(run_dir, "base-model", list(tasks), demos, max_eval_items)


def _version(manifest, arm, task="gsm8k"):
    return next(v for v in manifest["versions"] if v["arm"] == arm and v["task"] == task)


def test_manifest_exposes_four_demo_versions_per_task(tmp_path):
    for arm in ARMS:
        _summary(tmp_path, arm)
    (tmp_path / "gepa_3shot_gsm8k_s0_best_prompt.txt").write_text("best gepa\n")
    (tmp_path / "gepa_3shot_gsm8k_s0_seed_prompt.txt").write_text("seed gepa\n")
    (tmp_path / "t2l_gepa_opt_gsm8k_s0_best_prompt.txt").write_text("best opt\n")
    (tmp_path / "t2l_gepa_opt_gsm8k_s0_seed_prompt.txt").write_text("seed opt\n")

    manifest = _manifest(tmp_path)
    assert len(manifest["versions"]) == 4

    base = _version(manifest, "base")
    assert base["model"] == "base-model"
    assert base["prompt"]["demo_block"] is None
    assert base["complete"] is True
    assert base["metrics"] == {"n": 1000, "accuracy": 0.5, "wall_seconds": 12.0,
                               "generated_tokens": 345}

    gepa = _version(manifest, "gepa_3shot")
    assert gepa["prompt"]["instruction"] == "best gepa"
    assert gepa["prompt"]["seed_instruction"] == "seed gepa"
    assert gepa["prompt"]["files"]["best"] == "prompts/gepa_3shot/gepa_3shot_gsm8k_s0_best_prompt.txt"
    assert "2+2?" in gepa["prompt"]["demo_block"]

    opt = _version(manifest, "t2l_gepa_opt")
    assert opt["model"] == "t2l_gsm8k"
    assert opt["adapter"] == "adapters/gsm8k"
    assert opt["prompt"]["instruction"] == "best opt"


def test_unfinished_or_missing_runs_are_marked_incomplete(tmp_path):
    _summary(tmp_path, "base", n=40)  # truncated run
    manifest = _manifest(tmp_path)
    assert _version(manifest, "base")["complete"] is False
    for arm in ("t2l_icl", "gepa_3shot", "t2l_gepa_opt"):
        version = _version(manifest, arm)
        assert version["complete"] is False
        assert version["metrics"] is None


def test_gepa_version_without_a_saved_prompt_is_not_complete(tmp_path):
    for arm in ARMS:
        _summary(tmp_path, arm)
    (tmp_path / "gepa_3shot_gsm8k_s0_best_prompt.txt").write_text("only one arm saved\n")
    manifest = _manifest(tmp_path)
    assert _version(manifest, "gepa_3shot")["complete"] is True
    assert _version(manifest, "t2l_gepa_opt")["complete"] is False


def test_arm_of_uses_the_longest_matching_arm():
    assert arm_of("t2l_gepa_opt_gsm8k_s0_best_prompt.txt") == "t2l_gepa_opt"
    assert arm_of("gepa_3shot_arc_challenge_s0.curve.jsonl") == "gepa_3shot"
    assert arm_of("base_boolq_s0.jsonl") == "base"


def test_build_bundle_collects_prompts_adapters_and_serve_config(tmp_path):
    import json as js

    from t2lgepa.bundle import build_bundle

    run = tmp_path / "run"
    run.mkdir()
    for arm in ARMS:
        _summary(run, arm)
    (run / "gepa_3shot_gsm8k_s0_best_prompt.txt").write_text("best gepa\n")
    (run / "t2l_gepa_opt_gsm8k_s0_best_prompt.txt").write_text("best opt\n")
    (run / "gepa_3shot_gsm8k_s0.curve.jsonl").write_text('{"metric_calls": 0}\n')
    (run / "gepa_3shot_gsm8k_s0_candidates.json").write_text("[]\n")
    lora_root = tmp_path / "loras"
    (lora_root / "gsm8k").mkdir(parents=True)
    (lora_root / "gsm8k" / "adapter_config.json").write_text(
        js.dumps({"use_rslora": True, "r": 8}))
    (lora_root / "gsm8k" / "adapter_model.safetensors").write_bytes(b"weights")

    out = build_bundle(run, lora_root, tmp_path / "bundle", "base-model", ["gsm8k"],
                       {"gsm8k": [EX, EX, EX]}, 1000)

    assert (out / "prompts/gepa_3shot/gepa_3shot_gsm8k_s0_best_prompt.txt").exists()
    assert (out / "prompts/gepa_3shot/gepa_3shot_gsm8k_s0.curve.jsonl").exists()
    assert (out / "results/base_gsm8k_s0.jsonl").exists()
    assert (out / "adapters/gsm8k/adapter_model.safetensors").read_bytes() == b"weights"
    assert js.loads((out / "adapters/gsm8k/adapter_config.json").read_text())["use_rslora"] is False
    serve = (out / "serve_config.yaml").read_text()
    assert "./adapters/gsm8k" in serve and "base-model" in serve
    manifest = js.loads((out / "manifest.json").read_text())
    assert len(manifest["versions"]) == 4
    assert (out / "README.md").exists()


def test_partial_search_is_never_a_complete_version(tmp_path):
    for arm in ARMS:
        _summary(tmp_path, arm)
    (tmp_path / "gepa_3shot_gsm8k_s0_best_prompt.txt").write_text("seed fallback\n")
    (tmp_path / "gepa_3shot_gsm8k_s0.job.json").write_text(
        json.dumps({"arm": "gepa_3shot", "task": "gsm8k", "partial": True}))
    manifest = _manifest(tmp_path)
    version = _version(manifest, "gepa_3shot")
    assert version["partial"] is True
    assert version["complete"] is False


def test_missing_adapter_marks_t2l_versions_incomplete(tmp_path):
    import json as js

    from t2lgepa.bundle import build_bundle

    for arm in ARMS:
        _summary(tmp_path, arm)
    (tmp_path / "gepa_3shot_gsm8k_s0_best_prompt.txt").write_text("best gepa\n")
    (tmp_path / "t2l_gepa_opt_gsm8k_s0_best_prompt.txt").write_text("best opt\n")
    lora_root = tmp_path / "loras"
    lora_root.mkdir()  # no adapter for gsm8k at all
    out = build_bundle(tmp_path, lora_root, tmp_path / "bundle", "base-model", ["gsm8k"],
                       {"gsm8k": [EX, EX, EX]}, 1000)
    manifest = js.loads((out / "manifest.json").read_text())
    assert all(not v["complete"] for v in manifest["versions"] if v["arm"].startswith("t2l"))
    assert all(v["complete"] for v in manifest["versions"] if v["arm"] in ("base", "gepa_3shot"))
    assert "./adapters/gsm8k" not in (out / "serve_config.yaml").read_text()


def test_instruction_keeps_inner_whitespace_but_not_the_exported_newline(tmp_path):
    (tmp_path / "gepa_3shot_gsm8k_s0_best_prompt.txt").write_text("  spaced out  \n")
    _summary(tmp_path, "gepa_3shot")
    manifest = _manifest(tmp_path)
    assert _version(manifest, "gepa_3shot")["prompt"]["instruction"] == "  spaced out  "
