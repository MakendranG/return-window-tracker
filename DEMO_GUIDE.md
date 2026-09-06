# Demo & Video Guide — Return Window Tracker

Everything you need to record the Agents for Humans submission video (max 5 min)
and to share the live environment. This file is a helper for you; you don't have
to commit it.

Repo: https://github.com/MakendranG/return-window-tracker

--------------------------------------------------------------------------------
## 1. One-time prep before recording
--------------------------------------------------------------------------------

```bash
cd everyday/return-window-tracker
source .venv/bin/activate
export AWS_REGION=us-west-2          # or your Bedrock region
python generate_sample_data.py       # fresh dates relative to today
rm -f state.json                     # so run #1 shows everything as new
```

Terminal tips for a clean recording:
- Increase font size (judges watch small).
- Clear scrollback (`clear`) before each command.
- Full-screen the terminal; hide anything with secrets.

--------------------------------------------------------------------------------
## 2. Exact commands to show (in order)
--------------------------------------------------------------------------------

1. Show the code structure (10s):
   `ls` then open `agent.py`, scroll to `@tool check_return_deadlines` and
   `@tool decide_autonomy`.

2. First live run — everything is new:
   `python main.py --fresh`
   Point at: "5 need your decision · 4 handled automatically", the NEEDS YOU
   block with different escalation reasons, and a drafted return message.

3. Second run — background memory:
   `python main.py`
   Point at: items now say "Carried over from a previous run" (not 🆕). This is
   the "quiet background agent" behavior.

4. (Optional) Structured JSON:
   `python main.py --json-only | head -40`
   Point at: typed fields status / autonomy / escalation_reason / draft_message.

5. Show the architecture diagram: open `ARCHITECTURE.md` on GitHub (Mermaid
   renders automatically) and the MIT license in the repo About section.

--------------------------------------------------------------------------------
## 3. Narration script (~3.5 min — under the 5-min cap)
--------------------------------------------------------------------------------

[0:00–0:30] THE PROBLEM
"Retailers give you 15 to 30 days to return something. People lose real money
every year not because they didn't want to return an item, but because the
deadline quietly passed — the receipts are scattered across stores and email and
nobody's tracking them. This is Return Window Tracker, an Everyday Agent built
with the Strands Agents SDK that fixes exactly that."

[0:30–0:55] WHO IT'S FOR
"It's for anyone juggling multiple purchases and returns across different stores.
The goal isn't another app to babysit — it's an agent that runs in the
background, handles the routine returns itself, and only pings you when there's a
real decision to make."

[0:55–1:40] HOW IT'S BUILT (show agent.py)
"It's a genuine Strands agent with two deterministic Python tools. The first,
check_return_deadlines, does all the date math — deadline, days left, and status.
The second, decide_autonomy, decides what the agent can safely handle on its own
versus what needs you. All of that is auditable Python — never LLM guesswork. The
language model is used only for what it's good at: drafting the return messages
and the daily digest. And the final result comes back as typed structured
output."

[1:40–3:00] LIVE DEMO (run it)
"Let me run it. It reviewed 13 purchases: four it handled automatically, five it
surfaced for me. Look at why each one needs me — this one's high value, this
one's due tomorrow, this one my reason was uncertain, and this one already
expired but it's defective so it's worth a goodwill request. For the automatic
ones, the return message is already drafted and ready to send. Now watch — I run
it again, and the items it already knew about are marked 'carried over,' not new.
It remembers across runs, so it only re-nudges me when something actually
changes."

[3:00–3:30] WHY IT MATTERS + CLOSE
"That's the whole idea of an Everyday Agent: it takes a boring, money-losing
chore completely off your plate and only interrupts you when your judgment
genuinely matters. Built with the Strands Agents SDK on Amazon Bedrock. The code,
with an MIT license and full setup instructions, is on GitHub. Thanks for
watching."

--------------------------------------------------------------------------------
## 4. Recording tools
--------------------------------------------------------------------------------

- Screen + voice: OBS Studio (free, Win/Mac/Linux), QuickTime (Mac), or Loom.
- Keep it under 5:00. Aim for ~3.5–4:00.
- Export 1080p MP4.

--------------------------------------------------------------------------------
## 5. Upload to YouTube
--------------------------------------------------------------------------------

1. youtube.com → Create → Upload video → select your MP4.
2. Title: `Return Window Tracker — Agents for Humans (Everyday Agents) | Strands Agents SDK`
3. Visibility: **Unlisted** or **Public** (Devpost needs it publicly viewable —
   Unlisted is fine and keeps it off search). Do NOT use Private.
4. Description (paste):
   ```
   Return Window Tracker is an Everyday Agent built with the AWS Strands Agents
   SDK. It tracks every purchase's return deadline, auto-drafts return-request
   messages, and only surfaces items that need a human decision.

   Built With: Strands Agents SDK on Amazon Bedrock.
   Code (MIT): https://github.com/MakendranG/return-window-tracker
   All data shown is synthetic sample data.
   ```
5. Copy the video URL for the Devpost submission form.

--------------------------------------------------------------------------------
## 6. Sharing the "live environment"
--------------------------------------------------------------------------------

This is a CLI agent, so a "live demo link" can be one of:

- **Simplest (recommended for a CLI):** the GitHub repo IS the shareable
  artifact — anyone can `git clone`, add AWS creds, and run it. The README has
  cold-start setup. On Devpost, you can put the repo URL as the demo link.
- **Recorded terminal you can share as a link:** use asciinema
  (`asciinema rec demo.cast` then `asciinema upload demo.cast`) — gives a
  shareable URL of the exact terminal session. Great "live-feel" without hosting.
- **Fully hosted (optional, more work):** deploy the agent behind a tiny
  FastAPI endpoint on AWS Lambda or App Runner and expose a `/digest` route.
  Strands documents deployment to AgentCore / Lambda / App Runner. Only do this
  if you have time; it boosts the Technical Implementation score but isn't
  required.

--------------------------------------------------------------------------------
## 7. Final submission checklist (Devpost)
--------------------------------------------------------------------------------

- [ ] Text description (problem, who, how) — name "Strands Agents SDK" explicitly
- [ ] Public repo URL: https://github.com/MakendranG/return-window-tracker
- [ ] MIT license visible in About  ✅ (already detected by GitHub)
- [ ] README + ARCHITECTURE diagram  ✅ (in repo)
- [ ] Demo video URL (YouTube, <5 min)
- [ ] AWS Builder ID (the email you registered with)
- [ ] Track: Everyday Agents
- [ ] (Bonus) builder.aws.com post with "Agents for Humans" in the title
```
