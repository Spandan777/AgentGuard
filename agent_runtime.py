"""
AgentGuard Runtime
------------------

Central runtime middleware for the AgentGuard demonstration.

Every agent tool request passes through:

1. Task-level authorization
2. Global policy
3. Objective alignment
4. Risk scoring
5. Trajectory analysis
6. Enforcement

All tools are simulated.
"""

import time

from dataclasses import dataclass
from typing import Any

from tools import TOOL_REGISTRY
from policy import check_policy
from risk import score_action, escalation_decision
from objective import objective_alignment


# ============================================================
# TOOL CALL
# ============================================================

@dataclass
class ToolCall:

    tool: str
    args: dict[str, Any]


# ============================================================
# RUNTIME EXCEPTIONS
# ============================================================

class AgentTerminated(Exception):
    pass


class AgentPaused(Exception):
    pass


# ============================================================
# AGENTGUARD RUNTIME
# ============================================================

class AgentGuardRuntime:

    def __init__(
        self,
        allowed_tools=None,
        objective="Find and summarize my project report",
    ):

        self.history = []

        self.running = True

        self.paused = False

        # Tool request waiting for human approval.
        self.pending_call = None

        # Original task/objective.
        self.objective = objective

        # Task-level authorization.
        self.allowed_tools = set(
            allowed_tools or TOOL_REGISTRY.keys()
        )


    # ========================================================
    # INSPECTION PIPELINE
    # ========================================================

    def inspect(self, call: ToolCall):

        # ----------------------------------------------------
        # 1. TASK AUTHORIZATION
        # ----------------------------------------------------

        task_authorized = (
            call.tool in self.allowed_tools
        )


        # ----------------------------------------------------
        # 2. GLOBAL POLICY
        # ----------------------------------------------------

        policy_decision, policy_reason = check_policy(
            call.tool,
            call.args,
        )

        effective_policy = policy_decision

        if not task_authorized:

            effective_policy = "DENY"

            policy_reason = (
                f"Tool '{call.tool}' is not authorized "
                f"for the current task"
            )


        # ----------------------------------------------------
        # 3. OBJECTIVE ALIGNMENT
        # ----------------------------------------------------

        alignment_score, alignment_reason = (
            objective_alignment(
                self.objective,
                call.tool,
                call.args,
            )
        )


        # ----------------------------------------------------
        # 4. RISK SCORE
        # ----------------------------------------------------

        risk_score, risk_level, risk_reason = score_action(
            call.tool,
            call.args,
            effective_policy,
            self.history,
        )


        # ----------------------------------------------------
        # OBJECTIVE DEVIATION
        #
        # IMPORTANT:
        #
        # Objective deviation is reported separately.
        # It does NOT artificially add 15 points to the
        # risk score anymore.
        #
        # This preserves the HITL checkpoint:
        #
        # access_admin_panel = 70 -> PAUSE
        #
        # rather than:
        #
        # 70 + 15 = 85 -> TERMINATE
        # ----------------------------------------------------

        if alignment_score < 0.30:

            risk_reason = (
                "significant objective deviation; "
                + risk_reason
            )


        # ----------------------------------------------------
        # TASK SCOPE VIOLATION
        # ----------------------------------------------------

        if not task_authorized:

            risk_reason = (
                "task-level tool authorization violation; "
                + risk_reason
            )

            risk_score = min(
                risk_score + 25,
                100,
            )


        # ----------------------------------------------------
        # RECALCULATE RISK LEVEL
        # ----------------------------------------------------

        if risk_score <= 30:

            risk_level = "LOW"

        elif risk_score <= 60:

            risk_level = "MEDIUM"

        elif risk_score <= 80:

            risk_level = "HIGH"

        else:

            risk_level = "CRITICAL"


        # ----------------------------------------------------
        # 5. ESCALATION DECISION
        # ----------------------------------------------------

        decision = escalation_decision(
            risk_score,
            effective_policy,
        )


        # ----------------------------------------------------
        # OBJECTIVE-AWARE ENFORCEMENT
        #
        # A severely misaligned action should not silently
        # execute even if the numerical risk happens to be
        # below the PAUSE threshold.
        #
        # We use PAUSE here rather than adding artificial
        # risk points.
        # ----------------------------------------------------

        if (
            alignment_score < 0.30
            and decision == "ALLOW"
        ):

            decision = "PAUSE"

            risk_reason = (
                "objective alignment below safety threshold; "
                + risk_reason
            )


        # ----------------------------------------------------
        # UNAUTHORIZED TOOLS
        #
        # An unauthorized tool must never silently execute.
        # ----------------------------------------------------

        if (
            not task_authorized
            and decision == "ALLOW"
        ):

            decision = "PAUSE"


        # ----------------------------------------------------
        # 6. SECURITY EVENT
        # ----------------------------------------------------

        event = {

            "timestamp":
                time.time(),

            "tool":
                call.tool,

            "args":
                call.args,

            "objective":
                self.objective,

            "objective_alignment":
                alignment_score,

            "objective_alignment_reason":
                alignment_reason,

            "task_authorized":
                task_authorized,

            "policy":
                effective_policy,

            "policy_reason":
                policy_reason,

            "risk":
                risk_score,

            "risk_level":
                risk_level,

            "risk_reason":
                risk_reason,

            "decision":
                decision,
        }


        self.history.append(event)


        # ----------------------------------------------------
        # 7. SECURITY EVENT OUTPUT
        # ----------------------------------------------------

        print("\n" + "=" * 60)

        print(
            "AGENTGUARD SECURITY EVENT"
        )

        print("=" * 60)

        print(
            f"Tool:             {call.tool}"
        )

        print(
            f"Task authorized:  {task_authorized}"
        )

        print(
            f"Objective align:  "
            f"{alignment_score * 100:.0f}%"
        )

        print(
            f"Policy:           {effective_policy}"
        )

        print(
            f"Risk:             {risk_score}/100"
        )

        print(
            f"Level:            {risk_level}"
        )

        print(
            f"Decision:         {decision}"
        )


        print("\nPolicy reason:")

        print(
            policy_reason
        )


        print("\nObjective reason:")

        print(
            alignment_reason
        )


        print("\nRisk reason:")

        print(
            risk_reason
        )


        # ----------------------------------------------------
        # 8. ENFORCEMENT
        # ----------------------------------------------------

        if decision == "TERMINATE":

            self.running = False

            self.pending_call = None

            raise AgentTerminated(
                "AgentGuard terminated execution "
                f"of '{call.tool}'"
            )


        if decision == "PAUSE":

            self.paused = True

            self.pending_call = call

            raise AgentPaused(
                "AgentGuard paused execution "
                f"of '{call.tool}'"
            )


        return event


    # ========================================================
    # TOOL EXECUTION
    # ========================================================

    def execute(self, call: ToolCall):

        if not self.running:

            raise AgentTerminated(
                "AgentGuard has already terminated "
                "this agent."
            )


        if self.paused:

            raise AgentPaused(
                "AgentGuard is waiting for "
                "human approval."
            )


        # Security inspection happens BEFORE execution.
        self.inspect(call)


        return self._execute_tool(call)


    # ========================================================
    # INTERNAL TOOL EXECUTION
    # ========================================================

    def _execute_tool(self, call: ToolCall):

        tool = TOOL_REGISTRY.get(
            call.tool
        )


        if tool is None:

            raise ValueError(
                f"Unknown tool requested: "
                f"{call.tool}"
            )


        print(
            f"\n[AGENT] Executing "
            f"{call.tool}..."
        )


        result = tool(
            **call.args
        )


        if self.history:

            self.history[-1][
                "result"
            ] = result


        print(
            "[AGENT] Result:"
        )

        print(
            result
        )


        return result


    # ========================================================
    # HUMAN APPROVAL
    # ========================================================

    def approve_once(self):

        if (
            not self.paused
            or self.pending_call is None
        ):

            print(
                "[AgentGuard] No paused action "
                "requires approval."
            )

            return None


        call = self.pending_call


        print("\n" + "=" * 60)

        print(
            "AGENTGUARD HUMAN APPROVAL"
        )

        print("=" * 60)


        print(
            f"Approved tool: {call.tool}"
        )


        # Clear the pause.
        self.paused = False

        self.pending_call = None


        print(
            "[AgentGuard] Human approved "
            "this action once."
        )


        # The action has already been inspected.
        # Execute it once without re-running inspection.
        return self._execute_tool(
            call
        )


    # ========================================================
    # TERMINATE
    # ========================================================

    def terminate(self):

        self.running = False

        self.paused = False

        self.pending_call = None


        print(
            "\n[AgentGuard] AGENT TERMINATED"
        )


