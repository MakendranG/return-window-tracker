"""
Return Window Tracker — a Strands Agents SDK agent.

PROBLEM STATEMENT
-----------------
Retailers set short return windows (often 15-30 days), and people routinely lose
money simply by forgetting a window closed — not because they didn't want to
return an item, but because there's no unified place tracking every purchase's
deadline across different stores and receipts.

DESIGN PRINCIPLE
----------------
The correctness-critical logic is DETERMINISTIC and lives in two Python @tool
functions, NEVER left to the LLM:
  * `check_return_deadlines` — computes each return deadline, days-left, and
    status (SAFE / ACT_SOON / EXPIRED / ALREADY_FLAGGED_FOR_RETURN).
  * `decide_autonomy` — decides, by auditable policy, which items the agent can
    handle on its own (AUTO_HANDLED) versus which to surface for a human decision
    (NEEDS_YOU) — the core "Everyday Agent" behavior of running quietly in the
    background and only pinging a human when it truly matters.

The LLM is used only for what language models are good at: drafting the
natural-language return-request messages and the human-readable digest. The final
result is returned via Strands structured output as a typed Pydantic object, and
a small state file gives the agent background memory across runs.

Built With: Strands Agents SDK.
"""

from __future__ import annotations

import json
import os
from datetime import date, datetime, timedelta
from typing import Any

from pydantic import BaseModel, Field
from strands import Agent, tool


# ---------------------------------------------------------------------------
# Classification thresholds (single source of truth)
# ---------------------------------------------------------------------------
SAFE_THRESHOLD_DAYS = 7  # more than this many days left => SAFE

# Classification labels used across the tool, agent, and CLI.
STATUS_SAFE = "SAFE"
STATUS_ACT_SOON = "ACT_SOON"
STATUS_EXPIRED = "EXPIRED"
STATUS_ALREADY_FLAGGED = "ALREADY_FLAGGED_FOR_RETURN"

# ---------------------------------------------------------------------------
# Autonomy labels — the "quiet background agent" behavior.
# ---------------------------------------------------------------------------
# The whole point of an Everyday Agent (per the hackathon brief) is to "run
# quietly in the background, make the safe calls on its own, and surface only
# when a human actually needs to weigh in." We encode that as a deterministic
# decision so it is auditable rather than left to the LLM's judgment.
AUTONOMY_AUTO = "AUTO_HANDLED"  # agent prepped everything; no human decision needed
AUTONOMY_NEEDS_YOU = "NEEDS_YOU"  # a real judgment call — surface this to the human
AUTONOMY_NONE = "NO_ACTION"  # nothing to do (SAFE, or unrecoverable EXPIRED)

# A purchase above this price is always surfaced for human confirmation before a
# return is "handled", because the stakes are high enough to warrant a look.
HIGH_VALUE_THRESHOLD = 150.0


def _parse_date(value: str) -> date:
    """Parse an ISO 'YYYY-MM-DD' date string into a date object."""
    return datetime.strptime(value, "%Y-%m-%d").date()


