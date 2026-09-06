"""
Return Window Tracker — Streamlit UI.

A visually appealing front-end for the Strands `return_tracker_agent`. It reuses
the exact same agent core from agent.py (two deterministic @tools +
LLM drafting + typed structured output) — no logic is duplicated here; this file
only handles presentation.

Run locally:
    streamlit run app.py

Deploy publicly (free): Streamlit Community Cloud — see DEPLOYMENT.md.

Built With: Strands Agents SDK (on Amazon Bedrock).
All data shown is synthetic sample data.
"""

from __future__ import annotations

import json
import os

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Streamlit Community Cloud secrets -> environment bridge.
# On Streamlit Cloud you paste AWS credentials into the app's "Secrets" box
# (TOML). boto3 / Bedrock read credentials from environment variables, so we
# copy any recognized secrets into os.environ BEFORE importing the agent (which
# initializes the Bedrock client). Locally this is a no-op (st.secrets is empty).
# ---------------------------------------------------------------------------
_SECRET_KEYS = (
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_SESSION_TOKEN",
    "AWS_REGION",
    "AWS_DEFAULT_REGION",
    "AWS_BEARER_TOKEN_BEDROCK",
    "STRANDS_MODEL_ID",
)
try:
    for _k in _SECRET_KEYS:
        if _k in st.secrets and st.secrets[_k]:
            os.environ.setdefault(_k, str(st.secrets[_k]))
    # Keep AWS_REGION and AWS_DEFAULT_REGION in sync if only one was provided.
    if os.environ.get("AWS_REGION") and not os.environ.get("AWS_DEFAULT_REGION"):
        os.environ["AWS_DEFAULT_REGION"] = os.environ["AWS_REGION"]
    if os.environ.get("AWS_DEFAULT_REGION") and not os.environ.get("AWS_REGION"):
        os.environ["AWS_REGION"] = os.environ["AWS_DEFAULT_REGION"]
except Exception:
    # st.secrets raises if no secrets file exists (e.g. local dev) — safe to ignore.
    pass

from agent import (  # noqa: E402  (import after env is populated)
    AUTONOMY_AUTO,
    AUTONOMY_NEEDS_YOU,
    AUTONOMY_NONE,
    run_tracker,
)
from generate_sample_data import build_purchases  # noqa: E402

# ---------------------------------------------------------------------------
# Page config & lightweight styling
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Return Window Tracker",
    page_icon="🧾",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Status → colour + label used for badges throughout the UI.
STATUS_STYLE = {
    "SAFE": ("#1a7f37", "SAFE"),
    "ACT_SOON": ("#bf8700", "ACT SOON"),
    "EXPIRED": ("#cf222e", "EXPIRED"),
    "ALREADY_FLAGGED_FOR_RETURN": ("#8250df", "FLAGGED"),
}

st.markdown(
    """
    <style>
      .rwt-badge {
        display:inline-block; padding:2px 10px; border-radius:12px;
        color:#fff; font-size:0.75rem; font-weight:600; letter-spacing:.3px;
      }
      .rwt-card {
        border:1px solid rgba(128,128,128,.25); border-radius:14px;
        padding:16px 18px; margin-bottom:12px; background:rgba(128,128,128,.04);
      }
      .rwt-needs { border-left:6px solid #cf222e; }
      .rwt-auto  { border-left:6px solid #1a7f37; }
      .rwt-none  { border-left:6px solid #8c959f; }
      .rwt-item-title { font-size:1.05rem; font-weight:700; margin-bottom:2px; }
      .rwt-meta { color:#6e7781; font-size:0.85rem; margin-bottom:6px; }
      .rwt-reason { font-size:0.9rem; margin:4px 0 8px 0; }
    </style>
    """,
    unsafe_allow_html=True,
)


def badge(status: str) -> str:
    colour, label = STATUS_STYLE.get(status, ("#57606a", status))
    return f'<span class="rwt-badge" style="background:{colour}">{label}</span>'


def price_str(p) -> str:
    return f"${p:,.2f}" if isinstance(p, (int, float)) else "n/a"


