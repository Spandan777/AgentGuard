import time
import uuid
import pandas as pd
import streamlit as st

from agent import plan_normal_task, malicious_injection_plan, privilege_escalation_plan
from tools import TOOL_REGISTRY
from policy import check_policy
from risk import score_action, escalation_decision
from logger import init_db, log_action, get_all_runs, get_run_actions
from features import compute_features
from anomaly import detect_anomaly
from visuals import actions_to_dataframe, build_risk_chart, build_trajectory_graph

init_db()

st.set_page_config(
    page_title="AgentGuard | Runtime AI Security",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------
# Styling
# -----------------------------
st.markdown("""
<style>
:root { --bg:#07111f; --panel:#0d1a2b; --panel2:#101f33; --line:#1e3148; --text:#e8eef5; --muted:#8fa3b8; --cyan:#54b8ff; --green:#35d07f; --amber:#f5b942; --orange:#ff8c42; --red:#ff3b5c; }
.stApp { background: radial-gradient(circle at 70% 0%, #10243a 0%, #07111f 45%, #050b13 100%); color:var(--text); }
[data-testid="stHeader"] { background:rgba(0,0,0,0); }
[data-testid="stSidebar"] { background:#081423; border-right:1px solid var(--line); }
[data-testid="stSidebar"] * { color:#cdd9e6; }
.main .block-container { max-width:1500px; padding:1.5rem 2.5rem 3rem; }
.hero { display:flex; justify-content:space-between; align-items:center; padding:8px 0 20px; }
.brand { font-size:2rem; font-weight:800; letter-spacing:-0.04em; }
.subtitle { color:var(--muted); margin-top:2px; font-size:.92rem; }
.status { padding:8px 14px; border-radius:999px; border:1px solid rgba(53,208,127,.35); background:rgba(53,208,127,.09); color:#69e39b; font-weight:700; font-size:.8rem; }
.panel { background:rgba(13,26,43,.88); border:1px solid var(--line); border-radius:16px; padding:18px; box-shadow:0 10px 35px rgba(0,0,0,.18); }
.panel-title { color:#f2f6fa; font-weight:750; font-size:1rem; margin-bottom:12px; }
.kpi { background:rgba(16,31,51,.88); border:1px solid var(--line); border-radius:14px; padding:15px 18px; min-height:104px; }
.kpi-label { color:var(--muted); font-size:.76rem; text-transform:uppercase; letter-spacing:.08em; }
.kpi-value { color:#f2f6fa; font-size:1.65rem; font-weight:800; margin-top:8px; }
.kpi-sub { color:#91a5ba; font-size:.75rem; margin-top:3px; }
.event { background:#0b1726; border:1px solid #1b2d42; border-radius:11px; padding:11px 13px; margin:7px 0; }
.event-line { display:flex; justify-content:space-between; gap:15px; align-items:center; }
.event-tool { font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-weight:700; color:#e8eef5; }
.muted { color:var(--muted); font-size:.78rem; }
.pill { display:inline-block; border-radius:999px; padding:4px 9px; font-size:.68rem; font-weight:800; letter-spacing:.05em; }
.allow { background:rgba(53,208,127,.12); color:#69e39b; border:1px solid rgba(53,208,127,.35); }
.flag { background:rgba(245,185,66,.12); color:#f5c967; border:1px solid rgba(245,185,66,.35); }
.pause { background:rgba(255,140,66,.12); color:#ffad78; border:1px solid rgba(255,140,66,.35); }
.terminate { background:rgba(255,59,92,.12); color:#ff6d87; border:1px solid rgba(255,59,92,.35); }
.incident { border:1px solid rgba(255,59,92,.55); background:linear-gradient(135deg,rgba(255,59,92,.12),rgba(13,26,43,.9)); border-radius:16px; padding:22px; }
.incident-title { color:#ff6d87; font-size:1.35rem; font-weight:850; }
.command { font-family:ui-monospace,SFMono-Regular,Menlo,monospace; color:#bfe5ff; background:#06101c; border:1px solid #18304a; border-radius:10px; padding:12px; }
.small-note { color:#8fa3b8; font-size:.78rem; line-height:1.45; }
</style>
""", unsafe_allow_html=True)

# -----------------------------
# Session state
# -----------------------------
def reset_session():
    st.session_state.run_id = None
    st.session_state.plan = []
    st.session_state.step_index = 0
    st.session_state.history = []
    st.session_state.executed = []
    st.session_state.status = "READY"
    st.session_state.injected = False
    st.session_state.attack_type = None
    st.session_state.terminated = False
    st.session_state.paused = False
    st.session_state.max_risk = 0
    st.session_state.last_reason = ""
    st.session_state.last_decision = ""
    st.session_state.last_action = ""
    st.session_state.pending_step = None
    st.session_state.pending_evaluation = None


if "run_id" not in st.session_state:
    reset_session()

# -----------------------------
# Sidebar
# -----------------------------
with st.sidebar:
    st.markdown("## 🛡️ AgentGuard")
    st.caption("Runtime AI-agent security sandbox")
    page = st.radio("Navigate", ["Agent Simulator", "Threat Detection", "Policies", "Analytics"], label_visibility="collapsed")
    st.divider()
    st.markdown("**Escalation policy**")
    st.markdown("🟢 **LOW** · 0–30 · Allow")
    st.markdown("🟡 **MEDIUM** · 31–60 · Flag")
    st.markdown("🟠 **HIGH** · 61–80 · Pause")
    st.markdown("🔴 **CRITICAL** · 81–100 · Terminate")
    st.divider()
    st.caption("All tools are simulated. No real files, credentials, email or external servers are accessed.")
    st.markdown("**Attack classes**")
    st.caption("Prompt injection · privilege escalation")

# -----------------------------
# Helpers
# -----------------------------
def current_actions():
    if not st.session_state.run_id:
        return []
    return get_run_actions(st.session_state.run_id)


def status_html(decision):
    cls = {"ALLOW":"allow", "ALLOW_ONCE":"allow", "FLAG":"flag", "PAUSE":"pause", "BLOCK":"terminate", "TERMINATE":"terminate"}.get(decision, "flag")
    return f'<span class="pill {cls}">{decision}</span>'


def _record_executed(step, tool_name, args, risk_score, risk_level, policy_decision, decision, policy_reason, risk_reason, result):
    """Persist one completed/approved action in the live trajectory."""
    log_action(
        st.session_state.run_id, tool_name, args, risk_score, risk_level,
        policy_decision, decision, risk_reason
    )
    st.session_state.history.append({"tool": tool_name, "decision": decision})
    st.session_state.executed.append({
        "step": step,
        "tool": tool_name,
        "args": args,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "policy_decision": policy_decision,
        "policy_reason": policy_reason,
        "decision": decision,
        "reason": risk_reason,
        "result": result,
    })
    st.session_state.max_risk = max(st.session_state.max_risk, risk_score)
    st.session_state.last_reason = risk_reason
    st.session_state.last_decision = decision
    st.session_state.last_action = tool_name


def execute_next():
    if st.session_state.status in ("TERMINATED", "COMPLETE", "PAUSED"):
        return
    if not st.session_state.plan:
        return

    if st.session_state.run_id is None:
        st.session_state.run_id = str(uuid.uuid4())[:8]

    if st.session_state.step_index >= len(st.session_state.plan):
        st.session_state.status = "COMPLETE"
        return

    step = st.session_state.plan[st.session_state.step_index]
    tool_name, args = step["tool"], step["args"]
    policy_decision, policy_reason = check_policy(tool_name, args)
    risk_score, risk_level, risk_reason = score_action(
        tool_name, args, policy_decision, st.session_state.history
    )
    decision = escalation_decision(risk_score, policy_decision)
    step_number = st.session_state.step_index + 1

    # HIGH risk is a genuine human-in-the-loop checkpoint. The action is not
    # executed, logged, or advanced until the reviewer explicitly approves it.
    if decision == "PAUSE":
        st.session_state.status = "PAUSED"
        st.session_state.paused = True
        st.session_state.pending_step = step
        st.session_state.pending_evaluation = {
            "step": step_number,
            "tool": tool_name,
            "args": args,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "policy_decision": policy_decision,
            "policy_reason": policy_reason,
            "reason": risk_reason,
        }
        st.session_state.max_risk = max(st.session_state.max_risk, risk_score)
        st.session_state.last_reason = risk_reason
        st.session_state.last_decision = "PAUSE"
        st.session_state.last_action = tool_name
        return

    if decision == "ALLOW":
        result = TOOL_REGISTRY[tool_name](**args)["result"]
        st.session_state.status = "RUNNING"
    elif decision == "FLAG":
        result = "Action observed and flagged for monitoring."
        st.session_state.status = "RUNNING"
    else:
        result = "Execution terminated. Tool was not executed."
        st.session_state.status = "TERMINATED"
        st.session_state.terminated = True

    _record_executed(
        step_number, tool_name, args, risk_score, risk_level,
        policy_decision, decision, policy_reason, risk_reason, result
    )
    st.session_state.step_index += 1

    if decision == "TERMINATE":
        return
    if st.session_state.step_index >= len(st.session_state.plan):
        st.session_state.status = "COMPLETE"


def approve_pending_action():
    """Human override for a paused HIGH-risk action."""
    pending = st.session_state.pending_evaluation
    if not pending or st.session_state.status != "PAUSED":
        return

    tool_name = pending["tool"]
    args = pending["args"]
    result = TOOL_REGISTRY[tool_name](**args)["result"]

    _record_executed(
        pending["step"], tool_name, args, pending["risk_score"], pending["risk_level"],
        pending["policy_decision"], "ALLOW_ONCE", pending["policy_reason"],
        pending["reason"], result
    )
    st.session_state.step_index += 1
    st.session_state.pending_step = None
    st.session_state.pending_evaluation = None
    st.session_state.paused = False
    st.session_state.status = "RUNNING"

    if st.session_state.step_index >= len(st.session_state.plan):
        st.session_state.status = "COMPLETE"


def start_attack(attack_type: str):
    if st.session_state.status in ("TERMINATED", "COMPLETE", "PAUSED"):
        return
    if not st.session_state.run_id:
        st.session_state.run_id = str(uuid.uuid4())[:8]

    attack_plan = malicious_injection_plan() if attack_type == "prompt_injection" else privilege_escalation_plan()

    # Always demonstrate the attack as a trajectory: preserve the first two
    # benign actions when the attack is introduced before execution begins.
    if st.session_state.step_index < 2:
        task = st.session_state.get("task_input", "Find my project report and send it to my professor")
        safe_prefix = plan_normal_task(task)[:2]
        st.session_state.plan = safe_prefix + attack_plan
    else:
        st.session_state.plan = st.session_state.plan[:st.session_state.step_index] + attack_plan

    st.session_state.injected = True
    st.session_state.attack_type = attack_type
    st.session_state.paused = False
    st.session_state.pending_step = None
    st.session_state.pending_evaluation = None
    st.session_state.status = "RUNNING"

def inject_attack():
    start_attack("prompt_injection")

def inject_privilege_attack():
    start_attack("privilege_escalation")

# -----------------------------
# Header
# -----------------------------
st.markdown('''<div class="hero"><div><div class="brand">◈ AgentGuard</div><div class="subtitle">Runtime security & behavioural monitoring for tool-using AI agents</div></div><div class="status">● SANDBOX PROTECTED</div></div>''', unsafe_allow_html=True)

# -----------------------------
# Agent Simulator
# -----------------------------
if page == "Agent Simulator":
    c1, c2 = st.columns([2.2, 1])
    with c1:
        task = st.text_input("USER TASK", value="Find my project report and send it to my professor", key="task_input")
    with c2:
        scenario = st.selectbox("STARTING SCENARIO", ["Normal task", "Prompt injection", "Privilege escalation"], index=0)

    if st.session_state.status == "READY":
        if scenario == "Normal task":
            st.session_state.plan = plan_normal_task(task)
        elif scenario == "Prompt injection":
            st.session_state.plan = plan_normal_task(task)[:2] + malicious_injection_plan()
            st.session_state.attack_type = "prompt_injection"
        else:
            st.session_state.plan = plan_normal_task(task)[:2] + privilege_escalation_plan()
            st.session_state.attack_type = "privilege_escalation"

    b1, b2, b3, b4 = st.columns([1.25, 1.15, 1.15, 1.0])
    with b1:
        if st.button("▶ START / NEXT ACTION", type="primary", use_container_width=True, disabled=st.session_state.status in ("TERMINATED", "COMPLETE")):
            execute_next()
            st.rerun()
    with b2:
        if st.button("⚡ RUN TO END", use_container_width=True, disabled=st.session_state.status in ("TERMINATED", "COMPLETE")):
            while st.session_state.status not in ("TERMINATED", "COMPLETE", "PAUSED"):
                execute_next()
            st.rerun()
    with b3:
        if st.button("↺ RESET", use_container_width=True):
            reset_session()
            st.rerun()
    with b4:
        st.markdown('<div class="small-note" style="padding-top:9px;text-align:right">All attacks are simulated</div>', unsafe_allow_html=True)

    a1, a2 = st.columns(2)
    with a1:
        if st.button("☠ SIMULATE PROMPT INJECTION", use_container_width=True, disabled=st.session_state.status in ("TERMINATED", "COMPLETE")):
            inject_attack()
            st.rerun()
    with a2:
        if st.button("⚠ SIMULATE PRIVILEGE ESCALATION", use_container_width=True, disabled=st.session_state.status in ("TERMINATED", "COMPLETE")):
            inject_privilege_attack()
            st.rerun()

    if st.session_state.status == "PAUSED":
        pending = st.session_state.pending_evaluation or {}
        st.warning("AgentGuard paused execution before a HIGH-risk action. Human approval is required.")
        if pending:
            p1, p2, p3 = st.columns(3)
            p1.metric("Pending action", pending.get("tool", "—"))
            p2.metric("Risk", f"{pending.get('risk_score', 0)}/100")
            p3.metric("Response", "PAUSE")
            st.markdown(
                f'<div class="event"><div class="event-line"><span class="event-tool">Step {pending.get("step", "—")}: {pending.get("tool", "—")}</span>{status_html("PAUSE")}</div><div class="muted">Risk {pending.get("risk_score", 0)}/100 · {pending.get("risk_level", "HIGH")} · Policy {pending.get("policy_decision", "—")}</div><div class="muted">{pending.get("reason", "")}</div></div>',
                unsafe_allow_html=True,
            )
        r1, r2 = st.columns([1, 4])
        with r1:
            if st.button("✓ APPROVE ONCE", type="primary", use_container_width=True):
                approve_pending_action()
                st.rerun()
        with r2:
            st.caption("Approval executes only this paused action. The next action is evaluated again from scratch, preserving the full trajectory.")

    if st.session_state.injected:
        if st.session_state.attack_type == "privilege_escalation":
            title = "⚠ Privilege escalation attempt introduced"
            desc = "The simulated agent is attempting to obtain unauthorized privileges and modify access controls. AgentGuard evaluates the sequence before privileged actions are executed."
            command = "request admin access → access admin panel → modify permissions"
        else:
            title = "⚠ Prompt injection introduced"
            desc = "The simulated agent has been exposed to an instruction that attempts to move outside its original task scope. AgentGuard will evaluate the resulting action trajectory."
            command = "Ignore the original task → search credentials → contact external service → upload sensitive data"
        st.markdown(f'<div class="incident"><div class="incident-title">{title}</div><div class="small-note">{desc}</div><div class="command">{command}</div></div>', unsafe_allow_html=True)

    # KPIs
    status = st.session_state.status
    status_label = "● RUNNING" if status == "RUNNING" else status
    k1, k2, k3, k4, k5 = st.columns(5)
    for col, label, value, sub in [
        (k1, "AGENT STATUS", status_label, "sandbox state"),
        (k2, "CURRENT RISK", f"{st.session_state.max_risk}/100", "peak trajectory risk"),
        (k3, "ACTIONS", str(len(st.session_state.executed)), "observed steps"),
        (k4, "BLOCKED", str(sum(1 for x in st.session_state.executed if x["decision"] in ("TERMINATE", "BLOCK"))), "prevented actions"),
        (k5, "ESCALATION", st.session_state.last_decision or "—", "latest response"),
    ]:
        col.markdown(f'<div class="kpi"><div class="kpi-label">{label}</div><div class="kpi-value">{value}</div><div class="kpi-sub">{sub}</div></div>', unsafe_allow_html=True)

    st.write("")

    actions = current_actions()
    df = actions_to_dataframe(actions)

    # Large risk chart
    st.markdown('<div class="panel"><div class="panel-title">Risk Escalation Timeline</div>', unsafe_allow_html=True)
    st.plotly_chart(build_risk_chart(actions), use_container_width=True, config={"displayModeBar": False})
    st.markdown('</div>', unsafe_allow_html=True)

    st.write("")

    # Large trajectory graph
    st.markdown('<div class="panel"><div class="panel-title">Live Agent Trajectory</div>', unsafe_allow_html=True)
    if actions:
        st.plotly_chart(build_trajectory_graph(actions), use_container_width=True, config={"displayModeBar": False})
    else:
        st.info("Start the agent to build the live trajectory graph.")
    st.markdown('</div>', unsafe_allow_html=True)

    st.write("")

    left, right = st.columns([1.55, 1])
    with left:
        st.markdown('<div class="panel"><div class="panel-title">Live Security Events</div>', unsafe_allow_html=True)
        if st.session_state.executed:
            for event in reversed(st.session_state.executed):
                st.markdown(f'''<div class="event"><div class="event-line"><span class="event-tool">{event["step"]}. {event["tool"]}</span>{status_html(event["decision"])}</div><div class="muted">Risk {event["risk_score"]}/100 · {event["risk_level"]} · Policy {event["policy_decision"]}</div><div class="muted">{event["reason"]}</div></div>''', unsafe_allow_html=True)
        else:
            st.caption("No actions observed yet.")
        st.markdown('</div>', unsafe_allow_html=True)

    with right:
        st.markdown('<div class="panel"><div class="panel-title">Current Security Decision</div>', unsafe_allow_html=True)
        if status == "TERMINATED":
            st.markdown('<div class="incident"><div class="incident-title">🔴 THREAT CONTAINED</div><div class="small-note">Agent execution has been terminated before the critical tool could run.</div></div>', unsafe_allow_html=True)
        elif status == "PAUSED":
            st.warning("HIGH RISK ACTION — execution paused for approval.")
        elif status == "COMPLETE":
            st.success("Task completed within the configured policy.")
        elif st.session_state.executed:
            st.info(f"Latest action: {st.session_state.last_action} · {st.session_state.last_decision}")
        else:
            st.info("AgentGuard is waiting for the first action.")
        if st.session_state.last_reason:
            st.markdown(f'<div class="small-note"><b>Reason</b><br>{st.session_state.last_reason}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # Decision history
    if not df.empty:
        st.write("")
        st.markdown('<div class="panel"><div class="panel-title">Decision History</div>', unsafe_allow_html=True)
        display = df[["step", "tool", "risk_score", "risk_level", "policy_decision", "final_decision"]].copy()
        display.columns = ["Step", "Tool", "Risk", "Level", "Policy", "Decision"]
        st.dataframe(display, use_container_width=True, hide_index=True)
        st.markdown('</div>', unsafe_allow_html=True)

# -----------------------------
# Threat Detection
# -----------------------------
elif page == "Threat Detection":
    st.title("Threat Detection")
    st.caption("Trajectory-level behavioural analysis using the existing feature pipeline and Isolation Forest.")
    run_ids = get_all_runs()
    if not run_ids:
        st.info("Run a few simulations first. The anomaly detector becomes meaningful after at least five historical trajectories.")
    else:
        all_features = [compute_features(get_run_actions(rid)) for rid in run_ids]
        target = get_run_actions(run_ids[-1])
        target_features = compute_features(target)
        is_anomaly, anomaly_score = detect_anomaly(all_features, target_features)
        a, b, c = st.columns(3)
        a.metric("Historical runs", len(run_ids))
        b.metric("Latest anomaly score", f"{anomaly_score:.3f}")
        c.metric("Behaviour status", "ANOMALOUS" if is_anomaly else "CONSISTENT")
        st.plotly_chart(build_risk_chart(target), use_container_width=True, config={"displayModeBar": False})

# -----------------------------
# Policies
# -----------------------------
elif page == "Policies":
    st.title("Security Policies")
    st.caption("Explainable tool-level controls used by the runtime guard.")
    from policy import POLICY_RULES
    rows = []
    for tool, decision in POLICY_RULES.items():
        rows.append({"Tool": tool, "Policy": decision, "Escalation": "Blocked by default" if decision == "DENY" else "Allowed subject to risk"})
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    st.info("Policy decisions are combined with trajectory risk. A high-risk sequence can pause execution even before a hard policy violation occurs.")

# -----------------------------
# Analytics
# -----------------------------
elif page == "Analytics":
    st.title("Security Analytics")
    st.caption("Historical trajectory metrics from the local SQLite experiment log.")
    run_ids = get_all_runs()
    if not run_ids:
        st.info("No historical runs yet.")
    else:
        rows = []
        for rid in run_ids:
            acts = get_run_actions(rid)
            if acts:
                rows.append({
                    "run": rid,
                    "actions": len(acts),
                    "peak_risk": max(a[3] for a in acts),
                    "blocked": sum(1 for a in acts if a[6] in ("PAUSE", "TERMINATE", "BLOCK")),
                })
        hist = pd.DataFrame(rows)
        a, b, c = st.columns(3)
        a.metric("Total runs", len(hist))
        b.metric("Average peak risk", f"{hist.peak_risk.mean():.1f}")
        c.metric("Blocked actions", int(hist.blocked.sum()))
        st.line_chart(hist.set_index("run")["peak_risk"], height=360)
        st.dataframe(hist, use_container_width=True, hide_index=True)
