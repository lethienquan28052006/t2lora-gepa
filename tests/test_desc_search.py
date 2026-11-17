from pathlib import Path

import pytest
import respx

from t2lgepa.desc_search import DescriptionAdapter, LoRARegistry, adapter_name


def test_adapter_name_is_stable_and_ignores_padding():
    assert adapter_name("  solve math  ") == adapter_name("solve math")
    assert adapter_name("a") != adapter_name("b")
    assert adapter_name("a").startswith("desc_")


def test_registry_loads_once_and_unloads():
    with respx.mock(assert_all_called=False) as mock:
        load = mock.post("http://localhost:8010/v1/load_lora_adapter").respond(200)
        unload = mock.post("http://localhost:8010/v1/unload_lora_adapter").respond(200)
        reg = LoRARegistry("http://localhost:8010/v1")
        reg.load("desc_x", Path("/tmp/x"))
        reg.load("desc_x", Path("/tmp/x"))
        reg.unload("desc_x")
        assert load.call_count == 1
        assert unload.call_count == 1


def test_registry_raises_on_server_error():
    with respx.mock(assert_all_called=False) as mock:
        mock.post("http://localhost:8010/v1/load_lora_adapter").respond(400, text="nope")
        with pytest.raises(RuntimeError):
            LoRARegistry("http://localhost:8010").load("d", Path("/tmp/d"))


def test_adapter_switches_model_only_when_the_description_changes(tmp_path):
    made, loaded = [], []

    def make(desc):
        made.append(desc)
        return adapter_name(desc), tmp_path / adapter_name(desc)

    class Reg:
        def load(self, name, path):
            loaded.append(name)

    ad = DescriptionAdapter(client=object(), cfg=object(), metric=object(),
                            make_adapter=make, registry=Reg())
    first = ad.model_for("rules A")
    again = ad.model_for("rules A")
    second = ad.model_for("rules B")
    assert first == again == adapter_name("rules A")
    assert second == adapter_name("rules B")
    assert loaded == [adapter_name("rules A"), adapter_name("rules B")]
    assert made.count("rules A") == 2  # make_adapter is idempotent by name


def test_registry_treats_already_loaded_as_success():
    with respx.mock(assert_all_called=False) as mock:
        mock.post("http://localhost:8010/v1/load_lora_adapter").respond(
            400, json={"error": {"message": "The lora adapter 'x' has already been loaded."}})
        reg = LoRARegistry("http://localhost:8010")
        reg.load("x", Path("/tmp/x"))
        assert "x" in reg.loaded
