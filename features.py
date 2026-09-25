"""
Computes simple temporal/behavioural features for one trajectory (run).
These features feed the anomaly detector. Kept intentionally simple
(no foundation model) per the 6-day MVP scope.
"""
from datetime import datetime


def compute_features(actions):
    """
    actions: list of tuples from logger.get_run_actions
              (timestamp, tool, args, risk_score, risk_level, policy_decision, final_decision, reason)
    Returns a dict of numeric features describing the whole trajectory.
    """
    if not actions:
        return {}

    timestamps = [datetime.fromisoformat(a[0]) for a in actions]
    tools = [a[1] for a in actions]
    risk_scores = [a[3] for a in actions]
    decisions = [a[6] for a in actions]

    duration = (timestamps[-1] - timestamps[0]).total_seconds()
    duration = max(duration, 0.01)  # avoid divide by zero

    time_gaps = [
        (timestamps[i] - timestamps[i - 1]).total_seconds()
        for i in range(1, len(timestamps))
    ]
    avg_gap = sum(time_gaps) / len(time_gaps) if time_gaps else 0

    num_actions = len(actions)
    actions_per_minute = num_actions / (duration / 60)

    avg_risk = sum(risk_scores) / num_actions
    max_risk = max(risk_scores)

    blocked_count = decisions.count("BLOCK")
    flagged_count = decisions.count("FLAG")
    blocked_ratio = blocked_count / num_actions

    unique_tools = len(set(tools))
    repeated_tool_ratio = 1 - (unique_tools / num_actions)

    # crude "unusual combination" signal: sensitive tool pair present
    sensitive_pair = 1 if ("search_database" in tools and "upload_file" in tools) else 0

    return {
        "num_actions": num_actions,
        "duration_sec": duration,
        "avg_time_gap": avg_gap,
        "actions_per_minute": actions_per_minute,
        "avg_risk": avg_risk,
        "max_risk": max_risk,
        "blocked_count": blocked_count,
        "flagged_count": flagged_count,
        "blocked_ratio": blocked_ratio,
        "repeated_tool_ratio": repeated_tool_ratio,
        "sensitive_pair": sensitive_pair,
    }