# ---------------------------------------------------------------------------
# DETERMINISTIC TOOL
# ---------------------------------------------------------------------------
@tool
def check_return_deadlines(purchases: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Deterministically compute the return deadline and urgency status for each
    purchase. This is pure Python math — the LLM must rely on these numbers
    rather than computing dates itself.

    For each purchase this tool computes:
        deadline = purchase_date + return_window_days
        days_left = deadline - today

    And classifies each item as one of:
        SAFE                        -> more than 7 days left
        ACT_SOON                    -> 1 to 7 days left (inclusive)
        EXPIRED                     -> deadline already passed (days_left < 0)
        ALREADY_FLAGGED_FOR_RETURN  -> the user already gave a
                                       reason_for_potential_return, so this item
                                       is intentionally being returned

    Note on precedence: if a reason_for_potential_return is present, the item is
    labelled ALREADY_FLAGGED_FOR_RETURN *unless* it is already EXPIRED, because a
    passed deadline is the most important thing to surface to the user.

    Args:
        purchases (list[dict]): Each dict should contain:
            - item (str): The item name.
            - store (str): Where it was purchased.
            - purchase_date (str): ISO date 'YYYY-MM-DD'.
            - return_window_days (int): Length of the return window in days.
            - price (float): Purchase price (used for prioritization/reporting).
            - reason_for_potential_return (str, optional): Why the user might
              return it. Blank/absent means "no current intent to return".

    Returns:
        dict: {
            "today": "YYYY-MM-DD",
            "items": [ ...one enriched record per purchase, sorted by urgency... ]
        }
        Each enriched record adds:
            - deadline (str, ISO date)
            - days_left (int)
            - status (str, one of the STATUS_* labels)
            - needs_draft (bool): True if the agent should draft a return message
              (ACT_SOON, EXPIRED-with-reason, or ALREADY_FLAGGED_FOR_RETURN).
    """
    today = date.today()
    enriched: list[dict[str, Any]] = []

    for p in purchases:
        purchase_date = _parse_date(p["purchase_date"])
        window_days = int(p["return_window_days"])
        deadline = purchase_date + timedelta(days=window_days)
        days_left = (deadline - today).days

        reason = (p.get("reason_for_potential_return") or "").strip()
        has_reason = bool(reason)

        # Deterministic classification (order matters — see docstring).
        if days_left < 0:
            status = STATUS_EXPIRED
        elif has_reason:
            status = STATUS_ALREADY_FLAGGED
        elif days_left <= SAFE_THRESHOLD_DAYS:
            status = STATUS_ACT_SOON
        else:
            status = STATUS_SAFE

        # Draft a return-request message when the item is time-sensitive or the
        # user already expressed intent to return it.
        needs_draft = (
            status == STATUS_ACT_SOON
            or status == STATUS_ALREADY_FLAGGED
            or (status == STATUS_EXPIRED and has_reason)
        )

        enriched.append(
            {
                "item": p["item"],
                "store": p["store"],
                "purchase_date": p["purchase_date"],
                "return_window_days": window_days,
                "price": p.get("price"),
                "reason_for_potential_return": reason,
                "deadline": deadline.isoformat(),
                "days_left": days_left,
                "status": status,
                "needs_draft": needs_draft,
            }
        )

    # Sort by urgency: soonest deadline first (fewest days_left first).
    enriched.sort(key=lambda r: r["days_left"])

    return {"today": today.isoformat(), "items": enriched}


# ---------------------------------------------------------------------------
# DETERMINISTIC TOOL #2 — AUTONOMY DECISION ("surface only real decisions")
# ---------------------------------------------------------------------------
@tool
def decide_autonomy(items: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Deterministically decide, for each already-classified item, whether the agent
    can handle it autonomously (AUTO_HANDLED) or must surface it to the human for
    a real decision (NEEDS_YOU). This implements the Everyday-Agent principle of
    "make the safe calls on your own, only ping a human when it truly matters."

    This is pure Python policy — NOT an LLM judgment — so the escalation behavior
    is predictable and auditable.

    Decision policy:
      * SAFE                       -> NO_ACTION (nothing to do yet).
      * EXPIRED without a reason   -> NO_ACTION (window is gone; not recoverable).
      * EXPIRED *with* a reason    -> NEEDS_YOU (the user wanted to return it but
                                      the window closed — worth a human trying a
                                      goodwill/warranty exception).
      * ACT_SOON / ALREADY_FLAGGED -> AUTO_HANDLED, UNLESS one of these escalation
                                      triggers fires, in which case NEEDS_YOU:
                                        - price >= HIGH_VALUE_THRESHOLD (high stakes)
                                        - deadline is TODAY or TOMORROW (days_left
                                          <= 1) (last-chance, no room for error)
                                        - the reason text is ambiguous/uncertain
                                          (contains words like "maybe"/"not sure")

    Args:
        items (list[dict]): The enriched records produced by
            `check_return_deadlines` (must include price, days_left, status, and
            reason_for_potential_return).

    Returns:
        dict: {
            "items": [ each input record + "autonomy" and "escalation_reason" ],
            "needs_you_count": <int>,
            "auto_handled_count": <int>
        }
    """
    ambiguity_markers = ("maybe", "not sure", "might", "unsure", "?", "possibly")
    out: list[dict[str, Any]] = []
    needs_you = 0
    auto = 0

    for it in items:
        status = it.get("status")
        price = it.get("price") or 0.0
        days_left = it.get("days_left", 0)
        reason = (it.get("reason_for_potential_return") or "").lower()

        autonomy = AUTONOMY_NONE
        escalation_reason = ""

        if status == STATUS_SAFE:
            autonomy = AUTONOMY_NONE
        elif status == STATUS_EXPIRED:
            if reason:
                autonomy = AUTONOMY_NEEDS_YOU
                escalation_reason = (
                    "Return window already closed but you wanted to return this — "
                    "a human could still try a goodwill or warranty exception."
                )
            else:
                autonomy = AUTONOMY_NONE
        else:  # ACT_SOON or ALREADY_FLAGGED_FOR_RETURN
            triggers = []
            if price >= HIGH_VALUE_THRESHOLD:
                triggers.append(f"high value (${price:.2f})")
            if days_left <= 1:
                triggers.append("deadline is today/tomorrow")
            if any(m in reason for m in ambiguity_markers):
                triggers.append("your reason sounds uncertain")

            if triggers:
                autonomy = AUTONOMY_NEEDS_YOU
                escalation_reason = "Surface for your call: " + "; ".join(triggers) + "."
            else:
                autonomy = AUTONOMY_AUTO
                escalation_reason = (
                    "Safe to auto-handle: return request drafted and ready to send."
                )

        if autonomy == AUTONOMY_NEEDS_YOU:
            needs_you += 1
        elif autonomy == AUTONOMY_AUTO:
            auto += 1

        record = dict(it)
        record["autonomy"] = autonomy
        record["escalation_reason"] = escalation_reason
        out.append(record)

    return {
        "items": out,
        "needs_you_count": needs_you,
        "auto_handled_count": auto,
    }


# ---------------------------------------------------------------------------
# STRUCTURED OUTPUT SCHEMA (Pydantic)
# ---------------------------------------------------------------------------
# Using Strands' structured_output with a Pydantic model makes the agent emit a
# reliably-typed object instead of hand-written JSON (which LLMs frequently break
# with bad escaping). This is both more robust and a first-class Strands feature.
class ReturnItem(BaseModel):
    """One purchase after classification, autonomy decision, and (optional) draft."""

    item: str
    store: str
    purchase_date: str
    deadline: str
    days_left: int
    price: float | None = None
    status: str = Field(description="SAFE | ACT_SOON | EXPIRED | ALREADY_FLAGGED_FOR_RETURN")
    autonomy: str = Field(description="AUTO_HANDLED | NEEDS_YOU | NO_ACTION")
    escalation_reason: str = Field(default="", description="Why it needs you, or why auto-handled.")
    draft_message: str = Field(default="", description="Ready-to-send return request, or empty.")


class TrackerResult(BaseModel):
    """The full digest the agent returns."""

    digest: str = Field(description="Human-readable, prioritized daily digest.")
    needs_you_count: int
    auto_handled_count: int
    items: list[ReturnItem]


# ---------------------------------------------------------------------------
# AGENT
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """\
You are the Return Window Tracker assistant — an Everyday Agent that runs quietly
in the background and only surfaces items when a human actually needs to decide.

Your job: help a consumer avoid losing money by missing retailer return windows.

IMPORTANT RULES:
1. You MUST call the `check_return_deadlines` tool to compute every deadline,
   days-left value, and status classification. NEVER compute dates or day counts
   yourself — always trust the tool's numbers.
2. Then you MUST call the `decide_autonomy` tool, passing it the `items` returned
   by `check_return_deadlines`. It decides — deterministically — which items the
   agent can handle on its own (AUTO_HANDLED) versus which need the human's
   attention (NEEDS_YOU). NEVER override these autonomy decisions; trust the tool.
3. For every item whose `needs_draft` is true, write a short, polite,
   ready-to-send return-request message addressed to the store. The message must
   reference the item name and the purchase date, and (when the user provided
   one) the reason_for_potential_return. Keep each message under ~90 words.
4. Produce a prioritized DAILY DIGEST written like a calm background assistant.
   LEAD with the "NEEDS YOU" items (real decisions), each with its
   escalation_reason. Then briefly note the "AUTO-HANDLED" items (drafts ready to
   send). Then a one-line note on EXPIRED and SAFE items. Rank by urgency
   (soonest deadline first).

Include EVERY purchase in your final answer, in the urgency order the tools
returned (soonest deadline first), using the tools' exact deadline, days_left,
status, autonomy, and escalation_reason values. Fill draft_message only for items
that needed a draft; otherwise leave it empty.
"""


def build_agent(model: str | None = None) -> Agent:
    """
    Construct the Strands `return_tracker_agent`.

    Args:
        model: Optional model ID string. If None, the Strands SDK default
            (Amazon Bedrock Claude Sonnet) is used. Credentials come only from
            environment variables — no secrets are hardcoded.
    """
    kwargs: dict[str, Any] = {
        # Two deterministic tools: deadline math + autonomy/escalation policy.
        "tools": [check_return_deadlines, decide_autonomy],
        "system_prompt": SYSTEM_PROMPT,
        # Silence the default token-streaming console output so the CLI can own
        # the clean, formatted summary. Set to a custom handler to observe the
        # raw agent loop if desired.
        "callback_handler": None,
    }
    if model:
        kwargs["model"] = model
    return Agent(**kwargs)


# The named agent the hackathon brief asks for.
return_tracker_agent = build_agent


def _item_key(item: dict[str, Any]) -> str:
    """Stable identity for a purchase across runs (store + item + purchase_date)."""
    return f"{item.get('store','')}|{item.get('item','')}|{item.get('purchase_date','')}"


def load_state(state_path: str | None) -> dict[str, Any]:
    """
    Load prior run state so the agent behaves like a background service that
    remembers what it already surfaced/drafted, instead of a one-shot script.

    Returns {} if no state file exists yet.
    """
    if not state_path or not os.path.exists(state_path):
        return {}
    try:
        with open(state_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_state(state_path: str | None, seen: dict[str, Any]) -> None:
    """Persist the set of items the agent has already acted on."""
    if not state_path:
        return
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(seen, f, indent=2)
        f.write("\n")


def run_tracker(
    purchases: list[dict[str, Any]],
    model: str | None = None,
    state_path: str | None = None,
) -> dict[str, Any]:
    """
    Run the full pipeline: deterministic tools -> LLM drafting/digest -> structured
    output, with optional persistent state for background/continuous operation.

    Args:
        purchases: The user's purchases.
        model: Optional model ID override.
        state_path: Optional path to a JSON state file. When provided, each item
            is tagged as "first_seen_run" (new since last run) or "carried_over",
            so the digest can behave like a background agent that only re-nudges
            when something is genuinely new or newly urgent.

    Returns a dict with keys "digest", "needs_you_count", "auto_handled_count",
    and "items". Raises RuntimeError if the model output cannot be parsed.
    """
    agent = build_agent(model=model)

    prior = load_state(state_path)  # {item_key: {"last_status": ..., "last_autonomy": ...}}

    prompt = (
        "Here are the user's purchases as JSON. First call check_return_deadlines "
        "with this exact list, then call decide_autonomy with the items it "
        "returns, then produce the prioritized digest and drafted return messages "
        "per your instructions.\n\n"
        f"{json.dumps(purchases, indent=2)}"
    )

    # Two-phase for reliability on Bedrock:
    #  Phase 1 — run the normal agent loop so it calls both deterministic tools
    #            (check_return_deadlines, decide_autonomy) and drafts messages.
    #  Phase 2 — ask the SAME agent to coerce that work into our Pydantic schema
    #            via structured_output (typed, no fragile hand-written JSON).
    agent(prompt)  # Phase 1: populates the agent's conversation with tool results.

    typed: TrackerResult = agent.structured_output(
        TrackerResult,
        "Using the tool results and drafts already in this conversation, produce "
        "the final structured result. Include every purchase in urgency order "
        "(soonest deadline first) with exact tool values.",
    )
    parsed: dict[str, Any] = typed.model_dump()

    # Annotate each item with background-memory info and refresh the state file.
    today_str = date.today().isoformat()
    updated_state: dict[str, Any] = {}
    for item in parsed.get("items", []):
        key = _item_key(item)
        prev = prior.get(key)
        if prev is None:
            item["seen_before"] = False
            item["change_note"] = "New since last run."
        else:
            item["seen_before"] = True
            if prev.get("last_status") != item.get("status"):
                item["change_note"] = (
                    f"Status changed since last run: {prev.get('last_status')} -> {item.get('status')}."
                )
            else:
                item["change_note"] = "Carried over from a previous run (already known)."
        updated_state[key] = {
            "last_status": item.get("status"),
            "last_autonomy": item.get("autonomy"),
            "last_seen": today_str,
        }

    save_state(state_path, updated_state)
    return parsed


# ---------------------------------------------------------------------------
# OFFLINE / KEYLESS PIPELINE
# ---------------------------------------------------------------------------
# Runs the FULL deterministic pipeline (both @tools) with ZERO AWS/Bedrock, and
# substitutes template-generated return messages + a template digest for the
# LLM-drafted ones. This lets the public try the visual demo with no credentials
# and no login. The "smart" part of the agent — the deadline math and the
# AUTO_HANDLED-vs-NEEDS_YOU escalation policy — is identical to the live path;
# only the natural-language wording is templated instead of model-generated.
def _unwrap(tool_obj):
    """Return the plain Python function underneath a Strands @tool object."""
    return getattr(tool_obj, "__wrapped__", tool_obj)


def _template_draft(it: dict[str, Any]) -> str:
    """Generate a polite, ready-to-send return-request message without an LLM."""
    item = it.get("item", "the item")
    store = it.get("store", "there")
    pdate = it.get("purchase_date", "")
    deadline = it.get("deadline", "")
    reason = (it.get("reason_for_potential_return") or "").strip()
    reason_line = f" The reason for my return is: {reason}" if reason else ""
    return (
        f"Subject: Return Request - {item}\n\n"
        f"Hello {store} team,\n\n"
        f"I would like to initiate a return for the {item} I purchased on {pdate}. "
        f"I understand the return window closes on {deadline}, so I am reaching out "
        f"promptly to complete this in time.{reason_line} Could you please let me "
        f"know the next steps to process this return?\n\n"
        f"Thank you for your assistance."
    )


def _template_digest(items: list[dict[str, Any]], needs_you: int, auto: int, today: str) -> str:
    """Build a readable prioritized digest without an LLM."""
    lines = [f"RETURN WINDOW TRACKER - Daily Digest ({today})",
             f"{needs_you} item(s) need your decision - {auto} auto-handled and ready.", ""]
    ny = [it for it in items if it.get("autonomy") == AUTONOMY_NEEDS_YOU]
    ah = [it for it in items if it.get("autonomy") == AUTONOMY_AUTO]
    none = [it for it in items if it.get("autonomy") == AUTONOMY_NONE]
    if ny:
        lines.append("NEEDS YOU (act in urgency order):")
        for it in ny:
            lines.append(
                f"  - {it['item']} ({it['store']}) - {it['days_left']} day(s) left "
                f"- {it.get('escalation_reason','')}"
            )
        lines.append("")
    if ah:
        lines.append("AUTO-HANDLED (drafts ready to send):")
        for it in ah:
            lines.append(f"  - {it['item']} ({it['store']}) - deadline {it['deadline']}")
        lines.append("")
    if none:
        lines.append("NO ACTION NEEDED:")
        for it in none:
            lines.append(f"  - {it['item']} ({it['store']}) - {it['status']}, {it['days_left']} day(s) left")
    return "\n".join(lines)


def run_tracker_offline(
    purchases: list[dict[str, Any]],
    state_path: str | None = None,
) -> dict[str, Any]:
    """
    Keyless pipeline: runs check_return_deadlines + decide_autonomy directly and
    fills draft_message/digest from templates. Returns the same dict shape as
    run_tracker (digest, needs_you_count, auto_handled_count, items).
    """
    checked = _unwrap(check_return_deadlines)(purchases)
    today_str = checked.get("today", date.today().isoformat())
    decided = _unwrap(decide_autonomy)(checked["items"])

    items_out: list[dict[str, Any]] = []
    for it in decided["items"]:
        rec = {
            "item": it.get("item"),
            "store": it.get("store"),
            "purchase_date": it.get("purchase_date"),
            "deadline": it.get("deadline"),
            "days_left": it.get("days_left"),
            "price": it.get("price"),
            "status": it.get("status"),
            "autonomy": it.get("autonomy"),
            "escalation_reason": it.get("escalation_reason", ""),
            "draft_message": _template_draft(it) if it.get("needs_draft") else "",
        }
        items_out.append(rec)

    result = {
        "digest": _template_digest(
            items_out, decided["needs_you_count"], decided["auto_handled_count"], today_str
        ),
        "needs_you_count": decided["needs_you_count"],
        "auto_handled_count": decided["auto_handled_count"],
        "items": items_out,
    }

    # Reuse the same background-memory annotation + persistence as the live path.
    prior = load_state(state_path)
    updated_state: dict[str, Any] = {}
    for item in result["items"]:
        key = _item_key(item)
        prev = prior.get(key)
        if prev is None:
            item["seen_before"] = False
            item["change_note"] = "New since last run."
        else:
            item["seen_before"] = True
            item["change_note"] = (
                "Carried over from a previous run (already known)."
                if prev.get("last_status") == item.get("status")
                else f"Status changed since last run: {prev.get('last_status')} -> {item.get('status')}."
            )
        updated_state[key] = {
            "last_status": item.get("status"),
            "last_autonomy": item.get("autonomy"),
            "last_seen": today_str,
        }
    save_state(state_path, updated_state)
    return result
