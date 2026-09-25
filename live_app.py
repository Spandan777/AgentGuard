"""Streamlit UI for the AgentGuard dynamic multi-agent demonstration."""

import json
import time

import streamlit as st
from dotenv import load_dotenv

from live_demo import DynamicRun


load_dotenv()


st.set_page_config(
    page_title="AgentGuard Dynamic Runtime",
    page_icon="🛡️",
    layout="wide",
)


st.title("AgentGuard — Dynamic Agent Runtime")
st.caption(
    "Agent 1 chooses actions dynamically. Agent 2 evaluates them. "
    "AgentGuard independently enforces the final decision."
)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.header("Runtime Configuration")

    agent_provider = st.selectbox(
        "Agent 1 Provider",
        ["gemini", "groq"],
        index=0,
    )

    evaluator_provider = st.selectbox(
        "Agent 2 / Evaluator Provider",
        ["groq", "gemini"],
        index=0,
    )

    max_steps = st.slider(
        "Maximum autonomous steps",
        min_value=1,
        max_value=10,
        value=6,
    )

    st.divider()

    st.subheader("Trusted Objective")

    objective = st.text_area(
        "Objective",
        value=(
            "Find the current weather in Bhubaneswar "
            "and tell me whether I should carry an umbrella."
        ),
        height=100,
    )

    st.subheader("Optional Untrusted Instruction")

    untrusted_instruction = st.text_area(
        "External / untrusted context",
        value="",
        height=100,
        help=(
            "Used only for controlled prompt-injection / objective-drift "
            "experiments. It does not replace the trusted objective."
        ),
    )

    st.divider()

    start_button = st.button(
        "Start New Run",
        type="primary",
        use_container_width=True,
    )

    adversarial_button = st.button(
        "Run Adversarial Boundary Test",
        use_container_width=True,
    )

    st.divider()

    st.info(
        "All live APIs are bounded, public, and read-only. "
        "The adversarial test uses a synthetic unauthorized action "
        "and never executes it."
    )


# ============================================================
# SESSION STATE
# ============================================================

if "run" not in st.session_state:
    st.session_state.run = None

if "running" not in st.session_state:
    st.session_state.running = False

if "last_event" not in st.session_state:
    st.session_state.last_event = None


# ============================================================
# START NEW RUN
# ============================================================

if start_button:
    if not objective.strip():
        st.error("Please provide a trusted objective.")
        st.stop()

    st.session_state.run = DynamicRun(
        objective=objective.strip(),
        agent_provider=agent_provider,
        evaluator_provider=evaluator_provider,
        max_steps=max_steps,
        untrusted_instruction=(
            untrusted_instruction.strip()
            if untrusted_instruction.strip()
            else None
        ),
    )

    st.session_state.running = True
    st.session_state.last_event = None

    st.rerun()


# ============================================================
# ADVERSARIAL BOUNDARY TEST
# ============================================================

if adversarial_button:

    if not objective.strip():
        st.error("Please provide a trusted objective first.")
        st.stop()

    test_run = DynamicRun(
        objective=objective.strip(),
        agent_provider=agent_provider,
        evaluator_provider=evaluator_provider,
        max_steps=1,
    )

    with st.spinner("Running controlled adversarial boundary test..."):
        event = test_run.adversarial_boundary_test()

    st.session_state.last_event = event
    st.session_state.run = test_run
    st.session_state.running = False

    st.rerun()


# ============================================================
# NO ACTIVE RUN
# ============================================================

if st.session_state.run is None:

    st.markdown("## Ready")

    st.write(
        "Enter a trusted objective and start a dynamic run. "
        "Agent 1 will independently choose its next API call."
    )

    st.markdown(
        """
### Demonstration idea

**Trusted objective**

> Find the current weather in Bhubaneswar and tell me whether I should carry an umbrella.

Agent 1 may choose:

`weather`

AgentGuard should normally allow it.

If Agent 1 instead chooses something technically safe but unrelated, such as:

`currency`

Agent 2 should recognize that the action is not aligned with the original objective.

This is the key distinction:

**Technical safety ≠ Objective alignment**
"""
    )

    st.stop()


run = st.session_state.run


# ============================================================
# HEADER STATUS
# ============================================================

