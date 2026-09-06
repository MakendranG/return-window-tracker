# Demo Video Script — Return Window Tracker

**Target length:** ~3.5 minutes (hard cap is 5:00). Judges may stop watching at 5:00.
**Must cover (per rules):** (1) the problem, (2) who it's for, (3) why it matters — plus a working demo.
**Format:** screen recording + voiceover. No need to appear on camera.

**Setup before you hit record**
```
cd everyday/return-window-tracker
source .venv/bin/activate
export AWS_REGION=us-west-2
python generate_sample_data.py     # fresh dates
rm -f state.json                   # so run #1 shows items as "new"
```
Have these tabs/windows ready: the live Streamlit app, the GitHub repo, and
`agent.py` open in your editor. Increase your font size before recording.

---

## [0:00–0:25] Hook + the problem  🎯

> *(Screen: the Streamlit app hero, or a simple title slide.)*

"Every one of us buys things we end up needing to return — but retailers only
give you 15 to 30 days, and those deadlines are scattered across different
stores, emails, and receipts. So people lose real money, not because they didn't
want to return something, but because the window quietly closed while they
weren't looking.

That's the problem I set out to solve for the **Agents for Humans** hackathon,
Everyday Agents track."

## [0:25–0:45] What it is + who it's for  👥

"This is **Return Window Tracker** — an Everyday Agent built with the **Strands
Agents SDK** on **Amazon Bedrock**. It's for anyone juggling multiple purchases
and returns. The whole idea of an Everyday Agent is that it runs quietly in the
background, handles the routine stuff itself, and only pings you when there's a
real decision to make. That's exactly what this does."

## [0:45–1:15] The core idea — why it's trustworthy  🧠

> *(Screen: `agent.py`, scroll to the two `@tool` functions.)*

"Here's the key design decision. The deadline math and the 'do I bother the human'
decision are **deterministic Python tools** — `check_return_deadlines` and
`decide_autonomy`. The language model never does the math, because if it
miscalculates a deadline, you lose money. The LLM on Bedrock is used only for
what it's genuinely good at: writing the return messages and the digest. So the
numbers are auditable, and the writing is natural."

## [1:15–2:45] Live demo — the payoff  🖥️

> *(Screen: the live Streamlit app at return-window-tracker.streamlit.app.)*

"Let me show it. Here are a set of purchases across different stores. I click
**Run the agent**.

Instantly it reviewed everything and split it into two groups. On the right,
**four returns it auto-handled** — the message is already drafted and ready to
send, no decision needed from me.

On the left, **five items it's surfacing for me**, and notice *why* each one —
this one's high value at $249, this one's deadline is tomorrow, this one my
reason was uncertain, and this one already expired but it's defective, so it's
worth trying a goodwill exception. That's the agent making the judgment call
about what actually needs a human.

Every drafted message is right here — polite, references the item and date,
copy-and-paste ready.

And because it's a background agent, it remembers. If I run it again, the items
it already knew about are marked 'carried over' instead of new — so it only
re-nudges me when something actually changes."

> *(Optional 10s: switch the sidebar to "Live — Amazon Bedrock" to show the
> AI-drafted wording, if you have credentials configured.)*

## [2:45–3:15] How it's built  ☁️

> *(Screen: the architecture diagram — docs/architecture.png or ARCHITECTURE.md.)*

"Under the hood: the Strands agent runs its loop on Amazon Bedrock, calls the two
deterministic tools, then uses the model to draft — and returns a typed,
structured result. The same core runs three ways: this web UI, a command line,
and a Bedrock **AgentCore** runtime entrypoint. And anyone can try the live demo
with no AWS keys and no login, thanks to a built-in offline mode."

## [3:15–3:35] Why it matters + close  🙌

"Return Window Tracker takes a boring, money-losing chore completely off your
plate, and only interrupts you when your judgment genuinely matters. That, to me,
is what an Everyday Agent should be.

It's built with the Strands Agents SDK on Amazon Bedrock, it's open source under
MIT, and the live demo and code are linked below. Thanks for watching!"

---

## On-screen text / lower-thirds (optional but recommended)
- 0:00 — "Return Window Tracker · Agents for Humans · Everyday Agents"
- 0:45 — "Deterministic tools + LLM drafting"
- 1:15 — "Live demo"
- 3:15 — "Built with Strands Agents SDK on Amazon Bedrock"
- End card — the three links:
  - https://return-window-tracker.streamlit.app
  - https://makendrang.github.io/return-window-tracker/
  - https://github.com/MakendranG/return-window-tracker

## Recording checklist
- [ ] Font size bumped up; terminal/app full-screen
- [ ] Ran `rm -f state.json` so the first run shows "new" items, then re-run to show "carried over"
- [ ] Said "Strands Agents SDK" out loud and showed it on screen (judges check this)
- [ ] Covered problem → who → why → working demo
- [ ] Under 5:00 (aim ~3.5)
- [ ] Exported 1080p MP4, uploaded to YouTube as **Public or Unlisted** (never Private)

## Suggested YouTube title & description
**Title:** `Return Window Tracker — Agents for Humans (Everyday Agents) | Strands Agents SDK`

**Description:**
```
Return Window Tracker is an Everyday Agent built with the AWS Strands Agents SDK
on Amazon Bedrock. It tracks every purchase's return deadline, auto-drafts return
requests, and only surfaces the items that need a human decision.

Built With: Strands Agents SDK · Amazon Bedrock · Bedrock AgentCore
Live demo: https://return-window-tracker.streamlit.app
Code (MIT): https://github.com/MakendranG/return-window-tracker
All data shown is synthetic sample data.
```
