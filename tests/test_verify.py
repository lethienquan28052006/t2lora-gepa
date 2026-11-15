import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("safetensors")

from safetensors.torch import save_file

from t2lgepa.verify import compare_checkpoints


def _write(path, tensors):
    save_file(tensors, str(path))


def test_identical_checkpoints_have_no_differences(tmp_path):
    a, b = tmp_path / "a.safetensors", tmp_path / "b.safetensors"
    _write(a, {"w": torch.zeros(2, 3), "x": torch.ones(1)})
    _write(b, {"w": torch.zeros(2, 3), "x": torch.ones(1)})
    result = compare_checkpoints([a], [b])
    assert result["differing"] == [] and result["only_a"] == [] and result["only_b"] == []
    assert len(result["shared"]) == 2


def test_one_changed_tensor_is_reported(tmp_path):
    a, b = tmp_path / "a.safetensors", tmp_path / "b.safetensors"
    _write(a, {"w": torch.zeros(2, 3)})
    _write(b, {"w": torch.full((2, 3), 1e-3)})
    result = compare_checkpoints([a], [b])
    assert result["differing"] == ["w"]


def test_missing_tensor_is_reported(tmp_path):
    a, b = tmp_path / "a.safetensors", tmp_path / "b.safetensors"
    _write(a, {"w": torch.zeros(2), "extra": torch.ones(1)})
    _write(b, {"w": torch.zeros(2)})
    result = compare_checkpoints([a], [b])
    assert result["only_a"] == ["extra"] and result["only_b"] == []
