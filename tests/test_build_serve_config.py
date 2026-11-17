import build_serve_config
import yaml


def test_build_sets_gpu_util_and_max_len(tmp_path):
    root = tmp_path / "loras"
    (root / "gsm8k").mkdir(parents=True)
    config = build_serve_config.build(root, "mistralai/Mistral-7B-Instruct-v0.2", 8010,
                                      gpu_util=0.90, max_model_len=4096)
    assert config["gpu_memory_utilization"] == 0.90
    assert config["max_model_len"] == 4096
    assert config["model"] == "mistralai/Mistral-7B-Instruct-v0.2"


def test_main_writes_all_adapters(tmp_path):
    root = tmp_path / "loras"
    for task in ("gsm8k", "boolq"):
        (root / task).mkdir(parents=True)
    out = tmp_path / "serve.yaml"
    code = build_serve_config.main([
        "--lora-root", str(root), "--model", "m", "--port", "8010",
        "--out", str(out), "--gpu-util", "0.9", "--max-model-len", "4096",
    ])
    assert code == 0
    written = yaml.safe_load(out.read_text())
    assert len(written["lora_modules"]) == 2
    assert written["port"] == 8010