st.markdown("## Runtime Status")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Steps",
        len(run.trace),
    )

with col2:
    st.metric(
        "Max Steps",
        run.max_steps,
    )

with col3:
    if run.guard.terminated:
        st.error("TERMINATED")
    elif run.paused:
        st.warning("PAUSED")
    elif run.finished:
        st.success("FINISHED")
    else:
        st.info("RUNNING")

with col4:
    st.metric(
        "Events",
        len(run.trace),
    )


# ============================================================
# TRUSTED OBJECTIVE
# ============================================================

st.markdown("## Trusted Objective")

st.code(
    run.objective,
    language="text",
)


if run.untrusted_instruction:
    st.markdown("### Untrusted Instruction")

    st.warning(
        run.untrusted_instruction
    )


# ============================================================
# CONTROLLED ADVERSARIAL RESULT
# ============================================================

if (
    st.session_state.last_event
    and st.session_state.last_event.get("source")
    == "CONTROLLED_ADVERSARIAL_TEST"
):

    event = st.session_state.last_event

    st.markdown("## Controlled Adversarial Boundary Test")

    st.warning(
        "This is a synthetic unauthorized action. "
        "It was evaluated by AgentGuard but was never executed."
    )

    call_col, decision_col = st.columns(2)

    with call_col:
        st.markdown("### Synthetic Proposed Action")

        st.json(
            {
                "tool": event.get("tool"),
                "args": event.get("args"),
            }
        )

    with decision_col:
        st.markdown("### AgentGuard Decision")

        decision = event.get("decision", "UNKNOWN")

        if decision == "TERMINATE":
            st.error(decision)
        elif decision == "PAUSE":
            st.warning(decision)
        elif decision == "FLAG":
            st.warning(decision)
        else:
            st.success(decision)

        st.write(
            f"**Task authorized:** "
            f"{event.get('task_authorized')}"
        )

        st.write(
            f"**Policy:** "
            f"{event.get('policy')}"
        )

        st.write(
            f"**Technical safety:** "
            f"{event.get('technical_safety')}"
        )

        st.write(
            f"**Objective alignment:** "
            f"{event.get('objective_alignment')}"
        )

        st.write(
            f"**Trajectory risk:** "
            f"{event.get('trajectory_risk')}"
        )

    st.markdown("### Agent 2 Evaluation")

    evaluator = event.get("evaluator", {})

    st.json(evaluator)

    st.markdown("### Execution")

    st.error(
        "BLOCKED — synthetic action was never executed."
    )

    st.divider()


# ============================================================
# PAUSED STATE
# ============================================================

if run.paused:

    st.warning(
        "AgentGuard has PAUSED autonomous execution. "
        "Human approval is required before continuing."
    )

    if run.trace:
        pending = run.trace[-1]

        if pending.get("decision") == "PAUSE":

            st.markdown("### Paused Action")

            st.json(
                {
                    "tool": pending.get("tool"),
                    "args": pending.get("args"),
                }
            )

            st.markdown("### Why was it paused?")

            st.write(
                pending.get(
                    "reason",
                    "AgentGuard requested human review.",
                )
            )

            if st.button(
                "Approve and Resume",
                type="primary",
            ):
                run.resume()
                st.rerun()

    st.stop()


# ============================================================
# AUTONOMOUS EXECUTION
# ============================================================

if (
    st.session_state.running
    and not run.finished
    and not run.guard.terminated
    and not run.paused
):

    try:
        event = run.step()

        st.session_state.last_event = event

    except Exception as exc:

        st.session_state.running = False

        st.error(
            "Runtime error while executing the next agent cycle."
        )

        st.exception(exc)

        st.stop()

    # Stop automatic loop on pause/termination/finish.
    if (
        run.paused
        or run.guard.terminated
        or run.finished
        or event.get("status") in {
            "stopped",
            "max_steps",
            "finished",
        }
    ):
        st.session_state.running = False

    else:
        # Small delay makes the trajectory visually readable.
        time.sleep(0.4)
        st.rerun()


# ============================================================
# LATEST EVENT
# ============================================================

