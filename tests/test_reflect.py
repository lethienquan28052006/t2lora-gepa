
from t2lgepa import reflect


def _write_config(tmp_path, key):
    path = tmp_path / "opencode.jsonc"
    path.write_text(
        "{\n  // local provider block\n  \"providers\": {\n"
        "    \"bioturing\": {\n      \"settings\": {\n"
        f"        \"baseURL\": \"https://api.example/v1\",\n        \"apiKey\": \"{key}\"\n"
        "      }\n    }\n  }\n}\n"
    )
    return path


def test_reads_key_from_opencode_jsonc_with_comments(tmp_path):
    path = _write_config(tmp_path, "sk-local")
    assert reflect.opencode_api_key("bioturing", path=path) == "sk-local"


def test_missing_provider_returns_none(tmp_path):
    path = _write_config(tmp_path, "sk-local")
    assert reflect.opencode_api_key("nope", path=path) is None


def test_env_var_wins(tmp_path, monkeypatch, cfg):
    from dataclasses import replace

    path = _write_config(tmp_path, "sk-local")
    monkeypatch.setattr(reflect, "OPENCODE_CONFIG", path)
    monkeypatch.setenv("REFLECT_API_KEY", "sk-env")
    assert reflect.resolve_key(replace(cfg, reflection_api_key_env="REFLECT_API_KEY")) == "sk-env"
