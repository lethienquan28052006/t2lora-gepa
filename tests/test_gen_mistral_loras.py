import gen_mistral_loras


def test_every_configured_task_gets_an_adapter(monkeypatch, tmp_path):
    calls = []

    def fake_generate(cfg, task, out_dir):
        calls.append(task)
        return tmp_path / task

    monkeypatch.setattr(gen_mistral_loras, "generate_lora", fake_generate)
    cfg = gen_mistral_loras.load_config("configs/mistral.yaml")
    code = gen_mistral_loras.main(["--config", "configs/mistral.yaml",
                                   "--out", str(tmp_path)], cfg=cfg)
    assert code == 0
    assert calls == list(cfg.tasks)
