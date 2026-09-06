"""
Generate sample_data/purchases.json with realistic, RELATIVE dates.

Dates are computed relative to "today" at generation time so the demo always
looks fresh (a mix of SAFE, ACT_SOON, and EXPIRED cases) instead of going stale.

ALL DATA IS SYNTHETIC / SAMPLE DATA. Store names, items, and prices are made up
for demonstration purposes only.

Run this to (re)generate the sample file:
    python generate_sample_data.py
"""

from __future__ import annotations

import json
import os
from datetime import date, timedelta

# (days_ago_purchased, return_window_days, item, store, price, reason)
# Chosen so that purchase_date + return_window_days lands across the spectrum of
# statuses AND across the autonomy decisions (AUTO_HANDLED vs NEEDS_YOU):
#   deadline in the future by >7 days      -> SAFE            -> NO_ACTION
#   deadline 1-7 days away                  -> ACT_SOON        -> AUTO_HANDLED*
#   deadline in the past                    -> EXPIRED         -> NO_ACTION*
#   reason present                          -> ALREADY_FLAGGED -> AUTO_HANDLED*
#   * escalates to NEEDS_YOU when: price >= $150, deadline is today/tomorrow,
#     the reason is ambiguous, or an expired item still has a return reason.
_SPEC = [
    # --- SAFE (comfortable buffer) -> NO_ACTION ---
    (2, 30, "Wireless Noise-Cancelling Headphones", "SoundHub", 199.99, ""),
    (5, 45, "Cast-Iron Skillet 12in", "Kitchen Corner", 39.95, ""),
    (1, 90, "Trail Running Shoes", "Peak Outfitters", 128.00, ""),

    # --- ACT_SOON, safe to AUTO_HANDLE (low value, a few days of runway) ---
    (26, 30, "4K Streaming Stick", "MediaMart", 49.99, ""),
    (24, 30, "Mechanical Keyboard", "GadgetGo", 89.99, ""),
    (13, 15, "Cotton Bed Sheet Set (Queen)", "HomeThread", 74.50, ""),

    # --- ACT_SOON but NEEDS_YOU: high value ($249 >= $150) ---
    (28, 30, "Espresso Machine", "BrewWorks", 249.00, ""),

    # --- ACT_SOON but NEEDS_YOU: deadline is today/tomorrow (days_left <= 1) ---
    (29, 30, "Standing Desk Converter", "WorkNest", 129.00, ""),

    # --- ACT_SOON but NEEDS_YOU: ambiguous reason ---
    (25, 30, "Fitness Tracker Watch", "GadgetGo", 99.00, "Might return — not sure if I'll use it."),

    # --- EXPIRED, no reason -> NO_ACTION (window gone) ---
    (40, 30, "USB-C Charging Cable 3-pack", "GadgetGo", 15.99, ""),

    # --- EXPIRED WITH a reason -> NEEDS_YOU (try goodwill/warranty exception) ---
    (45, 30, "Desk Lamp (LED)", "WorkNest", 32.00, "Flickers intermittently — defective."),

    # --- ALREADY_FLAGGED_FOR_RETURN, safe to AUTO_HANDLE ---
    (7, 30, "Bluetooth Speaker", "SoundHub", 59.99, "Left channel crackles at high volume."),

    # --- ALREADY_FLAGGED_FOR_RETURN but NEEDS_YOU: high value ($149? -> bump to 189) ---
    (10, 60, "Winter Jacket (size L)", "TrailGear", 189.00, "Too small — need size XL."),
]


def build_purchases(today: date | None = None) -> list[dict]:
    today = today or date.today()
    purchases = []
    for days_ago, window, item, store, price, reason in _SPEC:
        purchase_date = today - timedelta(days=days_ago)
        purchases.append(
            {
                "item": item,
                "store": store,
                "purchase_date": purchase_date.isoformat(),
                "return_window_days": window,
                "price": price,
                "reason_for_potential_return": reason,
            }
        )
    return purchases


def main() -> None:
    out_dir = os.path.join(os.path.dirname(__file__), "sample_data")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "purchases.json")

    purchases = build_purchases()
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(purchases, f, indent=2)
        f.write("\n")

    print(f"Wrote {len(purchases)} synthetic purchases to {out_path}")


if __name__ == "__main__":
    main()
