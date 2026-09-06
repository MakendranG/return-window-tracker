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
    run_tracker_offline,
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

# Status → colour + label used for pills throughout the UI.
STATUS_STYLE = {
    "SAFE": ("#1a7f37", "#e7f6ec", "SAFE"),
    "ACT_SOON": ("#bf8700", "#fff5e0", "ACT SOON"),
    "EXPIRED": ("#cf222e", "#fdecec", "EXPIRED"),
    "ALREADY_FLAGGED_FOR_RETURN": ("#8250df", "#f3edfc", "FLAGGED"),
}

st.markdown(
    """
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

      html, body, [class*="css"] { font-family: 'Inter', -apple-system, sans-serif; }

      /* Hide default Streamlit chrome for a cleaner app feel */
      #MainMenu, footer, header [data-testid="stToolbar"] { visibility: hidden; }
      .block-container { padding-top: 1.4rem; max-width: 1200px; }

      /* ---- Hero banner ---- */
      .rwt-hero {
        background: linear-gradient(135deg, #cf222e 0%, #7d1620 100%);
        border-radius: 20px; padding: 30px 34px; color: #fff;
        box-shadow: 0 12px 34px rgba(207,34,46,.28); margin-bottom: 8px;
      }
      .rwt-hero h1 { margin: 0 0 6px 0; font-size: 2.05rem; font-weight: 800; letter-spacing:-.5px; }
      .rwt-hero p  { margin: 0; font-size: 1.02rem; opacity: .95; line-height: 1.5; max-width: 760px; }
      .rwt-hero .rwt-pills { margin-top: 14px; }
      .rwt-hero .rwt-pill {
        display:inline-block; background: rgba(255,255,255,.16); border:1px solid rgba(255,255,255,.28);
        color:#fff; padding:4px 12px; border-radius:999px; font-size:.78rem; font-weight:600;
        margin-right:8px; margin-top:6px; backdrop-filter: blur(4px);
      }

      /* ---- Metric tiles ---- */
      .rwt-tiles { display:flex; gap:14px; flex-wrap:wrap; margin: 18px 0 6px 0; }
      .rwt-tile {
        flex:1; min-width:160px; border-radius:16px; padding:18px 20px;
        background:#fff; border:1px solid #eaecef; box-shadow:0 4px 14px rgba(31,35,40,.06);
      }
      .rwt-tile .num { font-size:2.1rem; font-weight:800; line-height:1; }
      .rwt-tile .lbl { font-size:.82rem; color:#6e7781; margin-top:6px; font-weight:600; text-transform:uppercase; letter-spacing:.4px; }
      .rwt-tile.t-review { border-top:4px solid #0969da; }
      .rwt-tile.t-needs  { border-top:4px solid #cf222e; }
      .rwt-tile.t-auto   { border-top:4px solid #1a7f37; }
      .rwt-tile.t-none   { border-top:4px solid #8c959f; }

      /* ---- Section headers ---- */
      .rwt-h { font-size:1.15rem; font-weight:800; margin:22px 0 10px 0; padding-bottom:6px;
               border-bottom:2px solid #f0f1f3; }

      /* ---- Item cards ---- */
      .rwt-card {
        border:1px solid #eaecef; border-radius:16px; padding:16px 18px; margin-bottom:14px;
        background:#fff; box-shadow:0 3px 12px rgba(31,35,40,.05); transition:transform .12s ease, box-shadow .12s ease;
      }
      .rwt-card:hover { transform:translateY(-2px); box-shadow:0 8px 22px rgba(31,35,40,.10); }
      .rwt-needs { border-left:6px solid #cf222e; }
      .rwt-auto  { border-left:6px solid #1a7f37; }
      .rwt-none  { border-left:6px solid #8c959f; }
      .rwt-item-title { font-size:1.06rem; font-weight:700; margin-bottom:4px; color:#1f2328; }
      .rwt-meta { color:#6e7781; font-size:0.85rem; margin-bottom:8px; }
      .rwt-meta b { color:#1f2328; }
      .rwt-reason { font-size:0.92rem; margin:6px 0 2px 0; color:#3d444d;
                    background:#f6f8fa; border-radius:8px; padding:8px 10px; }
      .rwt-badge {
        display:inline-block; padding:2px 11px; border-radius:999px; font-size:0.72rem;
        font-weight:700; letter-spacing:.4px; margin-left:6px; vertical-align:middle;
      }
      .rwt-new { background:#0969da; color:#fff; padding:1px 8px; border-radius:999px;
                 font-size:.68rem; font-weight:700; margin-left:6px; }
    </style>
    """,
    unsafe_allow_html=True,
)


