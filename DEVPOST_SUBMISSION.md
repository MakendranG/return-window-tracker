# Devpost Submission — Return Window Tracker

Copy each field below into the matching box in the Devpost submission form.

---

## General info

### Project name  (max 60 chars)

```
Return Window Tracker
```

### Elevator pitch  (max 200 chars)

```
An Everyday Agent (Strands + Bedrock) that tracks every purchase's return deadline, auto-drafts return requests, and only pings you when a real decision is needed.
```

---

## Project details → About the project  (Markdown)

Paste everything in this block into the "About the project" field:

```markdown
## 🧾 Inspiration

Retailers give you 15–30 days to return something — but the receipts live in four
different places: one store's email, another's paper slip, a third app's order
history. Nobody tracks all those deadlines in one spot, so people lose real money
just because a window quietly closed while they weren't looking. That is exactly
the kind of small, repetitive, money-losing chore the **Everyday Agents** track is
about, so I built an agent that quietly handles it.

## 🤖 What it does

**Return Window Tracker** watches every purchase's return deadline and:

- Computes each item's exact deadline and status: **SAFE**, **ACT_SOON**,
  **EXPIRED**, or **ALREADY_FLAGGED_FOR_RETURN**.
- Decides — on its own — what it can **auto-handle** vs. what **needs you**. It
  only surfaces an item for a human decision when it truly matters: the item is
  expensive (≥ $150), the deadline is today/tomorrow, your reason sounds
  uncertain, or the window already closed on something you wanted to return.
- **Auto-drafts** a polite, copy-and-send return-request message for every
  actionable item.
- Produces a **prioritized daily digest** that leads with what needs you, then
  what it handled for you.
- **Remembers across runs** (a small state file) so it only re-nudges you when
  something is genuinely new or newly urgent — like a real background agent.

## 🧠 How I built it

The core design decision: **separate the deterministic work from the language
work.** An LLM should not be computing "is purchase date + 30 days still in the
future?" — get that wrong and you lose money. So:

- Two deterministic Python **`@tool`** functions own everything correctness-
  critical: `check_return_deadlines` (all date math + status) and
  `decide_autonomy` (the auto-handled-vs-needs-you escalation policy). This is
  auditable Python, never LLM guesswork.
- The **LLM on Amazon Bedrock** (via the **Strands Agents SDK**) is used only for
  what it's great at: drafting the return messages and the digest.
- **Strands structured output** (Pydantic) returns a reliably-typed result.
- The same `agent.py` core powers **three interfaces**: a CLI, a Streamlit web
  UI, and a **Bedrock AgentCore Runtime** entrypoint — no logic duplicated.
- A public-friendly **Offline mode** runs the full deterministic engine with
  template messages, so anyone can try the demo with **no AWS keys and no login**.

## 🚧 Challenges I ran into

- **LLM-written JSON kept breaking** (bad escape characters). I fixed it properly
  by switching to Strands structured output instead of hand-parsing JSON.
- **Letting the public try it without credentials.** AWS can't hand a browser's
  console session to a web app, so I built a keyless Offline mode as the default
  and an optional, session-only "bring your own temporary credentials" path.

## 🏆 Accomplishments I'm proud of

- A genuinely **autonomous** Everyday Agent that acts on the safe cases and only
  interrupts you for real decisions.
- Correctness is **deterministic and auditable**, not left to the model.
- Anyone can try the live demo instantly — no keys, no login.

## 📚 What I learned

- Push correctness into deterministic tools; let the LLM handle prose.
- The escalation policy *is* the product for an Everyday Agent.
- Use the SDK's structured output — don't hand-parse LLM JSON.

## 🚀 What's next

- Real receipt/email ingestion, calendar reminders, and one-click return filing.

**Built With: Strands Agents SDK** on **Amazon Bedrock** (with a Bedrock
AgentCore Runtime entrypoint). All demo data is synthetic.
```

---

## Built with  (tags — up to 25)

```
strands-agents, amazon-bedrock, bedrock-agentcore, aws, python, streamlit, pydantic, boto3, ai-agents, llm, generative-ai, github-pages
```

---

## "Try it out" links

- Live demo (Streamlit):
  ```
  https://return-window-tracker.streamlit.app
  ```
- Project page (GitHub Pages):
  ```
  https://makendrang.github.io/return-window-tracker/
  ```
- Source code (GitHub):
  ```
  https://github.com/MakendranG/return-window-tracker
  ```

---

## Video demo link

```
(paste your YouTube/Vimeo URL here — max 5 min, must show the project working + pitch)
```

---

## PUBLIC URL to your code repo

```
https://github.com/MakendranG/return-window-tracker
```

*(Repo has MIT license visible in the About section + README with setup instructions.)*

---

## Architecture diagram (REQUIRED — pdf/png/jpg)

Use the diagram in `ARCHITECTURE.md`. To produce an image quickly:
- Open `ARCHITECTURE.md` on GitHub (the Mermaid diagram renders), screenshot it, save as PNG; **or**
- Screenshot the architecture section of the GitHub Pages project page.

Then upload that PNG/JPG here.

---

## AWS Builder ID

```
(the email address you used to create your AWS Builder ID)
```

---

## (Optional) URL to your live demo link

```
https://return-window-tracker.streamlit.app
```

---

## (If applicable) testing instructions

```
No credentials needed. Open the live demo, keep the sidebar on "Offline preview
(no AWS needed)", and click "Run the agent" to see the prioritized digest with
the needs-you vs. auto-handled split and drafted return messages. To test Live
Amazon Bedrock, switch the mode to "Live — Amazon Bedrock" and paste your own
short-lived AWS STS session credentials in the sidebar (used only for that
session, never stored). All data shown is synthetic.
```

---

## URL to Optional Bonus Blog Post  (must be on builder.aws, title must include "Agents for Humans")

```
(paste the published builder.aws.com article URL here after you publish BUILDER_ARTICLE.md)
```
