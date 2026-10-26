# 🕯️ Necromancer: Ghost in the Machine

> **Resurrecting Dead Open-Source Repositories & Honoring Their Creators.**  
> Built for the **DEV × Hacktoberfest 2026 "Ghost in the Machine" Challenge (Week 4)**.  
> Target Portal: **[necromancer.shivysidinfo.tech](https://necromancer.shivysidinfo.tech)**

---

## 🔮 What is Necromancer?

Necromancer is an autonomous AI agent system designed to exhume and resurrect dormant open-source repositories (abandoned 5–10 years ago) using local open-weight LLMs (vLLM / Ollama), a hardened Docker sandbox, and supply-chain auditing.

When a repository is resurrected and passes 100% of its test invariants, Necromancer synthesizes a spoken eulogy via **ElevenLabs Voice AI**, monitors full agent latency & token spans via **Sentry**, and renders an offline commemorative HTML **"Ofrenda"** honoring the original authors in the spirit of *Día de los Muertos*.

---

## 🏛️ The 13 Architectural Pillars

1. **Séance Console:** Real-time WebSocket terminal & dashboard streaming agent thoughts, tool calls, and vital signs.
2. **Time-Machine Slider:** Interactive component to scrub between vintage release years and modern dependencies.
3. **Offline Standalone Ofrenda:** Single self-contained HTML memorial with embedded base64 audio and zero external CDN scripts.
4. **Hardened Docker Sandbox:** Ephemeral isolated containers running with dropped capabilities (`cap_drop=ALL`), `no-new-privileges`, CPU/memory quotas, and read-only host mounts.
5. **Supply-Chain Guard:** Automated dependency hashing, vulnerability audits, and retro mirror pinning.
6. **Prompt-Injection Defense:** Untrusted code and compiler outputs fenced in structured JSON contracts with strict tool allowlists.
7. **Era Detection:** Parses commit timestamps (2008–2026) to map runtime matrices (Python 2.7 Sunset, Python 3.5 Transition, Mature 3.8, Modern 3.10+).
8. **Failure Taxonomy Classifier:** Regex & AST engine compressing thousands of lines of compiler/pytest output into dense, token-frugal JSON digests for local LLMs.
9. **Repo Map AST Blueprint:** Compressed symbol extractor discovering classes, methods, docstrings, and entrypoints.
10. **Era-Level Caching:** Shared volume cache for historical pip/npm wheels.
11. **Model Router:** Routes simple syntax conversions to fast models (7B) and complex architecture fixes to larger reasoning models (14B).
12. **Strategy Branches:** Dual resurrection modes: *"Pin the Past"* (legacy reproduction) vs. *"Port to Present"* (contemporary modernization).
13. **Strict Test-Integrity Verification:** Mathematical invariant enforcement guaranteeing `tests_passed >= initial_test_count` and rejecting test deletions or mocks.

---

## 🤝 Targeted Event Partners

* **ElevenLabs:** Narrates commemorative audio eulogies celebrating original project creators.
* **Sentry:** Captures end-to-end agent execution transactions, model token usage, and sandbox diagnostics (`o4512324247683072.ingest.de.sentry.io`).
* **.tech Domains:** Hosted live portal at `necromancer.shivysidinfo.tech`.
* **Render:** Cloud hosting for web services and WebSocket séance daemon.

---

## 🚀 Quickstart

### Prerequisites
* Python 3.10+
* Docker Desktop running locally
* Local Ollama instance (e.g. `ollama run qwen2.5-coder:7b`)

### Installation & Launch
```bash
git clone https://github.com/satanic47/necromancer.git
cd necromancer
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Start local server
uvicorn app.main:app --reload --port 8000
```
Open [http://localhost:8000](http://localhost:8000) to access the **Séance Console**.

---

## 🧪 Comprehensive Verification Suite (89 Tests)

Necromancer includes an exhaustive 89-unit-test suite validating every phase:

```bash
python -m pytest tests/ -v
```

```
============================= 89 passed in 4.22s ==============================
- tests/test_phase1.py: 28 tests (Pytest/Unittest parsers, sandbox security, integrity invariants)
- tests/test_phase2.py: 30 tests (Era detector 2008-2026, failure taxonomy, AST repo mapper)
- tests/test_phase3.py: 16 tests (Agent orchestration, strategy branches, cheat rejection)
- tests/test_phase4.py: 15 tests (ElevenLabs eulogy, standalone HTML Ofrenda, FastAPI endpoints)
```

---

## 🌐 Deploy to Render with .tech Domain

### 1. Render Blueprint Deploy
This repository includes a `render.yaml` blueprint. Link this GitHub repository in Render:
1. Log in to [dashboard.render.com](https://dashboard.render.com).
2. Click **New +** $\to$ **Blueprint**.
3. Select `satanic47/necromancer` and click **Apply**.

### 2. DNS Configuration on .tech Dashboard
To point `necromancer.shivysidinfo.tech` to your Render service:
1. Open your **.tech Domain Control Panel** (or Cloudflare/Registrar managing `shivysidinfo.tech`).
2. Navigate to **DNS Management / DNS Records**.
3. Add a **CNAME** record:
   * **Type:** `CNAME`
   * **Host / Name:** `necromancer` (or `necromancer.shivysidinfo.tech`)
   * **Target / Value:** `<your-render-service-name>.onrender.com` (from your Render service dashboard)
   * **TTL:** `Automatic` (or `300` / `1 Hour`)
4. In Render: Go to your service **Settings** $\to$ **Custom Domains** $\to$ add `necromancer.shivysidinfo.tech`. Render automatically provisions an SSL/TLS certificate.
