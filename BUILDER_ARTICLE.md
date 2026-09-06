<!--
  NOTE: The article title goes in the Builder Center "Title" field (see
  BUILDER_ARTICLE_FIELDS.md), NOT here. Do not add an H1 to the body or the
  title will appear twice. Paste everything below into the Body field.
-->

![Strands Agents](https://img.shields.io/badge/Built_with-Strands_Agents_SDK-cf222e)
![Amazon Bedrock](https://img.shields.io/badge/Amazon-Bedrock-232f3e)
![AgentCore](https://img.shields.io/badge/Bedrock-AgentCore-ff9900)
![Python](https://img.shields.io/badge/Python-3.12-3776ab)
![License](https://img.shields.io/badge/License-MIT-1a7f37)

> **TL;DR** — I built an Everyday Agent with the **Strands Agents SDK** on **Amazon Bedrock** that tracks every purchase's return deadline, auto-drafts return requests, and only pings you when a real decision is needed. The twist: the smartest part of it *never* calls the LLM.

| | |
|---|---|
| 🚀 **Live demo** | <https://return-window-tracker.streamlit.app> |
| 🌐 **Project page** | <https://makendrang.github.io/return-window-tracker/> |
| 💻 **Source (MIT)** | <https://github.com/MakendranG/return-window-tracker> |
| 🏷️ **Track** | Agents for Humans → Everyday Agents |

---

## 😩 The problem

Retailers give you **15–30 days** to return something. That sounds generous — until you realize the receipts live in four different places: one store's email, another's paper slip, a third app's order history.

Nobody tracks all those deadlines in one spot. So people lose real money — **not** because they didn't want to return an item, but because the window quietly closed while they weren't looking.

> 💡 The *Everyday Agents* brief nailed the ideal: the best ones **"run quietly in the background, make the safe calls on their own, and surface only when a human actually needs to weigh in."** That one sentence shaped my entire design.

Meet **Return Window Tracker** — it watches every purchase's deadline, drafts the return messages for you, and only pings you when there's a genuine decision to make.

---

## 🧠 The key decision: don't let the LLM do math

The most important choice I made was **separating the deterministic work from the language work**.

An LLM is wonderful at writing a polite return email. It is *not* something you want computing *"is 2026-08-09 plus 30 days still in the future?"* Get that wrong and you tell someone their window is open when it closed yesterday. For a money-saving agent, that's unacceptable.

So the agent splits cleanly:

| Layer | Owned by | Responsibility |
|-------|----------|----------------|
| 🔢 **Deadline math** | `check_return_deadlines` (Python `@tool`) | `deadline = purchase_date + return_window_days`, days left, status |
| ⚖️ **Escalation policy** | `decide_autonomy` (Python `@tool`) | `AUTO_HANDLED` vs. `NEEDS_YOU` — deterministic, auditable |
| ✍️ **Wording** | LLM on Amazon Bedrock | Return-request messages + human-readable digest |

Every item lands in one of four statuses — 🟢 `SAFE`, 🟡 `ACT_SOON`, 🔴 `EXPIRED`, 🟣 `ALREADY_FLAGGED_FOR_RETURN` — and then a second, deterministic pass decides whether *you* need to be involved.

That escalation policy is what makes it an **Everyday Agent** and not a chatbot. It surfaces an item only when it truly matters:

```python
@tool
def decide_autonomy(items: list[dict]) -> dict:
    """Deterministically decide AUTO_HANDLED vs NEEDS_YOU for each item."""
    ambiguity_markers = ("maybe", "not sure", "might", "unsure", "?", "possibly")
    for it in items:
        triggers = []
        if (it.get("price") or 0) >= HIGH_VALUE_THRESHOLD:      # expensive
            triggers.append(f"high value (${it['price']:.2f})")
        if it["days_left"] <= 1:                                # last chance
            triggers.append("deadline is today/tomorrow")
        reason = (it.get("reason_for_potential_return") or "").lower()
        if any(m in reason for m in ambiguity_markers):         # unsure
            triggers.append("your reason sounds uncertain")
        # → NEEDS_YOU when any trigger fires, otherwise AUTO_HANDLED
```

The LLM then does what it's genuinely good at: drafting the messages and digest — always reusing the tools' exact numbers.

---

## ☁️ Where AWS comes in

**Amazon Bedrock** is the foundation-model runtime for the whole thing. The Strands Agents SDK defaults to Bedrock (Claude Sonnet), so both the agent's reasoning **and** the drafting run on Bedrock:

- 🔁 **The agentic loop** — the model decides to call `check_return_deadlines`, then `decide_autonomy`, reasoning over the results.
- ✉️ **The drafting layer** — Bedrock writes each copy-and-send return message and the prioritized digest.

I also built a **Bedrock AgentCore Runtime** entrypoint so the *same* agent can be deployed as a managed HTTP service — remarkably little code thanks to the Strands integration:

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

> ♻️ One `agent.py` core powers **three interfaces** — a CLI, a Streamlit web UI, and the AgentCore entrypoint — with zero logic duplicated.

---

## 🧩 Reliability: structured output over hand-written JSON

My first version asked the model to emit JSON directly. It worked… until the model wrote an escaped apostrophe inside a string and the parser choked. Instead of patching escaping bugs forever, I switched to **Strands structured output** with a Pydantic schema:

```python
class TrackerResult(BaseModel):
    digest: str
    needs_you_count: int
    auto_handled_count: int
    items: list[ReturnItem]

typed: TrackerResult = agent.structured_output(TrackerResult, prompt)
```

> ✅ **Lesson:** if you need machine-readable output from an LLM, let the SDK's structured-output feature handle serialization. More robust *and* a first-class Strands capability.

---

## 🔄 Running quietly in the background

To feel like a real background service instead of a one-shot script, the agent keeps a tiny `state.json` memory. Each run tags every item as **new since the last run** or **carried over** — so it only re-nudges you when something is genuinely new or newly urgent. That's the difference between a demo and something you'd actually let run every morning.

---

## 🔓 Usable by anyone — with no AWS keys

For a public demo, asking strangers to paste AWS credentials is a non-starter. So the app has two modes:

| Mode | Needs AWS? | What runs |
|------|:----------:|-----------|
| 🔌 **Offline preview** *(default)* | ❌ No | Full deterministic engine + template-written messages |
| 🟢 **Live — Amazon Bedrock** | ✅ Yes | Bedrock AI-drafts the messages & digest |

In Offline mode the *smart* part of the agent is 100% live — only the wording is templated. In Live mode, credentials are entered in an in-memory widget, passed to a scoped `boto3` session for a single run, and **never written to disk or the environment**.

> 🎯 A judge can click the link and see the agent working immediately, then optionally flip to live Bedrock on their own account.

---

## 📝 What I'd tell another builder

1. **Push correctness into deterministic tools.** Let the LLM write prose, not compute facts.
2. **Design for "only surface real decisions."** The escalation policy *is* the product for an Everyday Agent.
3. **Use structured output.** Don't hand-parse LLM JSON.
4. **Make the demo keyless.** The easiest way for people to try your agent is the one where they don't have to do anything.

---

Return Window Tracker takes a boring, money-losing chore off your plate and only interrupts you when your judgment genuinely matters. **That, to me, is what an Everyday Agent should be.** 🙌

---

**🛠️ Built With:** Strands Agents SDK · Amazon Bedrock · Amazon Bedrock AgentCore · Python · Streamlit

<sub>All data in the demo is synthetic sample data.</sub>
