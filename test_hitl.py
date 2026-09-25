from agent_runtime import create_agent


allowed_tools = {
    "search_files",
    "request_admin_access",
    "access_admin_panel",
    "modify_permissions",
}


agent, runtime = create_agent(
    allowed_tools=allowed_tools
)


print("\n--- STEP 1 ---")

agent.use_tool(
    "search_files",
    query="admin configuration"
)


print("\n--- STEP 2 ---")

agent.use_tool(
    "request_admin_access",
    reason="Need elevated access"
)


print("\n--- STEP 3 ---")

result = agent.use_tool(
    "access_admin_panel",
    resource="system administration"
)


print("\n--- HUMAN APPROVAL ---")

if result.get("status") == "PAUSED":

    agent.approve_pending_action()


print("\n--- STEP 4 ---")

agent.use_tool(
    "modify_permissions",
    target="agent_service",
    change="grant elevated privileges"
)


print("\n--- FINAL STATE ---")

print(
    "Running:",
    runtime.running
)

print(
    "Paused:",
    runtime.paused
)

print(
    "Events:",
    len(runtime.history)
)