# ============================================================
# DEMO AGENT
# ============================================================

class DemoAgent:

    def __init__(
        self,
        runtime: AgentGuardRuntime,
    ):

        self.runtime = runtime


    def use_tool(
        self,
        tool: str,
        **kwargs,
    ):

        call = ToolCall(
            tool=tool,
            args=kwargs,
        )


        try:

            return self.runtime.execute(
                call
            )


        except AgentPaused as exc:

            print(
                "\n[AGENTGUARD] PAUSED"
            )

            print(
                exc
            )


            return {

                "status":
                    "PAUSED",

                "reason":
                    str(exc),
            }


        except AgentTerminated as exc:

            print(
                "\n[AGENTGUARD] TERMINATED"
            )

            print(
                exc
            )


            return {

                "status":
                    "TERMINATED",

                "reason":
                    str(exc),
            }


    def approve_pending_action(self):

        try:

            result = (
                self.runtime.approve_once()
            )


            if result is None:

                return {
                    "status":
                        "NO_PENDING_ACTION"
                }


            return result


        except AgentTerminated as exc:

            return {

                "status":
                    "TERMINATED",

                "reason":
                    str(exc),
            }


# ============================================================
# FACTORY
# ============================================================

def create_agent(
    allowed_tools=None,
    objective="Find and summarize my project report",
):

    runtime = AgentGuardRuntime(

        allowed_tools=allowed_tools,

        objective=objective,
    )


    agent = DemoAgent(
        runtime
    )


    return agent, runtime