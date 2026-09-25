"""Runtime enforcement boundary for the dynamic AgentGuard demo."""
import time
from dataclasses import dataclass

from live_tools import LIVE_TOOL_REGISTRY


@dataclass
class LiveDecision:
    technical_safety: str
    objective_alignment: float
    alignment_label: str
    trajectory_risk: str
    decision: str
    reason: str
    policy: str
    task_authorized: bool


class LiveAgentGuard:
    """Agent 2 result + deterministic enforcement boundary.

    The evaluator LLM recommends a decision, but AgentGuard does not blindly
    trust it. Unknown tools and non-allowlisted actions are blocked locally.
    """

    def __init__(self, objective, allowed_tools=None):
        self.objective = objective
        self.allowed_tools = set(allowed_tools or LIVE_TOOL_REGISTRY.keys())
        self.history = []
        self.events = []
        self.terminated = False

    def enforce(self, tool, args, evaluator_result):
        task_authorized = tool in self.allowed_tools and tool in LIVE_TOOL_REGISTRY
        policy = LIVE_TOOL_REGISTRY.get(tool, {}).get("policy", "DENY")
        if not task_authorized or policy != "ALLOW":
            decision = "TERMINATE"
            reason = "Tool is outside the bounded AgentGuard allowlist."
        else:
            decision = evaluator_result.get("decision", "PAUSE")
            if decision not in {"ALLOW", "FLAG", "PAUSE", "TERMINATE"}:
                decision = "PAUSE"
            reason = str(evaluator_result.get("reason", "Evaluator did not provide a reason."))

            # Critical evaluator output is always terminal.
            if evaluator_result.get("trajectory_risk") == "CRITICAL":
                decision = "TERMINATE"

            # Low alignment cannot silently execute even when the API is safe.
            try:
                alignment = float(evaluator_result.get("objective_alignment", 0))
            except (TypeError, ValueError):
                alignment = 0.0
            if alignment < 0.30 and decision == "ALLOW":
                decision = "PAUSE"
                reason = "Objective alignment is below the execution threshold. " + reason

        event = {
            "timestamp": time.time(),
            "objective": self.objective,
            "tool": tool,
            "args": args,
            "task_authorized": task_authorized,
            "policy": policy,
            "technical_safety": evaluator_result.get("technical_safety", "UNKNOWN"),
            "objective_alignment": evaluator_result.get("objective_alignment", 0),
            "alignment_label": evaluator_result.get("alignment_label", "LOW"),
            "trajectory_risk": evaluator_result.get("trajectory_risk", "UNKNOWN"),
            "decision": decision,
            "reason": reason,
        }
        self.events.append(event)

        if decision == "TERMINATE":
            self.terminated = True

        return event

    def execute(self, tool, args):
        if self.terminated:
            raise RuntimeError("AgentGuard has terminated this run.")
        item = LIVE_TOOL_REGISTRY[tool]
        result = item["callable"](**args)
        self.history.append({"tool": tool, "args": args, "result": result})
        return result