def item_card(it: dict, css_class: str) -> None:
    """Render one purchase as a styled card with optional drafted message."""
    new_flag = " 🆕" if it.get("seen_before") is False else ""
    st.markdown(
        f"""
        <div class="rwt-card {css_class}">
          <div class="rwt-item-title">{it.get('item','')}{new_flag} &nbsp; {badge(it.get('status',''))}</div>
          <div class="rwt-meta">
            {it.get('store','')} · purchased {it.get('purchase_date','')} ·
            deadline <b>{it.get('deadline','')}</b> ·
            <b>{it.get('days_left','?')}</b> day(s) left · {price_str(it.get('price'))}
          </div>
          <div class="rwt-reason">↳ {it.get('escalation_reason','') or ''}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    draft = (it.get("draft_message") or "").strip()
    if draft:
        with st.expander("✉️  View drafted return request (copy & send)"):
            st.code(draft, language="text")


# ---------------------------------------------------------------------------
# Sidebar — inputs
# ---------------------------------------------------------------------------
st.sidebar.title("🧾 Return Window Tracker")
st.sidebar.caption("An Everyday Agent built with the **Strands Agents SDK** on Amazon Bedrock.")

st.sidebar.markdown("### 1. Purchases")
st.sidebar.write(
    "Edit the table on the main page, or start from realistic synthetic data."
)
if "purchases_df" not in st.session_state:
    st.session_state.purchases_df = pd.DataFrame(build_purchases())

if st.sidebar.button("↻ Load fresh sample data"):
    st.session_state.purchases_df = pd.DataFrame(build_purchases())
    st.session_state.pop("result", None)

st.sidebar.markdown("### 2. Model (optional)")
model_id = st.sidebar.text_input(
    "Model ID override",
    value=os.environ.get("STRANDS_MODEL_ID", ""),
    placeholder="global.anthropic.claude-sonnet-4-6",
    help="Leave blank to use the Strands default (Amazon Bedrock Claude Sonnet).",
)

st.sidebar.markdown("### 3. Run")
run_clicked = st.sidebar.button("🤖 Run the agent", type="primary", use_container_width=True)

st.sidebar.markdown("---")
st.sidebar.caption(
    "Credentials are read from the environment only (AWS creds / Bedrock). "
    "No secrets are stored in the app. All data shown is synthetic."
)

# ---------------------------------------------------------------------------
# Main — header + editable data
# ---------------------------------------------------------------------------
st.title("🧾 Return Window Tracker")
st.markdown(
    "Never lose money to a missed return window again. This agent tracks every "
    "purchase's deadline, **auto-drafts** the routine return requests, and only "
    "**surfaces the ones that need your decision** — running quietly in the "
    "background like a good Everyday Agent should."
)

with st.expander("📋 Purchases (editable)", expanded=not st.session_state.get("result")):
    edited = st.data_editor(
        st.session_state.purchases_df,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "price": st.column_config.NumberColumn("price", format="$%.2f"),
            "return_window_days": st.column_config.NumberColumn("return_window_days"),
        },
        key="editor",
    )
    st.session_state.purchases_df = edited

# ---------------------------------------------------------------------------
# Run the agent
# ---------------------------------------------------------------------------
if run_clicked:
    purchases = st.session_state.purchases_df.to_dict(orient="records")
    # Clean up rows / types coming out of the editor.
    cleaned = []
    for p in purchases:
        if not p.get("item"):
            continue
        p["return_window_days"] = int(p.get("return_window_days") or 0)
        try:
            p["price"] = float(p.get("price")) if p.get("price") not in (None, "") else None
        except (TypeError, ValueError):
            p["price"] = None
        p["reason_for_potential_return"] = p.get("reason_for_potential_return") or ""
        cleaned.append(p)

    with st.spinner("Agent is checking deadlines, deciding what needs you, and drafting messages…"):
        try:
            # state_path=None here so the hosted demo is stateless & repeatable.
            st.session_state.result = run_tracker(
                cleaned, model=model_id or None, state_path=None
            )
        except Exception as exc:  # noqa: BLE001
            st.session_state.result = None
            st.error(
                "The agent could not run. This usually means AWS Bedrock "
                f"credentials/model access aren't configured.\n\nDetails: {exc}"
            )

# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------
result = st.session_state.get("result")
if result:
    items = result.get("items", [])
    needs_you = [it for it in items if it.get("autonomy") == AUTONOMY_NEEDS_YOU]
    auto = [it for it in items if it.get("autonomy") == AUTONOMY_AUTO]
    none = [it for it in items if it.get("autonomy") == AUTONOMY_NONE]

    # Metric cards
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Purchases reviewed", len(items))
    c2.metric("⚠️ Need your decision", len(needs_you))
    c3.metric("✅ Auto-handled", len(auto))
    c4.metric("ℹ️ No action", len(none))

    st.markdown("### 🗒️ Daily digest")
    st.info(result.get("digest", "").strip() or "No digest produced.")

    left, right = st.columns(2)
    with left:
        st.markdown(f"### ⚠️ Needs you — {len(needs_you)} decision(s)")
        if not needs_you:
            st.success("Nothing needs you right now. The agent has it covered. ✅")
        for it in needs_you:
            item_card(it, "rwt-needs")

    with right:
        st.markdown(f"### ✅ Auto-handled — {len(auto)} draft(s) ready")
        if not auto:
            st.caption("No routine returns to auto-handle.")
        for it in auto:
            item_card(it, "rwt-auto")

    if none:
        st.markdown(f"### ℹ️ No action needed — {len(none)}")
        for it in none:
            item_card(it, "rwt-none")

    # Structured output + download
    st.markdown("### 🧩 Structured output (typed via Strands structured output)")
    st.json(result, expanded=False)
    st.download_button(
        "⬇️ Download result JSON",
        data=json.dumps(result, indent=2),
        file_name="return_window_result.json",
        mime="application/json",
    )
else:
    st.markdown(
        "> Click **🤖 Run the agent** in the sidebar to see the prioritized digest, "
        "the items that need your decision, and the auto-drafted return messages."
    )

st.markdown("---")
st.caption(
    "Built With: Strands Agents SDK · Amazon Bedrock · "
    "[Source on GitHub](https://github.com/MakendranG/return-window-tracker) · "
    "All data is synthetic sample data."
)
