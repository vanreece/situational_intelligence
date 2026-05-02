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

    # Recall (extrapolated) — synthetic case has no sample_role, so legacy mode applies.
    # In legacy mode all 20 labeled model-negatives serve as the "random_sample"
    # for FN extrapolation, and pool_direct_fn = 0 (no items have sample_role=pool).
    rc = sc["recall_extrapolated"]
    assert rc["random_sample_size"] == 20
    assert rc["random_sample_positives"] == 2
    assert approx(rc["fn_rate_in_unsampled"], 0.1000)
    assert rc["pool_direct_fn"] == 0  # no pool-stratum items in synthetic
    # 70 unsampled model-negatives × 0.10 = 7; plus 0 pool_fn = 7 total estimated FN
    # Note: the legacy estimator (v0.1.0) over-counted to 9 because it included
    # the 20 labeled items in the extrapolation base. The fix correctly excludes them.
    assert approx(rc["estimated_total_fn"], 7.0000)
    assert approx(rc["recall"], 7 / (7 + 7))  # = 0.5

    # F1: with the v0.2.0 fix, recall = 7/(7+7) = 0.5, so F1 = 2*0.7*0.5/(0.7+0.5) = 0.5833
    # (v0.1.0 reported 0.5385 because it inflated FN by double-counting labeled items.)
    assert approx(sc["f1"], 0.5833, tol=1e-3)

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


def test_stratification_fix_demonstrates_bias_correction():
    """si-2t4: stratified sampling fix.

    Scenario: a labels file built from a *prior* classifier's predictions is now
    being used to evaluate a *different* classifier. The labeled pool has two
    strata:
      - 10 'pool' items (exhaustive labels of the prior classifier's positives)
      - 100 'random_sample' items (uniform random sample of the prior classifier's
        negatives)
    Truth: the underlying corpus has a 1% base rate of positives among items
    that the prior classifier called negative. The new classifier under
    evaluation here has TP=8 (out of 10 in pool, where 8 happened to actually
    be positive under both classifiers), and DROPS 3 prior pool-positives by
    re-classifying them as model-negatives (they're our FNs in the pool stratum).

    Truth recall: TP / (TP + FN_pool + FN_unsampled_extrapolated)
                = 8 / (8 + 3 + 0.01 * (n_unsampled))
    For 1000 corpus, 110 labeled, 890 unsampled: FN_unsampled ≈ 8.9.
    Recall = 8 / (8 + 3 + 8.9) ≈ 0.40.

    The legacy estimator (without stratification) would compute FN_rate from
    ALL labeled model-negatives (=110), of which 3 are positive (the
    re-classified pool items). FN_rate = 3/110 ≈ 0.027. Total FN = 0.027 * 890
    + the 3 already counted in pool? No — legacy DIDN'T separate pool from
    sample, so it just used 0.027 * (total model-negatives) = 0.027 * 992
    (assuming 1000 - 8 model-positives) = 26.8. Recall_legacy = 8/(8+26.8) ≈ 0.23.

    The fix should report recall ≈ 0.40, not 0.23.
    """
    predictions = []
    labels = []
    # 10 model-positives in the labeled pool — 8 truly positive, 2 truly negative
    for i in range(8):
        predictions.append({"id": f"tp-{i}", "prediction": True, "p_positive": 0.9, "model_id": "test", "prompt_hash": "h"})
        labels.append({"id": f"tp-{i}", "label": "positive", "sample_role": "pool"})
    for i in range(2):
        predictions.append({"id": f"fp-{i}", "prediction": True, "p_positive": 0.9, "model_id": "test", "prompt_hash": "h"})
        labels.append({"id": f"fp-{i}", "label": "negative", "sample_role": "pool"})
    # 3 prior-pool items that are now model-NEGATIVES (FN under current classifier)
    # Labeled positive in the pool stratum.
    for i in range(3):
        predictions.append({"id": f"pool-fn-{i}", "prediction": False, "p_positive": 0.4, "model_id": "test", "prompt_hash": "h"})
        labels.append({"id": f"pool-fn-{i}", "label": "positive", "sample_role": "pool"})
    # 100 random-sample items of prior classifier's model-negatives, all also model-negatives now.
    # 1 of them is actually positive (1% base rate). Truly representative of the unsampled negatives.
    for i in range(99):
        predictions.append({"id": f"rs-tn-{i}", "prediction": False, "p_positive": 0.05, "model_id": "test", "prompt_hash": "h"})
        labels.append({"id": f"rs-tn-{i}", "label": "negative", "sample_role": "random_sample"})
    predictions.append({"id": "rs-fn-0", "prediction": False, "p_positive": 0.3, "model_id": "test", "prompt_hash": "h"})
    labels.append({"id": "rs-fn-0", "label": "positive", "sample_role": "random_sample"})
    # 887 unlabeled model-negatives in the corpus
    for i in range(887):
        predictions.append({"id": f"unlabeled-tn-{i}", "prediction": False, "p_positive": 0.05, "model_id": "test", "prompt_hash": "h"})

    sc = evaluate(predictions, labels, corpus_size=1000, random_sample_size=100)

    rc = sc["recall_extrapolated"]
    # Pool-direct FN: 3 (the pool-stratum positives that are model-negatives)
    assert rc["pool_direct_fn"] == 3, f"expected pool_direct_fn=3, got {rc['pool_direct_fn']}"
    # Random sample: 100 items, 1 positive
    assert rc["random_sample_size"] == 100
    assert rc["random_sample_positives"] == 1
    assert approx(rc["fn_rate_in_unsampled"], 0.01)
    # Unsampled model-negatives: 1000 - 10 (model-pos) - 113 (labeled model-neg) = 877
    # Actually: total = 1000, model_pos = 10, model_neg = 990, labeled model_neg = 113 (3+100+10? no)
    # Let me recount: model_neg = 990 (3 pool-fn + 100 rs + 887 unlabeled). labeled = 3 + 100 = 103.
    # n_unsampled = 990 - 103 = 887.
    # extrapolated = 0.01 * 887 = 8.87
    assert rc["stratification"]["n_unsampled_model_negatives"] == 887, f"got {rc['stratification']['n_unsampled_model_negatives']}"
    assert approx(rc["extrapolated_unsampled_fn"], 8.87, tol=0.01)
    # Total FN = 3 + 8.87 = 11.87
    assert approx(rc["estimated_total_fn"], 11.87, tol=0.01)
    # Recall = 8 / (8 + 11.87) ≈ 0.4026
    assert approx(rc["recall"], 0.4026, tol=0.001)
    # Precision = 8/10 = 0.8
    assert approx(sc["precision_pool"]["precision"], 0.8000)
    # F1 = 2*0.8*0.4026 / (0.8 + 0.4026) ≈ 0.5358
    assert approx(sc["f1"], 0.5358, tol=0.001)


