import json
import subprocess
import sys
from pathlib import Path
import importlib.util


def load_module(module_path: str):
    p = Path(module_path)
    spec = importlib.util.spec_from_file_location(p.stem, str(p))
    mod = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(mod)  # type: ignore[attr-defined]
    return mod


def test_evaluate_metrics_basic(tmp_path):
    # Arrange
    preds = [1, 0, 1, 1]
    labels = [1, 1, 0, 1]
    mod = load_module("training/scripts/evaluate_lora.py")

    # Act
    metrics = mod.evaluate_metrics(preds, labels)

    # Assert
    assert 0.0 <= metrics["accuracy"] <= 1.0
    assert metrics["accuracy"] == 0.5  # 2/4 correct


def test_cli_emits_json_with_accuracy_and_f1(tmp_path):
    # Arrange
    data = {"predictions": [1, 0, 1, 1], "labels": [1, 1, 0, 1]}
    data_path = tmp_path / "eval_input.json"
    data_path.write_text(json.dumps(data), encoding="utf-8")

    # Act
    p = subprocess.run(
        [sys.executable, "training/scripts/evaluate_lora.py", "--data", str(data_path)],
        capture_output=True,
        text=True,
        check=True,
    )

    # Assert
    out = p.stdout.strip()
    js = json.loads(out)
    assert set(["accuracy", "f1", "precision", "recall"]).issubset(js.keys())
    assert 0.0 <= js["accuracy"] <= 1.0

