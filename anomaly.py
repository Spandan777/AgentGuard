"""
Lightweight anomaly detector using Isolation Forest.
Trains on whatever trajectories are currently logged, then scores
the most recent trajectory as normal or anomalous.

Note: with very few logged runs, this will not be statistically
meaningful yet -- it becomes useful once we have the 100-150
evaluation scenarios in Day 5.
"""
import numpy as np
from sklearn.ensemble import IsolationForest

FEATURE_KEYS = [
    "num_actions", "duration_sec", "avg_time_gap", "actions_per_minute",
    "avg_risk", "max_risk", "blocked_count", "flagged_count",
    "blocked_ratio", "repeated_tool_ratio", "sensitive_pair"
]


def features_to_vector(feat_dict):
    return [feat_dict.get(k, 0) for k in FEATURE_KEYS]


def detect_anomaly(all_feature_dicts, target_feature_dict):
    """
    all_feature_dicts: list of feature dicts from previously logged runs
    target_feature_dict: the run we want to classify
    Returns (is_anomaly: bool, anomaly_score: float)
    """
    if len(all_feature_dicts) < 5:
        return False, 0.0  # not enough data to train meaningfully yet

    X = np.array([features_to_vector(f) for f in all_feature_dicts])
    model = IsolationForest(contamination=0.2, random_state=42)
    model.fit(X)

    target_vec = np.array([features_to_vector(target_feature_dict)])
    prediction = model.predict(target_vec)[0]   # 1 = normal, -1 = anomaly
    score = model.decision_function(target_vec)[0]  # lower = more anomalous

    is_anomaly = prediction == -1
    return is_anomaly, float(score)
