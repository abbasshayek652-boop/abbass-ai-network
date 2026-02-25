from __future__ import annotations

from typing import Dict, Iterable, Tuple

from learning.models.supervised import Dataset, train_classifier


def run_hpo(dataset: Dataset, target: str, param_grid: Dict[str, Iterable[int]]) -> Tuple[Dict[str, int], float]:
    """Brute-force over param combinations returning the best accuracy."""

    best_score = float("-inf")
    best_params: Dict[str, int] = {}
    if not dataset:
        return best_params, best_score
    keys = list(param_grid.keys())
    combos = [[]]
    for key in keys:
        values = list(param_grid[key]) or [1]
        combos = [combo + [value] for combo in combos for value in values]
    for combo in combos:
        params = dict(zip(keys, combo))
        result = train_classifier(dataset, target)
        score = result.metrics.get("accuracy", 0.0)
        if score > best_score:
            best_score = score
            best_params = params
    return best_params, best_score
