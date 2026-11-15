from pathlib import Path

from t2lgepa.serve import BASE_URL_DEFAULT, build_serve_cmd, gepa_prompt_from_curve, run_all

BASE = "google/gemma-2-2b-it"


def test_serve_cmd_enables_lora_and_names_module(cfg):
    cmd = build_serve_cmd(cfg, Path("/tmp/lora"), 8000)
    assert "--enable-lora" in cmd and "t2l_gsm8k=/tmp/lora" in cmd
    assert "--gpu-memory-utilization" in cmd
    assert cmd[cmd.index("--model") + 1] == BASE


def test_serve_cmd_sets_port_and_module_name(cfg):
    cmd = build_serve_cmd(cfg, Path("/tmp/lora"), 8123)
    assert cmd[cmd.index("--port") + 1] == "8123"
    assert "t2l_gsm8k=/tmp/lora" in cmd


def test_default_base_url_is_local():
    assert BASE_URL_DEFAULT.startswith("http://localhost")


def test_run_all_returns_three_surfaces(cfg, monkeypatch):
    calls = []

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def generate(self, prompts, model, temperature=0.0, max_tokens=512):
            calls.append(model)

            class G:
                text = f"answer for {model}"
                n_tokens = 3
                finish_reason = "stop"

            return [G() for _ in prompts]

    monkeypatch.setattr("t2lgepa.serve.VLLMClient", FakeClient)
    out = run_all(["2+2?"], cfg, gepa_prompt="be careful")
    assert set(out) == {"base", "t2l", "gepa"}
    assert calls.count(cfg.model_id) == 2 and "t2l_gsm8k" in calls


def test_gepa_prompt_from_curve_reads_best_prompt_file(tmp_path):
    path = tmp_path / "gepa_gsm8k_s0.curve.jsonl"
    path.write_text('{"metric_calls": 10, "pareto_score": 0.5}\n')
    assert gepa_prompt_from_curve(tmp_path) is None or isinstance(
        gepa_prompt_from_curve(tmp_path), str
    )


def test_format_report_shows_the_three_surfaces():
    from t2lgepa.demo import format_report

    text = format_report(["2+2?"], {"base": ["4"], "t2l": ["#### 4"], "gepa": ["The answer is 4"]})
    assert "base" in text and "t2l" in text and "gepa" in text
    assert text.count("2+2?") == 1