def test_legacy_fallback_when_no_sample_role():
    """If labels file has no sample_role, fall back to legacy (un-stratified) behavior.
    All labeled model-negatives are treated as the 'random sample' for FN extrapolation,
    pool_direct_fn=0. This preserves backward compatibility with v0.1.0 labels.
    """
    predictions = [
        {"id": "p1", "prediction": True, "p_positive": 0.9, "model_id": "t", "prompt_hash": "h"},
        {"id": "n1", "prediction": False, "p_positive": 0.1, "model_id": "t", "prompt_hash": "h"},
        {"id": "n2", "prediction": False, "p_positive": 0.1, "model_id": "t", "prompt_hash": "h"},
        {"id": "n3", "prediction": False, "p_positive": 0.1, "model_id": "t", "prompt_hash": "h"},
    ]
    # Labels WITHOUT sample_role
    labels = [
        {"id": "p1", "label": "positive"},
        {"id": "n1", "label": "negative"},
        {"id": "n2", "label": "positive"},  # FN
    ]
    sc = evaluate(predictions, labels, corpus_size=4, random_sample_size=2)
    rc = sc["recall_extrapolated"]
    # Without sample_role, pool_direct_fn = 0 (no items have pool role)
    assert rc["pool_direct_fn"] == 0
    # Random sample falls back to all labeled model-negatives: n1 (neg), n2 (pos) = 2 items, 1 pos
    assert rc["random_sample_size"] == 2
    assert rc["random_sample_positives"] == 1
    assert approx(rc["fn_rate_in_unsampled"], 0.5)
    # n_model_negatives = 3, n_labeled_model_negatives = 2, n_unsampled = 1
    assert rc["stratification"]["n_unsampled_model_negatives"] == 1
    # extrapolated = 0.5 * 1 = 0.5; total = 0 + 0.5 = 0.5
    assert approx(rc["estimated_total_fn"], 0.5)
    # recall = 1 / (1 + 0.5) = 0.667
    assert approx(rc["recall"], 0.6667, tol=0.001)


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
        ("si-2t4 stratification fix demonstrates bias correction", test_stratification_fix_demonstrates_bias_correction),
        ("legacy fallback when no sample_role", test_legacy_fallback_when_no_sample_role),
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
