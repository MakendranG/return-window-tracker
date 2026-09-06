# Agents for Humans: Building a Return Window Tracker That Quietly Saves You Money

> How I built an Everyday Agent with the Strands Agents SDK on Amazon Bedrock — and why the smartest part of it never calls the LLM.

Retailers give you 15–30 days to return something. That sounds generous until you realize the receipts live in four different places: one store's email, another store's paper slip, a third app's order history. Nobody tracks all of those deadlines in one spot — so people lose real money, not because they didn't want to return an item, but because the window quietly closed while they weren't looking.

That's a perfect fit for the **Agents for Humans** hackathon's *Everyday Agents* track: a small, repetitive, money-losing chore that an agent can take off your plate. The brief said it best — the strongest Everyday Agents *"run quietly in the background, make the safe calls on their own, and surface only when a human actually needs to weigh in."* That one sentence shaped my entire design.

So I built **Return Window Tracker**: an agent that watches every purchase's return deadline, drafts the return-request messages for you, and only pings you when there's a genuine decision to make.

- **Live demo:** <https://return-window-tracker.streamlit.app>
- **Project page:** <https://makendrang.github.io/return-window-tracker/>
- **Source (MIT):** <https://github.com/MakendranG/return-window-tracker>

## The Key Design Decision: Don't Let the LLM Do Math

The single most important choice I made was **separating the deterministic work from the language work**.

An LLM is wonderful at writing a polite return email. It is *not* something you want computing "is 2026-08-09 plus 30 days still in the future?" Get that wrong and you tell someone their window is open when it closed yesterday. For a money-saving agent, that's unacceptable.

So the agent has **two deterministic Python `@tool` functions** that own everything correctness-critical, and the LLM is used *only* for natural language:

1. **`check_return_deadlines`** — pure Python. For each purchase it computes `deadline = purchase_date + return_window_days`, the days left, and a status: `SAFE`, `ACT_SOON`, `EXPIRED`, or `ALREADY_FLAGGED_FOR_RETURN`.
2. **`decide_autonomy`** — pure Python policy. It decides, by auditable rules, whether the agent can handle an item on its own (`AUTO_HANDLED`) or must surface it to the human (`NEEDS_YOU`).

The escalation rules are what make it an *Everyday Agent* rather than a chatbot. It surfaces an item for a human only when the item is expensive (≥ $150), the deadline is today or tomorrow, the user's stated reason sounds uncertain, or the window already closed on something they wanted to return:

```python
@tool
def decide_autonomy(items: list[dict]) -> dict:
    """Deterministically decide AUTO_HANDLED vs NEEDS_YOU for each item."""
    ambiguity_markers = ("maybe", "not sure", "might", "unsure", "?", "possibly")
    for it in items:
        triggers = []
        if (it.get("price") or 0) >= HIGH_VALUE_THRESHOLD:
            triggers.append(f"high value (${it['price']:.2f})")
        if it["days_left"] <= 1:
            triggers.append("deadline is today/tomorrow")
        reason = (it.get("reason_for_potential_return") or "").lower()
        if any(m in reason for m in ambiguity_markers):
            triggers.append("your reason sounds uncertain")
        # NEEDS_YOU when any trigger fires, otherwise AUTO_HANDLED
```

The LLM then does what it's genuinely good at: drafting the return-request messages and writing the human-readable daily digest — always reusing the tools' exact numbers.

## Where AWS Comes In

**Amazon Bedrock** is the foundation-model runtime for the whole thing. The Strands Agents SDK defaults to Bedrock (Claude Sonnet), so both the agent's reasoning and the natural-language drafting run on Bedrock:

- **The agentic loop** — the model on Bedrock decides to call `check_return_deadlines`, then `decide_autonomy`, reasoning over the results.
- **The drafting layer** — Bedrock writes each polished, copy-and-send return message and the prioritized digest.

I also built a **Bedrock AgentCore Runtime** entrypoint so the exact same agent can be deployed as a managed HTTP service. With the Strands SDK integration it's remarkably little code:

```python
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from agent import run_tracker

app = BedrockAgentCoreApp()

@app.entrypoint
def invoke(payload):
    return run_tracker(payload.get("purchases") or [], state_path=None)

if __name__ == "__main__":
    app.run()
```

The same `agent.py` core powers three interfaces — a CLI, a Streamlit web UI, and the AgentCore entrypoint — with no logic duplicated.

## Making It Reliable: Structured Output Over Hand-Written JSON

My first version asked the model to emit JSON directly. It worked... until the model wrote an escaped apostrophe inside a string and the JSON parser choked. Rather than patch escaping bugs forever, I switched to **Strands structured output** with a Pydantic schema:

```python
class TrackerResult(BaseModel):
    digest: str
    needs_you_count: int
    auto_handled_count: int
    items: list[ReturnItem]

typed: TrackerResult = agent.structured_output(TrackerResult, prompt)
```

Lesson learned: if you need machine-readable output from an LLM, let the SDK's structured-output feature handle serialization. It's more robust *and* it's a first-class Strands capability.

## Running Quietly in the Background

To make it feel like a real background agent instead of a one-shot script, I added a tiny `state.json` memory. On each run the agent tags every item as *new since the last run* or *carried over* — so it only re-nudges you when something is genuinely new or newly urgent. Re-run it and yesterday's items are marked "carried over," not flagged again. That's the difference between a demo and something you'd actually let run every morning.

## Making It Usable by Anyone — With No AWS Keys

For a public demo, asking strangers to paste AWS credentials is a non-starter. So the app has two modes:

- **Offline preview (default):** runs the *full deterministic engine* — deadlines, statuses, and the auto-handled-vs-needs-you decisions — with template-written messages. No AWS, no keys, no login. The "smart" part of the agent is 100% live; only the wording is templated.
- **Live — Amazon Bedrock:** AI-drafts the messages via Bedrock. Credentials are entered in an in-memory widget, passed to a scoped `boto3` session for a single run, and never written to disk or the environment.

A judge can click the link and immediately see the agent working, then optionally flip to live Bedrock on their own account.

## What I'd Tell Another Builder

1. **Push correctness into deterministic tools.** Let the LLM write prose, not compute facts. It makes the agent auditable and trustworthy.
2. **Design for "only surface real decisions."** The escalation policy *is* the product for an Everyday Agent. Make it explicit and testable.
3. **Use structured output.** Don't hand-parse LLM JSON.
4. **Make the demo keyless.** The easiest way for people to try your agent is the one where they don't have to do anything.

Return Window Tracker takes a boring, money-losing chore off your plate and only interrupts you when your judgment genuinely matters. That, to me, is what an Everyday Agent should be.

---

**Built With:** Strands Agents SDK · Amazon Bedrock · Amazon Bedrock AgentCore · Python · Streamlit

*All data in the demo is synthetic sample data.*