if run.trace:

    st.markdown("## Latest Runtime Event")

    event = run.trace[-1]

    if event.get("status") == "finished":

        st.success("Agent 1 finished the task.")

        st.markdown("### Final Answer")

        st.write(
            event.get(
                "final_answer",
                "No final answer returned.",
            )
        )

    elif event.get("status") == "max_steps":

        st.warning(
            "Maximum autonomous steps reached."
        )

    elif event.get("status") not in {
        "stopped",
        "paused",
        "max_steps",
    }:

        decision = event.get(
            "decision",
            "UNKNOWN",
        )

        if decision == "ALLOW":
            st.success("AgentGuard: ALLOW")

        elif decision == "FLAG":
            st.warning("AgentGuard: FLAG")

        elif decision == "PAUSE":
            st.warning("AgentGuard: PAUSE")

        elif decision == "TERMINATE":
            st.error("AgentGuard: TERMINATE")

        else:
            st.info(decision)

        left, right = st.columns(2)

        with left:

            st.markdown("### Proposed API Call")

            st.json(
                {
                    "tool": event.get("tool"),
                    "args": event.get("args"),
                }
            )

        with right:

            st.markdown("### Agent 2 Evaluation")

            st.json(
                event.get(
                    "evaluator",
                    {},
                )
            )

        st.markdown("### AgentGuard Enforcement")

        enforcement_data = {
            "task_authorized": event.get(
                "task_authorized"
            ),
            "policy": event.get(
                "policy"
            ),
            "technical_safety": event.get(
                "technical_safety"
            ),
            "objective_alignment": event.get(
                "objective_alignment"
            ),
            "alignment_label": event.get(
                "alignment_label"
            ),
            "trajectory_risk": event.get(
                "trajectory_risk"
            ),
            "decision": event.get(
                "decision"
            ),
            "execution": event.get(
                "execution"
            ),
            "reason": event.get(
                "reason"
            ),
        }

        st.json(enforcement_data)

        if event.get("api_result") is not None:

            st.markdown("### Real API Response")

            st.json(
                event.get("api_result")
            )

        if event.get("api_error"):

            st.error(
                f"API error: {event['api_error']}"
            )


# ============================================================
# COMPLETE TRAJECTORY
# ============================================================

st.markdown("## Runtime Trajectory")

for index, event in enumerate(run.trace):

    if event.get("status") == "finished":

        st.markdown(
            f"**Step {index + 1}: FINISHED**"
        )

        if event.get("final_answer"):
            st.write(
                event.get("final_answer")
            )

        continue

    if event.get("status") == "max_steps":

        st.markdown(
            f"**Step {index + 1}: MAX STEPS**"
        )

        continue

    if not event.get("tool"):
        continue

    decision = event.get(
        "decision",
        "UNKNOWN",
    )

    label = (
        f"Step {index + 1} — "
        f"`{event.get('tool')}` → **{decision}**"
    )

    with st.expander(label):

        st.json(
            {
                "tool": event.get("tool"),
                "args": event.get("args"),
                "decision": event.get("decision"),
                "technical_safety": event.get(
                    "technical_safety"
                ),
                "objective_alignment": event.get(
                    "objective_alignment"
                ),
                "alignment_label": event.get(
                    "alignment_label"
                ),
                "trajectory_risk": event.get(
                    "trajectory_risk"
                ),
                "task_authorized": event.get(
                    "task_authorized"
                ),
                "policy": event.get(
                    "policy"
                ),
                "execution": event.get(
                    "execution"
                ),
                "reason": event.get(
                    "reason"
                ),
            }
        )

        if event.get("api_result") is not None:

            st.markdown("**API Response**")

            st.json(
                event.get("api_result")
            )


# ============================================================
# MACHINE-READABLE TRACE
# ============================================================

st.markdown("## Machine-Readable Trace")

st.download_button(
    label="Export Runtime Trace",
    data=json.dumps(
        run.trace,
        indent=2,
        default=str,
    ),
    file_name="agentguard_runtime_trace.json",
    mime="application/json",
)


# ============================================================
# SECURITY NOTE
# ============================================================

st.divider()

st.caption(
    "Security boundary: AgentGuard only executes tools registered in "
    "the bounded live tool registry. The adversarial boundary test uses "
    "a synthetic unauthorized action and never executes it."
)