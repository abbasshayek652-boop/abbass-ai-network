from __future__ import annotations

from learning.models.supervised import train_classifier


def test_classifier_metrics_reasonable() -> None:
    data = [
        {"feature": 0.1, "label": 1},
        {"feature": 0.2, "label": 1},
        {"feature": -0.1, "label": 0},
        {"feature": -0.2, "label": 0},
        {"feature": 0.3, "label": 1},
        {"feature": -0.3, "label": 0},
        {"feature": 0.4, "label": 1},
        {"feature": -0.4, "label": 0},
    ]
    result = train_classifier(data, "label")
    assert result.metrics["accuracy"] >= 0.75
    assert result.metrics["roc_auc"] >= 0.5
    assert "feature" in result.feature_importances
