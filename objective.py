"""
AgentGuard Objective Alignment Engine
--------------------------------------

Measures how strongly an individual tool action contributes
to the agent's original objective.

This MVP uses an explainable rule-based approach.
"""

TOOL_ALIGNMENT = {
    "search_files": 0.95,
    "read_file": 0.90,
    "summarize": 0.95,
    "search_database": 0.20,
    "send_email": 0.10,
    "external_api": 0.10,
    "upload_file": 0.05,
    "request_admin_access": 0.10,
    "access_admin_panel": 0.05,
    "modify_permissions": 0.01,
}


def objective_alignment(
    objective: str,
    tool_name: str,
    args: dict,
) -> tuple[float, str]:

    objective_text = objective.lower()

    # --------------------------------------------------
    # File search
    # --------------------------------------------------

    if tool_name == "search_files":

        if any(
            word in objective_text
            for word in [
                "find",
                "search",
                "locate",
                "report",
                "document",
                "file",
            ]
        ):
            return (
                0.95,
                "Searching files directly contributes to the objective.",
            )


    # --------------------------------------------------
    # File reading
    # --------------------------------------------------

    if tool_name == "read_file":

        if any(
            word in objective_text
            for word in [
                "read",
                "analyze",
                "review",
                "report",
                "document",
                "summarize",
            ]
        ):
            return (
                0.90,
                "Reading the requested document contributes to the objective.",
            )


    # --------------------------------------------------
    # Summarization
    # --------------------------------------------------

    if tool_name == "summarize":

        if any(
            word in objective_text
            for word in [
                "summarize",
                "summary",
                "report",
                "analyze",
                "review",
            ]
        ):
            return (
                0.95,
                "Summarization directly contributes to the objective.",
            )


    # --------------------------------------------------
    # Database
    # --------------------------------------------------

    if tool_name == "search_database":

        if any(
            word in objective_text
            for word in [
                "database",
                "records",
                "customer data",
                "database records",
            ]
        ):
            return (
                0.75,
                "Database access appears relevant to the stated objective.",
            )

        return (
            0.20,
            "Database access is not clearly required by the objective.",
        )


    # --------------------------------------------------
    # Email
    # --------------------------------------------------

    if tool_name == "send_email":

        if any(
            word in objective_text
            for word in [
                "email",
                "send",
                "mail",
                "notify",
            ]
        ):
            return (
                0.80,
                "Sending an email is explicitly related to the objective.",
            )

        return (
            0.10,
            "Email communication is not required by the objective.",
        )


    # --------------------------------------------------
    # External API
    # --------------------------------------------------

    if tool_name == "external_api":

        if any(
            word in objective_text
            for word in [
                "api",
                "external service",
                "weather",
                "external data",
            ]
        ):
            return (
                0.75,
                "External API access is explicitly related to the objective.",
            )

        return (
            0.10,
            "External communication is not required by the objective.",
        )


    # --------------------------------------------------
    # File upload
    # --------------------------------------------------

    if tool_name == "upload_file":

        if any(
            word in objective_text
            for word in [
                "upload",
                "submit",
                "send file",
                "share file",
            ]
        ):
            return (
                0.75,
                "Uploading the file is explicitly part of the objective.",
            )

        return (
            0.05,
            "Uploading data is not required by the objective.",
        )


    # --------------------------------------------------
    # Privilege escalation
    # --------------------------------------------------

    if tool_name == "request_admin_access":

        if any(
            word in objective_text
            for word in [
                "admin",
                "administrator",
                "privileged",
                "permissions",
            ]
        ):
            return (
                0.60,
                "Administrative access may be related to the objective.",
            )

        return (
            0.10,
            "Administrative access is not required by the objective.",
        )


    if tool_name == "access_admin_panel":

        if any(
            word in objective_text
            for word in [
                "admin",
                "administrator",
                "privileged",
            ]
        ):
            return (
                0.50,
                "Admin-panel access may be related to the objective.",
            )

        return (
            0.05,
            "Admin-panel access is not required by the objective.",
        )


    if tool_name == "modify_permissions":

        if any(
            word in objective_text
            for word in [
                "permissions",
                "administrator",
                "admin",
            ]
        ):
            return (
                0.50,
                "Permission modification may be related to the objective.",
            )

        return (
            0.01,
            "Changing permissions is unrelated to the objective.",
        )


    # --------------------------------------------------
    # Fallback
    # --------------------------------------------------

    score = TOOL_ALIGNMENT.get(
        tool_name,
        0.10,
    )

    return (
        score,
        "Tool has no strong relationship with the stated objective.",
    )