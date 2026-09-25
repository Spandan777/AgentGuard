"""Safe, simulated tools for the AgentGuard sandbox.

No real files, email accounts, databases, credentials or external servers are
accessed. Every tool returns a simulated result for the live demonstration.
"""


def search_files(query: str):
    return {"tool": "search_files", "result": f"Found project report matching: {query}"}


def read_file(filename: str):
    return {"tool": "read_file", "result": f"Read simulated document: {filename}"}


def summarize(filename: str):
    return {"tool": "summarize", "result": f"Generated a simulated summary of {filename}"}


def search_database(query: str):
    return {"tool": "search_database", "result": f"Simulated database returned 3 records for '{query}'"}


def send_email(recipient: str, subject: str):
    return {"tool": "send_email", "result": f"Simulated email prepared for {recipient} with subject '{subject}'"}


def external_api(endpoint: str, payload: str):
    return {"tool": "external_api", "result": f"Simulated external API request to {endpoint}"}


def upload_file(filename: str, destination: str):
    return {"tool": "upload_file", "result": f"Simulated upload of {filename} to {destination}"}


def request_admin_access(reason: str):
    return {"tool": "request_admin_access", "result": f"Simulated privileged-access request: {reason}"}


def access_admin_panel(resource: str):
    return {"tool": "access_admin_panel", "result": f"Simulated access to admin resource: {resource}"}


def modify_permissions(target: str, change: str):
    return {"tool": "modify_permissions", "result": f"Simulated permission change on {target}: {change}"}


TOOL_REGISTRY = {
    "search_files": search_files,
    "read_file": read_file,
    "summarize": summarize,
    "search_database": search_database,
    "send_email": send_email,
    "external_api": external_api,
    "upload_file": upload_file,
    "request_admin_access": request_admin_access,
    "access_admin_panel": access_admin_panel,
    "modify_permissions": modify_permissions,
}
