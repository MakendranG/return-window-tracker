"""
Return Window Tracker — CLI entry point.

Loads sample_data/purchases.json, runs the Strands `return_tracker_agent`, and
prints a prioritized daily digest with drafted return-request messages. Also
writes the full structured JSON result next to the console summary.

Usage:
    python main.py                      # uses sample_data/purchases.json
    python main.py --input path.json    # use a custom purchases file
    python main.py --model <model_id>   # override the model (optional)
    python main.py --json-only          # print only the structured JSON

Built With: Strands Agents SDK.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from dotenv import load_dotenv

from agent import (
    AUTONOMY_AUTO,
    AUTONOMY_NEEDS_YOU,
    AUTONOMY_NONE,
    STATUS_ACT_SOON,
    STATUS_ALREADY_FLAGGED,
    STATUS_EXPIRED,
    STATUS_SAFE,
    run_tracker,
)

# Load environment variables (e.g. AWS creds / model config) from a .env file if
# present. No secrets are ever hardcoded — everything comes from the environment.
load_dotenv()

DEFAULT_INPUT = os.path.join(os.path.dirname(__file__), "sample_data", "purchases.json")
DEFAULT_STATE = os.path.join(os.path.dirname(__file__), "state.json")

# Emoji/label decorations per status for the console summary.
_STATUS_BADGE = {
    STATUS_EXPIRED: "❌ EXPIRED",
    STATUS_ACT_SOON: "⏰ ACT SOON",
    STATUS_ALREADY_FLAGGED: "🚩 FLAGGED FOR RETURN",
    STATUS_SAFE: "✅ SAFE",
}


def _load_purchases(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _print_console_summary(result: dict) -> None:
    """Render a clean, human-readable console summary from the structured result."""
    digest = result.get("digest", "")
    items = result.get("items", [])
    needs_you = result.get("needs_you_count", 0)
    auto = result.get("auto_handled_count", 0)

    print("\n" + "=" * 72)
    print(" RETURN WINDOW TRACKER — BACKGROUND AGENT DIGEST")
    print("=" * 72)
    print(f"\n🤖 I reviewed {len(items)} purchases. "
          f"{auto} handled automatically · {needs_you} need your decision.\n")
    print(digest.strip() + "\n")

    # The headline section: only the items that genuinely need a human decision.
    needs_you_items = [it for it in items if it.get("autonomy") == AUTONOMY_NEEDS_YOU]
    print("-" * 72)
    print(f" ⚠️  NEEDS YOU — {len(needs_you_items)} decision(s) to make")
    print("-" * 72)
    if not needs_you_items:
        print("\n   Nothing needs you right now. The agent has it covered. ✅")
    for it in needs_you_items:
        _print_item(it, show_draft=True)

    # Everything the agent quietly took care of on its own.
    auto_items = [it for it in items if it.get("autonomy") == AUTONOMY_AUTO]
    print("\n" + "-" * 72)
    print(f" ✅ AUTO-HANDLED — {len(auto_items)} return request(s) drafted & ready")
    print("-" * 72)
    for it in auto_items:
        _print_item(it, show_draft=True)

    # Informational: expired / safe (no action).
    info_items = [it for it in items if it.get("autonomy") == AUTONOMY_NONE]
    if info_items:
        print("\n" + "-" * 72)
        print(" ℹ️  NO ACTION (expired or safe — shown for awareness)")
        print("-" * 72)
        for it in info_items:
            badge = _STATUS_BADGE.get(it.get("status", ""), it.get("status", ""))
            print(f"   {badge}  {it.get('item')} ({it.get('store')}) — "
                  f"{it.get('days_left')} day(s) left, deadline {it.get('deadline')}")

    print("\n" + "=" * 72)
    print(" All data shown is synthetic sample data.")
    print("=" * 72 + "\n")


def _print_item(it: dict, show_draft: bool) -> None:
    """Print one item block with badge, dates, escalation reason, and optional draft."""
    badge = _STATUS_BADGE.get(it.get("status", ""), it.get("status", ""))
    days_left = it.get("days_left")
    price = it.get("price")
    price_str = f"${price:.2f}" if isinstance(price, (int, float)) else "n/a"
    new_flag = " 🆕" if it.get("seen_before") is False else ""
    print(f"\n{badge}  —  {it.get('item')}  ({it.get('store')}){new_flag}")
    print(
        f"   purchased {it.get('purchase_date')} | "
        f"deadline {it.get('deadline')} | "
        f"{days_left} day(s) left | {price_str}"
    )
    escalation = (it.get("escalation_reason") or "").strip()
    if escalation:
        print(f"   ↳ {escalation}")
    change = (it.get("change_note") or "").strip()
    if change:
        print(f"   ↳ {change}")
    draft = (it.get("draft_message") or "").strip()
    if show_draft and draft:
        print("   ── Drafted return request (copy & send) ──")
        for line in draft.splitlines():
            print(f"   | {line}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Track retailer return windows and draft return requests."
    )
    parser.add_argument(
        "--input",
        default=DEFAULT_INPUT,
        help="Path to a purchases JSON file (default: sample_data/purchases.json).",
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("STRANDS_MODEL_ID"),
        help="Optional model ID override (else uses Strands default / env).",
    )
    parser.add_argument(
        "--json-only",
        action="store_true",
        help="Print only the structured JSON result.",
    )
    parser.add_argument(
        "--state",
        default=DEFAULT_STATE,
        help="Path to the background-memory state file (default: state.json). "
             "Lets the agent remember what it already surfaced across runs.",
    )
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="Ignore any existing state file (treat every item as new).",
    )
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(
            f"ERROR: input file not found: {args.input}\n"
            "Generate the sample data first with:  python generate_sample_data.py",
            file=sys.stderr,
        )
        return 1

    purchases = _load_purchases(args.input)

    state_path = None if args.fresh else args.state

    try:
        result = run_tracker(purchases, model=args.model, state_path=state_path)
    except Exception as exc:  # noqa: BLE001 - surface any runtime/model error clearly
        print(f"ERROR running the agent: {exc}", file=sys.stderr)
        return 2

    if args.json_only:
        print(json.dumps(result, indent=2))
        return 0

    _print_console_summary(result)

    # Also emit the full structured JSON so it can be piped/stored.
    print("Structured JSON result:")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
