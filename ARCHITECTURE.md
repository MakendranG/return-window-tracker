# Architecture

Return Window Tracker is a single **Strands Agents SDK** agent
(`return_tracker_agent`) with **two deterministic custom tools**, an LLM drafting
layer, background memory, and typed structured output.

The diagram below maps to the five elements judges look for: **user
input/interface**, **Strands agent + agentic loop**, **tools & integrations**,
**AWS services**, and **output**.

```mermaid
flowchart TB
    subgraph UI["1 · User Input / Interface"]
        A["CLI: python main.py<br/>reads sample_data/purchases.json"]
    end

    subgraph AGENT["2 · Strands Agent — return_tracker_agent (agentic loop)"]
        direction TB
        R["Model reasoning<br/>(Amazon Bedrock — Claude Sonnet)"]
        R --> T1["3 · @tool check_return_deadlines<br/>(deterministic: deadline, days_left, status)"]
        T1 --> T2["3 · @tool decide_autonomy<br/>(deterministic: AUTO_HANDLED vs NEEDS_YOU)"]
        T2 --> D["LLM drafting layer<br/>return-request messages + prioritized digest"]
        D --> SO["Strands structured_output<br/>→ typed Pydantic TrackerResult"]
    end

    subgraph AWS["4 · AWS Services"]
        BR["Amazon Bedrock<br/>(foundation model runtime)"]
    end

    subgraph MEM["Background Memory"]
        ST["state.json<br/>(remembers what was already surfaced)"]
    end

    subgraph OUT["5 · Output"]
        O1["Clean console digest<br/>(NEEDS YOU → AUTO-HANDLED → no action)"]
        O2["Structured JSON<br/>(digest + typed per-item records)"]
    end

    A --> AGENT
    R <-.->|invoke model| BR
    AGENT --> ST
    ST -.->|prior run state| AGENT
    AGENT --> O1
    AGENT --> O2
```

## Flow explained

The user runs the CLI, which loads their purchases and hands them to the Strands
`return_tracker_agent`. The agent's system prompt requires it to first call the
deterministic `check_return_deadlines` tool (all date math and status
classification) and then `decide_autonomy` (the deterministic escalation policy
that decides what the agent can safely auto-handle versus what a human must
weigh in on) — so every number and every escalation decision is auditable Python,
never LLM guesswork. The agent (running on **Amazon Bedrock**) then uses the LLM
only for drafting the natural-language return-request messages and the
human-readable digest, and Strands **structured output** coerces the final answer
into a typed `TrackerResult`. A small `state.json` gives the agent background
memory across runs, so it behaves like a quiet background service that only
re-surfaces what is genuinely new or newly urgent, and the CLI prints both a
clean console digest and machine-readable JSON.

## Why split deterministic tools vs. LLM?

- **`check_return_deadlines`** owns correctness-critical math: deadlines,
  days-left, and status. Testable and reproducible.
- **`decide_autonomy`** owns the escalation policy: whether to act autonomously
  or surface for a human. Predictable and auditable — the core "Everyday Agent"
  behavior of *"make the safe calls on its own, only ping a human when it
  matters."*
- **LLM layer** owns natural language: polite, contextual return-request messages
  and a readable digest, always reusing the tools' exact numbers.
- **Structured output** guarantees the machine-readable result is well-typed
  rather than fragile hand-written JSON.
