# Builder Center — Form Field Values

Copy these into the matching boxes in the AWS Builder Center "Create an article"
editor. The article body itself is in [`BUILDER_ARTICLE.md`](./BUILDER_ARTICLE.md).

## Title (80 / 255 characters)

```
Agents for Humans: Building a Return Window Tracker That Quietly Saves You Money
```

## Description (255 / 512 characters)

```
How I built an Everyday Agent with the Strands Agents SDK on Amazon Bedrock that tracks every purchase's return deadline, auto-drafts return requests, and only pings you when a real decision is needed — and why the smartest part of it never calls the LLM.
```

## Tags (5 maximum)

```
Strands Agents, Amazon Bedrock, AI Agents, Bedrock AgentCore, Python
```

## Canonical URL (optional)

```
https://makendrang.github.io/return-window-tracker/
```

## Cover image (optional, 1200 × 675)

A simple left-to-right flow graphic:
`Purchases → Strands Agent (deterministic tools) → LLM drafting → Prioritized digest`.
Keep it text-light (AWS recommends against text-heavy cover images).

## Body

Paste the full contents of [`BUILDER_ARTICLE.md`](./BUILDER_ARTICLE.md) into the
Body field. It is already valid Markdown and renders directly in the editor.

> **Important:** put the editor in **Markdown mode** before pasting. If you paste
> into the rich "Paragraph"/WYSIWYG mode, it inserts blank lines between table
> rows and **breaks the tables**. In Markdown mode the tables render correctly.

## Table-free fallback (use if the editor keeps breaking tables)

If your editor mangles Markdown tables no matter what, replace the two tables in
the body with these bullet lists — bullets survive any paste mode.

Replace the **links table** at the top with:

```
**🚀 Live demo:** https://return-window-tracker.streamlit.app
**🌐 Project page:** https://makendrang.github.io/return-window-tracker/
**💻 Source (MIT):** https://github.com/MakendranG/return-window-tracker
**🏷️ Track:** Agents for Humans → Everyday Agents
```

Replace the **layer-split table** with:

```
- 🔢 **Deadline math** — `check_return_deadlines` (Python @tool): computes deadline, days left, and status.
- ⚖️ **Escalation policy** — `decide_autonomy` (Python @tool): AUTO_HANDLED vs NEEDS_YOU, deterministic and auditable.
- ✍️ **Wording** — the LLM on Amazon Bedrock: return-request messages + human-readable digest.
```

Replace the **modes table** with:

```
- 🔌 **Offline preview (default)** — no AWS needed; full deterministic engine + template messages.
- 🟢 **Live — Amazon Bedrock** — Bedrock AI-drafts the messages and digest.
```
