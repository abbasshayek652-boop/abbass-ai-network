from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple

Dataset = List[Dict[str, float]]


@dataclass
class SupervisedResult:
    model: "BaseModel"
    metrics: Dict[str, float]
    feature_importances: Dict[str, float]
    dataset_hash: str


class BaseModel:
    columns: Tuple[str, ...]

    def predict(self, rows: Dataset) -> List[float]:  # pragma: no cover - interface
        raise NotImplementedError


class NaiveClassifier(BaseModel):
    def __init__(self, columns: Sequence[str], weights: Sequence[float], bias: float) -> None:
        self.columns = tuple(columns)
        self.weights = list(weights)
        self.bias = bias

    def predict_proba(self, rows: Dataset) -> List[float]:
        scores = []
        for row in rows:
            score = self.bias
            for name, weight in zip(self.columns, self.weights):
                score += float(row.get(name, 0.0)) * weight
            scores.append(1 / (1 + math.exp(-score)))
        return scores

    def predict(self, rows: Dataset) -> List[float]:
        return [1.0 if prob > 0.5 else 0.0 for prob in self.predict_proba(rows)]


class NaiveRegressor(BaseModel):
    def __init__(self, columns: Sequence[str], weights: Sequence[float], bias: float) -> None:
        self.columns = tuple(columns)
        self.weights = list(weights)
        self.bias = bias

    def predict(self, rows: Dataset) -> List[float]:
        outputs = []
        for row in rows:
            value = self.bias
            for name, weight in zip(self.columns, self.weights):
                value += float(row.get(name, 0.0)) * weight
            outputs.append(value)
        return outputs


def _prepare_xy(dataset: Dataset, target: str) -> Tuple[List[List[float]], List[float], List[str]]:
    if not dataset:
        return [], [], []
    columns = [name for name in dataset[0] if name not in {target, "ts"}]
    X: List[List[float]] = []
    y: List[float] = []
    for row in dataset:
        X.append([float(row.get(name, 0.0)) for name in columns])
        y.append(float(row.get(target, 0.0)))
    return X, y, columns


def _logistic_regression(features: List[List[float]], target: List[float], iterations: int = 200, lr: float = 0.1) -> Tuple[List[float], float]:
    if not features:
        return [], 0.0
    n_features = len(features[0])
    weights = [0.0] * n_features
    bias = 0.0
    for _ in range(iterations):
        probs = []
        for row in features:
            score = bias + sum(val * weight for val, weight in zip(row, weights))
            score = max(min(score, 50.0), -50.0)
            probs.append(1 / (1 + math.exp(-score)))
        for j in range(n_features):
            gradient = sum((probs[i] - target[i]) * features[i][j] for i in range(len(features))) / len(features)
            weights[j] -= lr * gradient
        bias_grad = sum(probs[i] - target[i] for i in range(len(features))) / len(features)
        bias -= lr * bias_grad
    return weights, bias


def _linear_regression(features: List[List[float]], target: List[float], iterations: int = 300, lr: float = 0.05) -> Tuple[List[float], float]:
    if not features:
        return [], 0.0
    n_features = len(features[0])
    weights = [0.0] * n_features
    bias = 0.0
    for _ in range(iterations):
        preds = [bias + sum(val * weight for val, weight in zip(row, weights)) for row in features]
        for j in range(n_features):
            gradient = sum((preds[i] - target[i]) * features[i][j] for i in range(len(features))) / len(features)
            weights[j] -= lr * gradient
        bias_grad = sum(preds[i] - target[i] for i in range(len(features))) / len(features)
        bias -= lr * bias_grad
    return weights, bias


def train_classifier(dataset: Dataset, target: str) -> SupervisedResult:
    X, y, columns = _prepare_xy(dataset, target)
    weights, bias = _logistic_regression(X, y)
    model = NaiveClassifier(columns, weights, bias)
    probs = model.predict_proba(dataset)
    preds = model.predict(dataset)
    accuracy = sum(1.0 for pred, actual in zip(preds, y) if pred == actual) / len(y) if y else 0.0
    roc = sum(1.0 for prob, actual in zip(probs, y) if (prob > 0.5) == bool(actual)) / len(y) if y else 0.0
    importances = {col: abs(weight) for col, weight in zip(columns, weights)}
    return SupervisedResult(model=model, metrics={"accuracy": accuracy, "roc_auc": roc}, feature_importances=importances, dataset_hash=str(hash(tuple(y))))


def train_regressor(dataset: Dataset, target: str) -> SupervisedResult:
    X, y, columns = _prepare_xy(dataset, target)
    weights, bias = _linear_regression(X, y)
    model = NaiveRegressor(columns, weights, bias)
    preds = model.predict(dataset)
    mse = sum((pred - actual) ** 2 for pred, actual in zip(preds, y)) / len(y) if y else 0.0
    importances = {col: abs(weight) for col, weight in zip(columns, weights)}
    return SupervisedResult(model=model, metrics={"rmse": math.sqrt(mse)}, feature_importances=importances, dataset_hash=str(hash(tuple(y))))
