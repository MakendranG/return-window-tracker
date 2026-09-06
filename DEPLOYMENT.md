# Deployment Guide — Return Window Tracker

This project has three deployment targets. You can do any of them independently:

1. **Streamlit Community Cloud** — the live, interactive public demo (runs the Python agent).
2. **GitHub Pages** — a static landing page that links to the demo.
3. **Amazon Bedrock AgentCore Runtime** — an optional hosted HTTP endpoint for the agent.

> No secrets appear in this document. Anywhere credentials are needed, placeholders are shown.

---

## 1. Streamlit Community Cloud (the live public demo)

This hosts `app.py` as a running Python app so visitors can interact with the Strands agent.

### Prerequisites
- A **public GitHub repo** — already published at <https://github.com/MakendranG/return-window-tracker>.
- A **Streamlit Community Cloud** account at <https://share.streamlit.io>, signed in **with GitHub** (so it can read the repo).
- **Amazon Bedrock model access enabled** in the AWS account/region you will use (see Secrets below).

### Steps
1. Go to <https://share.streamlit.io> and click **New app** → **Deploy a public app from GitHub**.
2. Fill in:
   - **Repository:** `MakendranG/return-window-tracker`
   - **Branch:** `master`
   - **Main file path:** `app.py`
3. Open **Advanced settings** and set:
   - **Python version:** `3.12`

   > ⚠️ **Do NOT choose Python 3.13 or 3.14.** Some dependencies do not yet
   > build/resolve cleanly on those versions. Use **3.12**.

### Secrets (AWS credentials for Bedrock)
Still in **Advanced settings**, paste the following into the **Secrets** box.
Secrets use **TOML** format. Replace every placeholder with your own values:

```toml
AWS_ACCESS_KEY_ID = "YOUR_ACCESS_KEY_ID"
AWS_SECRET_ACCESS_KEY = "YOUR_SECRET_ACCESS_KEY"
AWS_REGION = "us-west-2"

# Optional:
# AWS_SESSION_TOKEN = "YOUR_SESSION_TOKEN"   # only if using temporary/STS creds
# STRANDS_MODEL_ID = "YOUR_BEDROCK_MODEL_ID" # override the default Bedrock model
```

**How this works:** `app.py` reads Streamlit's `st.secrets` and copies the
recognized keys into `os.environ` **before** the agent (and its Bedrock client)
is imported. `boto3`/Bedrock then pick up the credentials from those environment
variables automatically. It also keeps `AWS_REGION` and `AWS_DEFAULT_REGION` in
sync. Locally (no secrets file) this is a harmless no-op.

**Security — use least privilege:** Create a **scoped IAM user** whose only
permission is `bedrock:InvokeModel`, and use *those* keys here. Do **not** use
account root or admin/full-access keys. Example minimal policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "bedrock:InvokeModel",
      "Resource": "*"
    }
  ]
}
```

### Deploy & result
1. Click **Deploy**. First build takes a couple of minutes.
2. Your app gets a public URL following the pattern:

   ```text
   https://<app-name>.streamlit.app
   ```

> Reminder: the app can only call Bedrock if **model access is enabled** in the
> same AWS account **and** region (`us-west-2`) your secrets point to.

---

## 2. GitHub Pages (static landing page)

The landing page lives in **`docs/index.html`**. GitHub Pages serves it as a
static site.

### Steps
1. In the GitHub repo, go to **Settings → Pages**.
2. Under **Build and deployment → Source**, choose **Deploy from a branch**.
3. Set:
   - **Branch:** `master`
   - **Folder:** `/docs`
4. Click **Save**.

### Result
- Live at (note the **lowercase** URL):

  ```text
  https://makendrang.github.io/return-window-tracker/
  ```
- It may take **1–2 minutes** to go live after saving.

> **What Pages can and cannot do:** GitHub Pages serves **static files only**.
> This landing page simply **links to the live Streamlit demo and the video** —
> it **cannot run the Python agent** itself. For the interactive experience,
> use the Streamlit URL from Section 1.

---

## 3. Amazon Bedrock AgentCore Runtime (optional)

Hosts the agent as a managed HTTP service on AWS. Optional, but it strengthens
the **Technical Implementation** story.

### What's in the repo
- **`agentcore_app.py`** — the entrypoint. It creates a `BedrockAgentCoreApp`,
  registers `@app.entrypoint def invoke(payload)`, and (via `app.run()`) exposes
  the standard **`/invocations`** (POST) and **`/ping`** (GET) HTTP routes. It
  reuses the same agent core from `agent.py` — no logic is duplicated.
- **`requirements-agentcore.txt`** — the lean runtime dependency list (Streamlit
  UI deps intentionally excluded).

> ✅ This repo has already **verified the entrypoint locally**: `/ping` returns
> **200**, and `/invocations` returns the structured result.

### Local test
```bash
# Terminal 1 — start the local server (listens on :8080)
python agentcore_app.py
```

```bash
# Terminal 2 — exercise the endpoints
curl -X POST http://localhost:8080/invocations \
  -H 'Content-Type: application/json' \
  -d '{"purchases":[]}'

curl http://localhost:8080/ping
```

An empty `purchases` list makes the endpoint fall back to synthetic sample data,
so it is demoable out of the box.

### Deploy with the AgentCore CLI
```bash
# Runtime library
pip install bedrock-agentcore

# Recommended AgentCore CLI
npm install -g @aws/agentcore
```

```bash
# Configure the deployment
agentcore configure \
  -e agentcore_app.py \
  -n returnwindowtracker \
  -rf requirements-agentcore.txt
```

When prompted, choose:
- **Direct Code Deploy**
- **Python 3.12**
- **Auto-create** the execution role **and** the S3 bucket

```bash
# Build & deploy to AgentCore Runtime
agentcore deploy

# Invoke the deployed agent
agentcore invoke
```

### Requirements & cost
- AWS credentials with permissions for **Bedrock**, **AgentCore**, and
  **IAM / ECR / S3 / CodeBuild** (used to build and host the runtime).
- **This incurs AWS costs** (build + hosting + model invocation). Tear down
  resources you no longer need.
