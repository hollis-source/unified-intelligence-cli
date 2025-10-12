#!/usr/bin/env python3
"""
Lightweight evaluation utilities for LoRA outputs.

- Computes accuracy, precision, recall, F1 for binary classification
- CLI accepts a JSON file with {"predictions": [...], "labels": [...]} and prints metrics JSON
- Keep functions small (<20 lines) and explicit error handling
"""
from __future__ import annotations

import argparse
import json
from typing import List, Dict


def _safe_div(n: float, d: float) -> float:
    """Divide with zero-protection."""
    return 0.0 if d == 0 else n / d


def evaluate_metrics(predictions: List[int], labels: List[int]) -> Dict[str, float]:
    """Compute accuracy, precision, recall, and F1 for binary labels.

    Assumes labels and predictions contain 0/1 integers of equal length.
    """
    if len(predictions) != len(labels):
        raise ValueError("predictions and labels must have the same length")
    tp = fp = tn = fn = 0
    for p, y in zip(predictions, labels):
        if p == 1 and y == 1:
            tp += 1
        elif p == 1 and y == 0:
            fp += 1
        elif p == 0 and y == 0:
            tn += 1
        elif p == 0 and y == 1:
            fn += 1
    precision = _safe_div(tp, tp + fp)
    recall = _safe_div(tp, tp + fn)
    f1 = _safe_div(2 * precision * recall, precision + recall)
    accuracy = _safe_div(tp + tn, len(labels))
    return {
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
    }


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description="Evaluate LoRA predictions vs labels")
    parser.add_argument("--data", required=True, help="Path to JSON file with predictions and labels")
    return parser.parse_args()


def main() -> int:
    """Entry point: load data, compute metrics, print JSON to stdout."""
    args = parse_args()
    with open(args.data, "r", encoding="utf-8") as f:
        js = json.load(f)
    preds = js.get("predictions")
    labels = js.get("labels")
    if not isinstance(preds, list) or not isinstance(labels, list):
        raise ValueError("JSON must contain 'predictions' and 'labels' lists")
    metrics = evaluate_metrics(preds, labels)
    print(json.dumps(metrics))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

