# 🕯️ Necromancer: Ghost in the Machine

> **Resurrecting Dead Open-Source Repositories & Honoring Their Creators.**
> Built for the **DEV × Hacktoberfest 2026 "Ghost in the Machine" Challenge (Week 4)**.

Necromancer is an autonomous AI agent system designed to resurrect dormant open-source repositories (abandoned 5–10 years ago) using local open-weight LLMs, hardened sandboxes, and supply-chain auditing. When a resurrection succeeds, it generates an offline, commemorative HTML **"Ofrenda"** honoring the original contributors in the spirit of *Día de los Muertos*.

---

## 🔮 The 13 Architectural Pillars

1. **Séance Console:** Live terminal & web dashboard streaming agent thoughts, tool calls, and vital signs.
2. **Time-Machine Slider:** Interactive UI to inspect and pin legacy dependency versions over historical releases.
3. **Offline Ofrenda:** Standalone commemorative HTML page with high contrast, marigold aesthetics, and no external CDN dependencies.
4. **Hardened Sandbox:** Isolated Docker containers running with dropped capabilities (`cap_drop=ALL`), no new privileges, and memory/CPU quotas.
5. **Supply-Chain Guard:** Automated dependency hashing, vulnerability audits, and OSV scanning.
6. **Prompt-Injection Defense:** Untrusted code and build logs fenced in structured quotes; strict tool allowlist.
7. **Era Detection:** Parses commit dates to map legacy language runtimes and pin compatible dependencies without breaking modern tools.
8. **Failure Taxonomy Classifier:** Compact JSON summarizer translating verbose compiler/traceback dumps for small local models.
9. **Repo Map (tree-sitter):** AST symbol extractor (classes/methods) saving context tokens.
10. **Era-Level Caching:** Shared volume cache for legacy pip/npm artifacts.
11. **Model Router:** Routes simple syntax errors to small models (7B) and complex logic repairs to larger models (14B).
12. **Strategy Branches:** Dual resurrection modes: *"Pin the Past"* (legacy reproduction) vs. *"Port to Present"* (modern modernization).
13. **Test-Integrity Verification:** Invariant guard ensuring `tests_passed >= initial_test_count` before any build is certified.

---

## 🚀 Quickstart

### Prerequisites
* Python 3.10+
* Docker Desktop running locally
* Local Ollama or vLLM instance (e.g. `ollama run qwen2.5-coder:7b`)

### Installation
```bash
git clone https://github.com/YOUR_USERNAME/necromancer.git
cd necromancer
python -m venv .venv
source .venv/bin/activate  # Or on Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

---

## 🧪 Testing Phase 1

```bash
pytest tests/
```

---

## 📜 License
MIT License. Honoring open-source ancestors.
