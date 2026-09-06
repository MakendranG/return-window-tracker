# Return Window Tracker

A **Strands Agents SDK** agent that quietly tracks the return deadline of every
purchase you make across different stores, handles the routine returns on its
own, and only pings you when there's a real decision to make — so you never lose
money to a missed return window again.

> Hackathon: **Agents for Humans** — Everyday Agents track.
> **Built With: Strands Agents SDK** (on Amazon Bedrock).
>
> - 🚀 **Live demo (Streamlit):** https://return-window-tracker.streamlit.app
> - 🌐 **Landing page (GitHub Pages):** https://makendrang.github.io/return-window-tracker/
> - 💻 **Source:** https://github.com/MakendranG/return-window-tracker
> - 🖥️ **Interfaces:** Streamlit web UI (`app.py`), CLI (`main.py`), and a Bedrock
>   AgentCore Runtime entrypoint (`agentcore_app.py`). See [DEPLOYMENT.md](./DEPLOYMENT.md).

## The problem (in plain language)

Retailers set short return windows (often 15–30 days), and people routinely lose
money simply by forgetting a window closed — not because they didn't want to
return an item, but because there's no unified place tracking every purchase's
deadline across different stores and receipts.

You buy a coffee maker from one store, headphones from another, and a jacket
online. Each has its own return window buried in a different receipt or email.
Miss one by a day and you're stuck with something you didn't want. Return Window
Tracker gives you one place that watches every deadline, drafts the return
requests for you, and nudges you only when it genuinely needs your call.

## Who it's for

Any consumer juggling multiple purchases and returns across different stores —
online and in-person — who wants a single, trustworthy view of what needs action
and when.

## What it does

- Takes a list of purchases (item, store, purchase date, return-window length,
  price, and an optional reason you might return it).
- Computes each item's exact return deadline and classifies it as:
  - **SAFE** — more than 7 days left
  - **ACT_SOON** — 1–7 days left
  - **EXPIRED** — the deadline already passed
  - **ALREADY_FLAGGED_FOR_RETURN** — you already noted a reason to return it
- Decides, deterministically, what it can do on its own versus what needs you:
  - **AUTO_HANDLED** — safe, routine returns; the agent drafts a ready-to-send
    message and needs no decision from you.
  - **NEEDS_YOU** — surfaced for a human call when the stakes are high: the item
    is expensive (≥ $150), the deadline is today/tomorrow, your reason sounds
    uncertain, or the window already closed on something you wanted to return
    (worth trying a goodwill/warranty exception).
- Drafts a polite, copy-and-send return-request message for every actionable item.
- Produces a **prioritized daily digest** that leads with the items that
  **need you**, then lists what it **auto-handled**, then a one-line note on the
  rest — ranked by urgency (soonest deadline first).
- **Remembers across runs** via a small `state.json` file, so it behaves like a
  background service that only re-flags what's genuinely new or newly urgent
  (items new since the last run are marked 🆕).
- Outputs both **structured JSON** (typed via Strands structured output) and a
  **clean console summary**.

## How it works

This is a genuine Strands agent with the correctness-critical logic pushed into
**two deterministic Python `@tool` functions**, and the LLM used only for what
language models are actually good at:

1. **`check_return_deadlines`** — pure Python date math. Computes
   `deadline = purchase_date + return_window_days`, the days left, and the status
   for every item. The model is instructed never to compute dates itself.
2. **`decide_autonomy`** — pure Python policy. Decides AUTO_HANDLED vs. NEEDS_YOU
   using auditable rules (price threshold, deadline proximity, ambiguous reason,
   expired-with-reason). Escalation is predictable, not left to model judgment.
3. **LLM drafting layer** — the Strands agent (Amazon Bedrock Claude Sonnet)
   writes the natural-language return-request messages and the human-readable
   digest, using the tools' exact numbers.
4. **Strands structured output** — the final result is coerced into a typed
   Pydantic schema (`TrackerResult`), so the JSON is always well-formed.

```
Purchase data → Strands Agent
                  ├─ @tool check_return_deadlines  (deterministic dates/status)
                  └─ @tool decide_autonomy         (deterministic escalation)
              → LLM drafting layer (return messages + digest)
              → structured output (typed JSON) + clean console summary
```

See [ARCHITECTURE.md](./ARCHITECTURE.md) for the full Mermaid diagram and flow.

## Project layout

```
return-window-tracker/
├── agent.py                  # Strands agent + 2 deterministic @tools + Pydantic schema
├── app.py                    # Streamlit web UI (visual demo)
├── agentcore_app.py          # Amazon Bedrock AgentCore Runtime entrypoint (/invocations, /ping)
├── main.py                   # CLI entry point (loads data, runs agent, prints digest)
├── generate_sample_data.py   # Regenerates sample_data/purchases.json with relative dates
├── sample_data/
│   └── purchases.json        # 13 synthetic purchases across every status & autonomy case
├── docs/
│   └── index.html            # GitHub Pages landing page (static)
├── state.json                # Background memory (auto-created at runtime; git-ignored)
├── requirements.txt          # App + CLI + UI dependencies
├── requirements-agentcore.txt# Lean deps for the AgentCore runtime container
├── .streamlit/config.toml    # Streamlit theme
├── .env.example
├── ARCHITECTURE.md
├── DEPLOYMENT.md             # Streamlit Cloud + GitHub Pages + AgentCore steps
├── LICENSE                   # MIT
└── .gitignore
```

