"""Large, readable Plotly visualizations for the AgentGuard simulator."""
import pandas as pd
import plotly.graph_objects as go


DECISION_COLORS = {
    "ALLOW": "#35d07f",
    "FLAG": "#f5b942",
    "PAUSE": "#ff8c42",
    "BLOCK": "#ff5c5c",
    "TERMINATE": "#ff3b5c",
}

LEVEL_COLORS = {
    "LOW": "#35d07f",
    "MEDIUM": "#f5b942",
    "HIGH": "#ff8c42",
    "CRITICAL": "#ff3b5c",
}


def actions_to_dataframe(actions):
    df = pd.DataFrame(actions, columns=[
        "timestamp", "tool", "args", "risk_score", "risk_level",
        "policy_decision", "final_decision", "reason"
    ])
    if df.empty:
        df["step"] = pd.Series(dtype=int)
        return df
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["step"] = range(1, len(df) + 1)
    return df


def build_risk_chart(actions):
    df = actions_to_dataframe(actions)
    fig = go.Figure()
    if df.empty:
        return fig

    fig.add_trace(go.Scatter(
        x=df["step"], y=df["risk_score"],
        mode="lines+markers",
        line=dict(color="#54b8ff", width=4),
        marker=dict(size=10, color=[LEVEL_COLORS.get(x, "#54b8ff") for x in df["risk_level"]]),
        hovertemplate="Step %{x}<br>Risk: %{y}<extra></extra>",
        name="Risk"
    ))
    for y, label, color in [(30, "LOW", "#35d07f"), (60, "MEDIUM", "#f5b942"), (80, "HIGH", "#ff8c42")]:
        fig.add_hline(y=y, line_dash="dot", line_color=color, opacity=0.65,
                      annotation_text=label, annotation_position="top left")
    fig.add_hline(y=100, line_dash="dot", line_color="#ff3b5c", opacity=0.5,
                  annotation_text="CRITICAL", annotation_position="top left")
    fig.update_yaxes(range=[0, 105], title="Risk score")
    fig.update_xaxes(dtick=1, title="Agent action")
    fig.update_layout(
        height=390, margin=dict(l=50, r=25, t=25, b=45),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#d9e2ec"),
        showlegend=False,
    )
    return fig


def build_trajectory_graph(actions):
    """Create a large horizontal trajectory diagram with Plotly."""
    df = actions_to_dataframe(actions)
    fig = go.Figure()
    if df.empty:
        return fig

    n = len(df)
    xs = list(range(n))
    ys = [0] * n

    # Connecting arrows/lines.
    for i in range(n - 1):
        fig.add_trace(go.Scatter(
            x=[xs[i], xs[i + 1]], y=[0, 0],
            mode="lines", line=dict(color="#526173", width=3),
            hoverinfo="skip", showlegend=False
        ))

    colors = [DECISION_COLORS.get(d, "#54b8ff") for d in df["final_decision"]]
    labels = [f"{i+1}. {tool}" for i, tool in enumerate(df["tool"])]
    hover = [
        f"Step {i+1}<br>Tool: {row.tool}<br>Risk: {row.risk_score}/100<br>Level: {row.risk_level}<br>Decision: {row.final_decision}"
        for i, row in df.iterrows()
    ]

    fig.add_trace(go.Scatter(
        x=xs, y=ys, mode="markers+text",
        marker=dict(size=46, color=colors, line=dict(color="#dce6f2", width=2)),
        text=labels, textposition="bottom center",
        textfont=dict(size=12, color="#e8eef5"),
        hovertext=hover, hoverinfo="text", showlegend=False
    ))

    fig.update_xaxes(showgrid=False, zeroline=False, showticklabels=False, range=[-0.6, max(n - 0.4, 0.6)])
    fig.update_yaxes(showgrid=False, zeroline=False, showticklabels=False, range=[-0.9, 0.9])
    fig.update_layout(
        height=350, margin=dict(l=30, r=30, t=25, b=90),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#d9e2ec"),
    )
    return fig
