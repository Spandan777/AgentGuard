"""Orchestrates Agent 1 -> AgentGuard/Agent 2 -> real API -> Agent 1."""

from dynamic_agents import TaskAgent, EvaluatorAgent
from live_runtime import LiveAgentGuard


class DynamicRun:
    def __init__(
        self,
        objective,
        agent_provider="gemini",
        evaluator_provider="groq",
        allowed_tools=None,
        max_steps=6,
        untrusted_instruction=None,
    ):
        self.objective = objective
        self.untrusted_instruction = untrusted_instruction

        self.task_agent = TaskAgent(agent_provider)
        self.evaluator = EvaluatorAgent(evaluator_provider)

        self.guard = LiveAgentGuard(
            objective,
            allowed_tools,
        )

        self.max_steps = max_steps

        self.trace = []
        self.finished = False
        self.paused = False
        self.last_result = None

        # Stores the exact action that AgentGuard paused.
        self.pending_action = None

    def _execute_action(self, tool, args, event):
        """Execute an already-approved action."""

        try:
            result = self.guard.execute(
                tool,
                args,
            )

            self.last_result = result

            event["api_result"] = result
            event["execution"] = "EXECUTED"

        except Exception as exc:
            event["execution"] = "API_ERROR"
            event["api_error"] = str(exc)

        return event

    def step(self):
        """Run exactly one Agent 1 -> AgentGuard -> API cycle."""

        if self.finished or self.guard.terminated:
            return {
                "status": "stopped",
            }

        if self.paused:
            return {
                "status": "paused",
            }

        if len(self.trace) >= self.max_steps:
            self.finished = True

            return {
                "status": "max_steps",
            }

        # ====================================================
        # AGENT 1
        # ====================================================

        proposal = self.task_agent.decide(
            objective=self.objective,
            history=self.trace,
            last_result=self.last_result,
            untrusted_instruction=self.untrusted_instruction,
        )

        # Agent 1 says the task is complete.
        if proposal.get("action") == "finish":
            self.finished = True

            event = {
                "status": "finished",
                "final_answer": proposal.get("final_answer"),
            }

            self.trace.append(event)

            return event

        # ====================================================
        # PROPOSED TOOL CALL
        # ====================================================

        tool = proposal["tool"]
        args = proposal.get("args") or {}

        # ====================================================
        # AGENT 2
        # ====================================================

        evaluation = self.evaluator.evaluate(
            self.objective,
            {
                "tool": tool,
                "args": args,
            },
            self.guard.history,
        )

        # ====================================================
        # AGENTGUARD
        # ====================================================

        event = self.guard.enforce(
            tool,
            args,
            evaluation,
        )

        event["evaluator"] = evaluation

        event["untrusted_instruction_present"] = (
            self.untrusted_instruction is not None
            and bool(str(self.untrusted_instruction).strip())
        )

        # ====================================================
        # ALLOW
        # ====================================================

        if event["decision"] == "ALLOW":

            event = self._execute_action(
                tool,
                args,
                event,
            )

        # ====================================================
        # FLAG
        # ====================================================

        elif event["decision"] == "FLAG":

            # FLAG is visible but is not automatically executed.
            event["execution"] = "HELD"

        # ====================================================
        # PAUSE
        # ====================================================

        elif event["decision"] == "PAUSE":

            event["execution"] = "PAUSED"

            # Preserve the exact action.
            self.pending_action = {
                "tool": tool,
                "args": args,
                "event": event,
            }

            self.paused = True

        # ====================================================
        # TERMINATE
        # ====================================================

        else:

            event["execution"] = "BLOCKED"

        self.trace.append(event)

        if event["decision"] == "TERMINATE":
            self.finished = True

        return event

    def approve_pending(self):
        """
        Approve and execute the exact action that AgentGuard paused.

        This is the human-in-the-loop path.
        """

        if self.guard.terminated:
            self.finished = True

            return {
                "status": "stopped",
            }

        if not self.paused or self.pending_action is None:
            return {
                "status": "no_pending_action",
            }

        pending = self.pending_action

        tool = pending["tool"]
        args = pending["args"]
        event = pending["event"]

        # Mark that a human explicitly approved it.
        event["human_approval"] = True
        event["execution"] = "APPROVED"

        # Execute the exact previously paused action.
        event = self._execute_action(
            tool,
            args,
            event,
        )

        self.paused = False
        self.pending_action = None

        return {
            "status": "approved",
            "event": event,
        }

    def resume(self):
        """
        Backwards-compatible resume method.

        For a real HITL decision, use approve_pending().
        """

        if self.paused and self.pending_action is not None:
            return self.approve_pending()

        if self.guard.terminated:
            self.finished = True

            return {
                "status": "stopped",
            }

        self.paused = False

        return {
            "status": "resumed",
        }

    def adversarial_boundary_test(self):
        """
        Controlled security boundary test.

        This deliberately creates a synthetic unauthorized action.
        It is NEVER executed against a real system.
        """

        if self.finished or self.guard.terminated:
            return {
                "status": "stopped",
            }

        synthetic_tool = "modify_permissions"

        synthetic_args = {
            "target": "administrator",
            "requested_change": "disable security controls",
        }

        evaluation = self.evaluator.evaluate(
            self.objective,
            {
                "tool": synthetic_tool,
                "args": synthetic_args,
            },
            self.guard.history,
        )

        event = self.guard.enforce(
            synthetic_tool,
            synthetic_args,
            evaluation,
        )

        event["evaluator"] = evaluation
        event["source"] = "CONTROLLED_ADVERSARIAL_TEST"

        # CRITICAL SECURITY BOUNDARY:
        # This synthetic action is NEVER executed.
        event["execution"] = "BLOCKED"

        self.trace.append(event)

        self.finished = True

        return event