"""Explainable trajectory-aware risk engine."""

BASE_RISK = {
    "search_files": 5,
    "read_file": 10,
    "summarize": 5,
    "search_database": 15,
    "send_email": 10,
    "external_api": 35,
    "upload_file": 60,
    "request_admin_access": 35,
    "access_admin_panel": 35,
    "modify_permissions": 55,
}

SENSITIVE_KEYWORDS = ["credential", "password", "secret", "external", "sensitive"]


def score_action(tool_name: str, args: dict, policy_decision: str, history: list):
    score = BASE_RISK.get(tool_name, 20)
    reasons = [f"base risk for '{tool_name}'"]

    arg_text = " ".join(str(v) for v in args.values()).lower()
    if any(word in arg_text for word in SENSITIVE_KEYWORDS):
        score += 20
        reasons.append("sensitive resource or destination detected")

    if policy_decision == "DENY":
        score += 20
        reasons.append("current policy denies this tool")

    previous_tools = [h["tool"] for h in history]
    if tool_name == "external_api" and "search_database" in previous_tools:
        score += 10
        reasons.append("external communication follows sensitive database access")

    if tool_name == "upload_file" and ("search_database" in previous_tools or "external_api" in previous_tools):
        score += 15
        reasons.append("upload follows sensitive access/external communication")

    if tool_name == "access_admin_panel" and "request_admin_access" in previous_tools:
        score += 15
        reasons.append("privileged panel access follows an unauthorized access request")

    if tool_name == "modify_permissions" and "access_admin_panel" in previous_tools:
        score += 15
        reasons.append("permission modification follows privileged admin-panel access")

    score = min(score, 100)

    if score <= 30:
        level = "LOW"
    elif score <= 60:
        level = "MEDIUM"
    elif score <= 80:
        level = "HIGH"
    else:
        level = "CRITICAL"

    return score, level, "; ".join(reasons)


def escalation_decision(risk_score: int, policy_decision: str):
    """Map risk to an operational response."""
    if risk_score >= 81:
        return "TERMINATE"
    if risk_score >= 61:
        return "PAUSE"
    if risk_score >= 31:
        return "FLAG"
    return "ALLOW"