def badge(status: str) -> str:
    fg, bg, label = STATUS_STYLE.get(status, ("#57606a", "#eef0f2", status))
    return f'<span class="rwt-badge" style="background:{bg};color:{fg}">{label}</span>'


def price_str(p) -> str:
    return f"${p:,.2f}" if isinstance(p, (int, float)) else "n/a"


def item_card(it: dict, css_class: str) -> None:
    """Render one purchase as a styled card with optional drafted message."""
    new_flag = '<span class="rwt-new">NEW</span>' if it.get("seen_before") is False else ""
    st.markdown(
        f"""
        <div class="rwt-card {css_class}">
          <div class="rwt-item-title">{it.get('item','')} {badge(it.get('status',''))}{new_flag}</div>
          <div class="rwt-meta">
            🏬 {it.get('store','')} &nbsp;·&nbsp; 🧾 purchased {it.get('purchase_date','')} &nbsp;·&nbsp;
            ⏰ deadline <b>{it.get('deadline','')}</b> &nbsp;·&nbsp;
            <b>{it.get('days_left','?')}</b> day(s) left &nbsp;·&nbsp; 💵 {price_str(it.get('price'))}
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


def tiles(review: int, needs: int, auto: int, none: int) -> None:
    """Render the four metric tiles as one styled HTML row."""
    st.markdown(
        f"""
        <div class="rwt-tiles">
          <div class="rwt-tile t-review"><div class="num">{review}</div><div class="lbl">Reviewed</div></div>
          <div class="rwt-tile t-needs"><div class="num" style="color:#cf222e">{needs}</div><div class="lbl">Need your decision</div></div>
          <div class="rwt-tile t-auto"><div class="num" style="color:#1a7f37">{auto}</div><div class="lbl">Auto-handled</div></div>
          <div class="rwt-tile t-none"><div class="num" style="color:#57606a">{none}</div><div class="lbl">No action</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


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

st.sidebar.markdown("### 2. Mode")

# Detect whether a shared/deployer Bedrock key is already available in the env.
_shared_creds = bool(
    os.environ.get("AWS_ACCESS_KEY_ID") or os.environ.get("AWS_BEARER_TOKEN_BEDROCK")
)

mode = st.sidebar.radio(
    "How should the agent run?",
    options=["Offline preview (no AWS needed)", "Live — Amazon Bedrock"],
    index=1 if _shared_creds else 0,
    help=(
        "Offline runs the full deterministic pipeline (deadline math + "
        "auto-handled vs needs-you decisions) with template-written messages — "
        "no credentials, no login. Live uses Amazon Bedrock to AI-draft the "
        "return messages and digest."
    ),
)
use_offline = mode.startswith("Offline")

model_id = ""
byo_creds: dict[str, str] = {}
if not use_offline:
    model_id = st.sidebar.text_input(
        "Model ID override (optional)",
        value=os.environ.get("STRANDS_MODEL_ID", ""),
        placeholder="global.anthropic.claude-sonnet-4-6",
        help="Leave blank to use the Strands default (Amazon Bedrock Claude Sonnet).",
    )
    with st.sidebar.expander("🔑 Enter your AWS credentials (not stored)", expanded=not _shared_creds):
        st.caption(
            "Paste **short-lived STS session credentials** — from your AWS SSO / "
            "IAM Identity Center 'command line access' screen, or `aws sts "
            "assume-role`. (`get-session-token` fails on temporary/CloudShell "
            "creds.) These are held only in memory for this single run, are "
            "**never written to disk or the environment**, and are cleared when "
            "you close the tab. Do NOT paste long-lived keys."
        )
        byo_creds["aws_access_key_id"] = st.text_input("Access key ID", type="password")
        byo_creds["aws_secret_access_key"] = st.text_input("Secret access key", type="password")
        byo_creds["aws_session_token"] = st.text_input("Session token", type="password")
        byo_creds["region_name"] = st.text_input("Region", value=os.environ.get("AWS_REGION", "us-west-2"))
        if _shared_creds:
            st.caption(
                "ℹ️ Leave blank to use this deployment's own key. Fill these in to "
                "run Live mode on **your** AWS account instead."
            )

st.sidebar.markdown("### 3. Run")
run_clicked = st.sidebar.button("🤖 Run the agent", type="primary", use_container_width=True)

st.sidebar.markdown("---")
st.sidebar.caption(
    "No login required. Offline mode needs no AWS at all. Any credentials you "
    "enter are used only for the current session and never stored. "
    "All data shown is synthetic."
)

# ---------------------------------------------------------------------------
# Main — header + editable data
# ---------------------------------------------------------------------------
st.markdown(
    """
    <div class="rwt-hero">
      <h1>🧾 Return Window Tracker</h1>
      <p>Never lose money to a missed return window again. This Everyday Agent tracks every
      purchase's deadline, <b>auto-drafts</b> the routine return requests, and only
      <b>surfaces the ones that need your decision</b> — running quietly in the background.</p>
      <div class="rwt-pills">
        <span class="rwt-pill">⚡ No login required</span>
        <span class="rwt-pill">🔌 Works offline — no AWS keys</span>
        <span class="rwt-pill">🤖 Built with Strands Agents SDK</span>
        <span class="rwt-pill">☁️ Amazon Bedrock</span>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
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
            if use_offline:
                # Keyless path: full deterministic pipeline + template drafting.
                st.session_state.result = run_tracker_offline(cleaned, state_path=None)
                st.session_state.result_mode = "offline"
            else:
                # Pass any user-entered credentials to this single run only.
                # They are NOT written to os.environ or disk. If left blank, the
                # deployment's default credential chain is used.
                creds = None
                if byo_creds.get("aws_access_key_id") and byo_creds.get("aws_secret_access_key"):
                    creds = {k: v for k, v in byo_creds.items() if v}
                # state_path=None here so the hosted demo is stateless & repeatable.
                st.session_state.result = run_tracker(
                    cleaned, model=model_id or None, state_path=None, creds=creds
                )
                st.session_state.result_mode = "live"
        except Exception as exc:  # noqa: BLE001
            st.warning(
                "Couldn't reach Amazon Bedrock (missing/invalid credentials or "
                "model access). Falling back to **Offline preview** so you can "
                "still see the full demo."
            )
            try:
                st.session_state.result = run_tracker_offline(cleaned, state_path=None)
                st.session_state.result_mode = "offline"
            except Exception as exc2:  # noqa: BLE001
                st.session_state.result = None
                st.error(f"The agent could not run at all.\n\nDetails: {exc2}")

# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------
result = st.session_state.get("result")
if result:
    if st.session_state.get("result_mode") == "offline":
        st.info(
            "🔌 **Offline preview** — deterministic deadline math and the "
            "auto-handled vs. needs-you decisions are fully live; the return "
            "messages and digest are template-generated. Switch to **Live — "
            "Amazon Bedrock** in the sidebar for AI-drafted wording. No login "
            "required either way."
        )
    else:
        st.success("🟢 **Live** — return messages and digest drafted by Amazon Bedrock via Strands.")

    items = result.get("items", [])
    needs_you = [it for it in items if it.get("autonomy") == AUTONOMY_NEEDS_YOU]
    auto = [it for it in items if it.get("autonomy") == AUTONOMY_AUTO]
    none = [it for it in items if it.get("autonomy") == AUTONOMY_NONE]

    # Metric tiles (custom styled)
    tiles(len(items), len(needs_you), len(auto), len(none))

    st.markdown('<div class="rwt-h">🗒️ Daily digest</div>', unsafe_allow_html=True)
    st.info(result.get("digest", "").strip() or "No digest produced.")

    left, right = st.columns(2)
    with left:
        st.markdown(
            f'<div class="rwt-h" style="border-color:#f7c5c9">⚠️ Needs you — {len(needs_you)} decision(s)</div>',
            unsafe_allow_html=True,
        )
        if not needs_you:
            st.success("Nothing needs you right now. The agent has it covered. ✅")
        for it in needs_you:
            item_card(it, "rwt-needs")

    with right:
        st.markdown(
            f'<div class="rwt-h" style="border-color:#bde5c8">✅ Auto-handled — {len(auto)} draft(s) ready</div>',
            unsafe_allow_html=True,
        )
        if not auto:
            st.caption("No routine returns to auto-handle.")
        for it in auto:
            item_card(it, "rwt-auto")

    if none:
        st.markdown(
            f'<div class="rwt-h">ℹ️ No action needed — {len(none)}</div>',
            unsafe_allow_html=True,
        )
        for it in none:
            item_card(it, "rwt-none")

    # Structured output + download
    st.markdown(
        '<div class="rwt-h">🧩 Structured output (typed via Strands structured output)</div>',
        unsafe_allow_html=True,
    )
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