## Run the web UI (Streamlit)

```bash
pip install -r requirements.txt
streamlit run app.py
```

Then open the local URL Streamlit prints. Edit the purchases table, click
**Run the agent**, and see the prioritized digest with the "needs you" vs.
"auto-handled" split and the drafted return messages. The same app is deployed
publicly on Streamlit Community Cloud (link at the top). Deployment steps for the
live demo, the GitHub Pages landing page, and the optional Bedrock AgentCore
Runtime are in [DEPLOYMENT.md](./DEPLOYMENT.md).

## Setup (from a cold start)

You need **Python 3.10+** and AWS credentials with access to Amazon Bedrock
(the Strands SDK default model provider is Bedrock Claude Sonnet).

```bash
# 1. Clone the repository
git clone https://github.com/MakendranG/return-window-tracker.git
cd return-window-tracker

# 2. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure credentials (NO secrets are stored in code)
cp .env.example .env
# then edit .env and fill in your AWS credentials / region

# 5. (Optional) regenerate fresh sample data with dates relative to today
python generate_sample_data.py

# 6. Run the agent end-to-end
python main.py
```

Useful flags:

```bash
python main.py --input path/to/your_purchases.json   # use your own data
python main.py --model global.anthropic.claude-sonnet-4-6   # override the model
python main.py --json-only                            # print only structured JSON
python main.py --fresh                                # ignore saved state (all items new)
python main.py --state path/to/state.json             # custom background-memory file
```

### Credentials

No secrets are hardcoded anywhere — everything is read from environment
variables (loaded from `.env` if present). Provide either standard AWS keys
(`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`) or a Bedrock API key
(`AWS_BEARER_TOKEN_BEDROCK`). See `.env.example`.

## Sample output

Real output from `python main.py` against the included synthetic sample data
(dates are relative to the day it runs):

```
========================================================================
 RETURN WINDOW TRACKER — BACKGROUND AGENT DIGEST
========================================================================

🤖 I reviewed 13 purchases. 4 handled automatically · 5 need your decision.

🔴 NEEDS YOU (act in urgency order):
1. Standing Desk Converter — WorkNest | TOMORROW (Sep 7) | $129.00
   → Deadline is today/tomorrow — your go-ahead required immediately.
2. Espresso Machine — BrewWorks | Sep 8 | $249.00
   → High-value item; needs your explicit sign-off before a draft is sent.
3. Fitness Tracker Watch — GadgetGo | Sep 11 | $99.00
   → Your reason is uncertain ("not sure if I'll use it") — decide yes/no; 5 days left.
4. Desk Lamp (LED) — WorkNest | EXPIRED Aug 22 | $32.00
   → Window closed (-15 days) but item is defective — a warranty/goodwill exception may still apply.
5. Winter Jacket (size L) — TrailGear | Oct 26 | $189.00
   → High-value return flagged (wrong size); needs your approval to proceed.

🟡 AUTO-HANDLED (drafts ready to send):
6. Cotton Bed Sheet Set (Queen) — HomeThread | Sep 8 | $74.50
7. 4K Streaming Stick — MediaMart | Sep 10 | $49.99
8. Mechanical Keyboard — GadgetGo | Sep 12 | $89.99
9. Bluetooth Speaker — SoundHub | Sep 29 | $59.99 (defective — left channel crackles)

------------------------------------------------------------------------
 ⚠️  NEEDS YOU — 5 decision(s) to make
------------------------------------------------------------------------

⏰ ACT SOON  —  Standing Desk Converter  (WorkNest) 🆕
   purchased 2026-08-08 | deadline 2026-09-07 | 1 day(s) left | $129.00
   ↳ Surface for your call: deadline is today/tomorrow.
   ↳ New since last run.
   ── Drafted return request (copy & send) ──
   | Subject: Return Request — Standing Desk Converter (Purchased Aug 8, 2026)
   |
   | Hello WorkNest team,
   |
   | I'd like to initiate a return for the Standing Desk Converter I purchased
   | on August 8, 2026. I understand the return deadline is September 7th and am
   | reaching out to ensure the return is processed within the window. Please let
   | me know the next steps.
   |
   | Thank you for your assistance.
```

The CLI also prints the full **structured JSON** result (digest, counts, and
per-item records including `status`, `autonomy`, `escalation_reason`,
`deadline`, `days_left`, and `draft_message`) so it can be piped into other tools.

## Note on data

All data in `sample_data/` is **synthetic sample data** — the store names,
items, prices, and reasons are fictional and generated for demonstration only.
Dates are computed relative to "today" at generation time so the demo always
shows a realistic mix of safe, urgent, expired, and needs-you items.

## License

MIT — see [LICENSE](./LICENSE).
