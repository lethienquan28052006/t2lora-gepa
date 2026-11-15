from pathlib import Path

import pytest

from t2lgepa import t2l
from t2lgepa.config import load_config
from t2lgepa.t2l import T2LError, describe_task, generate_lora, lora_module_name

STDOUT = Path("tests/fixtures/t2l_generate_stdout.txt").read_text()


@pytest.fixture
def cfg():
    return load_config("configs/base.yaml")


def test_generate_lora_parses_printed_path(tmp_path, monkeypatch, cfg):
    target = tmp_path / "loras" / "gsm8k"
    target.mkdir(parents=True)
    (target / "adapter_config.json").write_text("{}")
    monkeypatch.setattr(t2l, "_run", lambda cmd, cfg: STDOUT.replace("{LORA_DIR}", str(target)))
    assert generate_lora(cfg, "gsm8k", str(tmp_path / "loras")) == target


def test_missing_adapter_config_is_an_error(tmp_path, monkeypatch, cfg):
    empty = tmp_path / "vendor_out"
    empty.mkdir()
    monkeypatch.setattr(t2l, "_run", lambda cmd, cfg: STDOUT.replace("{LORA_DIR}", str(empty)))
    with pytest.raises(T2LError, match="adapter_config.json"):
        generate_lora(cfg, "gsm8k", str(tmp_path / "loras"))


def test_unparseable_stdout_is_an_error(tmp_path, monkeypatch, cfg):
    monkeypatch.setattr(t2l, "_run", lambda cmd, cfg: "boom")
    with pytest.raises(T2LError):
        generate_lora(cfg, "gsm8k", str(tmp_path / "loras"))


def test_describe_task_is_versioned_and_task_specific():
    assert "math" in describe_task("gsm8k").lower()
    assert describe_task("arc_challenge") != describe_task("gsm8k")
    with pytest.raises(KeyError):
        describe_task("nope")


def test_lora_module_name():
    assert lora_module_name("gsm8k") == "t2l_gsm8k"


def test_checkpoint_path_is_passed_absolutely(tmp_path, monkeypatch, cfg):
    captured = {}

    def fake_run(cmd, cfg):
        captured["cmd"] = cmd
        target = tmp_path / "loras" / "gsm8k"
        target.mkdir(parents=True)
        (target / "adapter_config.json").write_text("{}")
        return STDOUT.replace("{LORA_DIR}", str(target))

    monkeypatch.setattr(t2l, "_run", fake_run)
    generate_lora(cfg, "gsm8k", str(tmp_path / "loras"))
    ckpt_arg = captured["cmd"][captured["cmd"].index("scripts/generate_lora.py") + 1]
    assert ckpt_arg.startswith("/")


def test_command_uses_the_dedicated_t2l_interpreter(tmp_path, monkeypatch, cfg):
    captured = {}

    def fake_run(cmd, cfg):
        captured["cmd"] = cmd
        captured["env_keys"] = True
        target = tmp_path / "loras" / "gsm8k"
        target.mkdir(parents=True)
        (target / "adapter_config.json").write_text("{}")
        return STDOUT.replace("{LORA_DIR}", str(target))

    monkeypatch.setattr(t2l, "_run", fake_run)
    generate_lora(cfg, "gsm8k", str(tmp_path / "loras"))
    assert captured["cmd"][0].endswith(".venv-t2l/bin/python")
    assert captured["cmd"][1] == "-m"
    assert captured["cmd"][2] == "t2lgepa._t2l_shim"
    assert captured["cmd"][3] == "scripts/generate_lora.py"


def test_generated_adapter_uses_alpha_over_r_scaling(tmp_path, monkeypatch, cfg):
    import json

    target = tmp_path / "loras" / "gsm8k"
    target.mkdir(parents=True)
    (target / "adapter_config.json").write_text(json.dumps({"use_rslora": True, "r": 8,
                                                            "lora_alpha": 16}))
    monkeypatch.setattr(t2l, "_run", lambda cmd, cfg: STDOUT.replace("{LORA_DIR}", str(target)))
    generate_lora(cfg, "gsm8k", str(tmp_path / "loras"))
    saved = json.loads((target / "adapter_config.json").read_text())
    assert saved["use_rslora"] is False


def test_cpu_shim_disables_flash_attention_default():
    from types import SimpleNamespace

    from t2lgepa._t2l_shim import disable_flash_attn

    def get_model_and_tokenizer(path, train, requires_grad, use_flash_attn=True, peft_config=None):
        return None

    stub = SimpleNamespace(get_model_and_tokenizer=get_model_and_tokenizer)
    disable_flash_attn(stub)
    assert stub.get_model_and_tokenizer.__defaults__[0] is False
