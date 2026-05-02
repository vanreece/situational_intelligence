"""Self-test for pool_and_extrapolate.evaluate using synthetic data with known metrics.

Run: python -m src.evaluate.test_pool_and_extrapolate
"""

from __future__ import annotations

import math

from src.evaluate.pool_and_extrapolate import evaluate, wilson_interval, f1_score, reliability_table


def make_synthetic():
    """Construct a 100-item corpus with hand-computable expected metrics.

    - 10 model-positives: 7 actually positive (TP), 3 actually negative (FP).
      precision = 7/10 = 0.70
    - 90 model-negatives, of which 20 are randomly sampled and labeled:
      2 actually positive (FN observed), 18 actually negative.
      fn_rate = 0.10; estimated total FN = 0.10 * 90 = 9.
      recall = 7 / (7 + 9) = 0.4375
      F1 = 2 * 0.70 * 0.4375 / (0.70 + 0.4375) ≈ 0.5385
    - Brier with p=0.9 on model-positives and p=0.1 on labeled-sample:
      (7*0.01 + 3*0.81 + 2*0.81 + 18*0.01) / 30 = 4.30 / 30 ≈ 0.1433
    """
    predictions = []
    labels = []

    for i in range(7):
        predictions.append({"id": f"tp-{i}", "prediction": True, "p_positive": 0.9, "model_id": "test", "prompt_hash": "h"})
        labels.append({"id": f"tp-{i}", "label": "positive"})
    for i in range(3):
        predictions.append({"id": f"fp-{i}", "prediction": True, "p_positive": 0.9, "model_id": "test", "prompt_hash": "h"})
        labels.append({"id": f"fp-{i}", "label": "negative"})

    for i in range(2):
        predictions.append({"id": f"fn-{i}", "prediction": False, "p_positive": 0.1, "model_id": "test", "prompt_hash": "h"})
        labels.append({"id": f"fn-{i}", "label": "positive"})
    for i in range(18):
        predictions.append({"id": f"tn-sampled-{i}", "prediction": False, "p_positive": 0.1, "model_id": "test", "prompt_hash": "h"})
        labels.append({"id": f"tn-sampled-{i}", "label": "negative"})

    for i in range(70):
        predictions.append({"id": f"tn-unsampled-{i}", "prediction": False, "p_positive": 0.1, "model_id": "test", "prompt_hash": "h"})

    return predictions, labels


def approx(a: float, b: float, tol: float = 1e-3) -> bool:
    return abs(a - b) < tol


def test_synthetic():
    predictions, labels = make_synthetic()
    sc = evaluate(predictions, labels, corpus_size=100, random_sample_size=20)

    # Counts
    assert sc["prediction_summary"]["total"] == 100
    assert sc["prediction_summary"]["model_positives"] == 10
    assert sc["prediction_summary"]["model_negatives"] == 90
    assert sc["label_summary"]["labeled_total"] == 30
    assert sc["label_summary"]["labeled_positive"] == 9
    assert sc["label_summary"]["labeled_negative"] == 21

    # Precision (direct)
    assert sc["precision_pool"]["tp"] == 7
    assert sc["precision_pool"]["fp"] == 3
    assert approx(sc["precision_pool"]["precision"], 0.7000)

    # Recall (extrapolated)
    rc = sc["recall_extrapolated"]
    assert rc["random_sample_size"] == 20
    assert rc["random_sample_positives"] == 2
    assert approx(rc["fn_rate_in_negatives"], 0.1000)
    assert approx(rc["estimated_total_fn"], 9.0000)
    assert approx(rc["recall"], 0.4375)

    # F1
    assert approx(sc["f1"], 0.5385, tol=1e-3)

    # Brier
    assert sc["brier_score"]["n_used"] == 30
    assert approx(sc["brier_score"]["value"], 0.1433, tol=1e-3)


def test_wilson():
    # Sanity: Wilson interval for 5/10 should bracket 0.5 reasonably.
    lo, hi = wilson_interval(5, 10)
    assert lo < 0.5 < hi
    assert 0.20 < lo < 0.30
    assert 0.70 < hi < 0.80
    # Edge: 0/0 → trivial (0, 1)
    assert wilson_interval(0, 0) == (0.0, 1.0)
    # Edge: 0/100 → upper bound > 0
    lo0, hi0 = wilson_interval(0, 100)
    assert lo0 == 0.0
    assert 0.0 < hi0 < 0.05


def test_f1_edge():
    assert f1_score(0.0, 0.0) == 0.0
    assert f1_score(1.0, 1.0) == 1.0
    assert approx(f1_score(0.5, 0.5), 0.5)


def test_reliability_table_shape():
    items = [(0.05, 0), (0.15, 0), (0.25, 1), (0.95, 1), (0.05, 0)]
    table = reliability_table(items, n_bins=10)
    assert len(table) == 10
    # First bin (0.0-0.1) should have 2 items, all negative
    first = table[0]
    assert first["n"] == 2
    assert approx(first["frac_positive"], 0.0)
    # Last bin (0.9-1.0) should have 1 item, positive
    last = table[9]
    assert last["n"] == 1
    assert approx(last["frac_positive"], 1.0)


def test_no_model_positives():
    # If model never says positive, precision is undefined; harness should not crash.
    predictions = [{"id": f"x-{i}", "prediction": False, "p_positive": 0.1, "model_id": "t", "prompt_hash": "h"} for i in range(10)]
    labels = [{"id": "x-0", "label": "negative"}, {"id": "x-1", "label": "positive"}]
    sc = evaluate(predictions, labels, corpus_size=10, random_sample_size=2)
    assert sc["precision_pool"]["pool_labeled_total"] == 0
    assert sc["precision_pool"]["precision"] is None
    assert sc["recall_extrapolated"]["random_sample_positives"] == 1
    # F1 undefined if precision is NaN
    assert sc["f1"] is None


def main():
    tests = [
        ("synthetic pool-and-extrapolate", test_synthetic),
        ("wilson interval", test_wilson),
        ("f1 edge cases", test_f1_edge),
        ("reliability table shape", test_reliability_table_shape),
        ("no model positives", test_no_model_positives),
    ]
    failures = []
    for name, fn in tests:
        try:
            fn()
            print(f"  ok   {name}")
        except AssertionError as e:
            failures.append(name)
            print(f"  FAIL {name}: {e}")
    print(f"\n{len(tests) - len(failures)}/{len(tests)} passed")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
