"""Explainable policy layer for the AgentGuard sandbox."""

POLICY_RULES = {
    "search_files": "ALLOW",
    "read_file": "ALLOW",
    "summarize": "ALLOW",
    "search_database": "ALLOW",
    "send_email": "ALLOW",
    "external_api": "DENY",
    "upload_file": "DENY",
    "request_admin_access": "ALLOW",
    "access_admin_panel": "DENY",
    "modify_permissions": "DENY",
}

APPROVED_EMAIL_DOMAINS = ["example.com"]


def check_policy(tool_name: str, args: dict):
    base_decision = POLICY_RULES.get(tool_name, "DENY")

    if tool_name == "send_email":
        recipient = args.get("recipient", "")
        domain = recipient.split("@")[-1] if "@" in recipient else ""
        if domain not in APPROVED_EMAIL_DOMAINS:
            return "DENY", f"Recipient domain '{domain}' is not approved"
        return "ALLOW", "Recipient domain approved"

    if base_decision == "DENY":
        return "DENY", f"Tool '{tool_name}' is not permitted by the current policy"

    return "ALLOW", f"Tool '{tool_name}' is permitted by policy"
