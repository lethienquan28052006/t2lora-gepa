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
