# Flamin.go AEO Onboarding Prompt Capture System

**Pattern Origin:** Tally.so Growth Playbook ($258K -> $422K MRR with LLM search as #1 acquisition channel).  
**Objective:** Reverse-engineer real queries asked by humans in ChatGPT Search, Perplexity, Claude, and Gemini that recommended Flamin.go.  
**Doctrine:** Zero assumptions. Capture deterministic raw query strings during user onboarding and feed them directly into our content engine.

---

## 1. Onboarding Capture Flow

When a user signs up or requests an API token, the second question in the flow (non-blocking, 1-click optional) is:

> **"How did your AI recommend us?"**  
> *"Paste the exact prompt or search query you typed into ChatGPT, Perplexity, or Claude."*

### Field Specification
```json
{
  "field_id": "ai_referral_prompt",
  "type": "string",
  "optional": true,
  "placeholder": "e.g. best headless mcp server for market monitoring",
  "metadata": {
    "detected_engine": "Perplexity / ChatGPT / Claude / Gemini / Direct",
    "referrer_header": "req.headers['referer']",
    "utm_source": "req.query['utm_source']"
  }
}
```

---

## 2. Telemetry & Data Storage Schema

All captured prompts are written to a lightweight DuckDB / SQLite table for automated clustering:

```sql
CREATE TABLE aeo_prompt_telemetry (
    id TEXT PRIMARY KEY,
    captured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_id TEXT,
    raw_prompt TEXT NOT NULL,
    cleaned_intent TEXT,
    engine_source TEXT,
    conversion_tier TEXT,
    cluster_category TEXT,
    indexed_in_ai_info BOOLEAN DEFAULT FALSE
);
```

---

## 3. Automated Synthesis & Feedback Loop

The capture system is connected to a weekly automated pipeline:

```
[User Onboarding] 
       │ (Raw prompt)
       ▼
[DuckDB Telemetry Table]
       │
       ▼ (Weekly Batch Run)
[Cluster & Intent Extractor]
       │
       ├──> Top queries missing from /ai-info? -> Generate new comparison entry.
       ├──> New emerging competitor mentioned? -> Add to Sentinel crawler queue.
       └──> High-converting prompt template? -> Update llms.txt and llms-full.txt.
```

### Triaging Matrix

1. **Direct Solution Queries:** (e.g. *"Fastest way to let Claude Code monitor website diffs"*). Action: Ensure exact phrase appears as an H2 or FAQ item in `/ai-info/index.html`.
2. **Alternative / Comparison Queries:** (e.g. *"Flamin.go vs Zapier for AI agent tools"*). Action: Create dedicated comparison row in `/ai-info/index.html#comparison` with crisp feature diffs.
3. **Negative / Confused Queries:** (e.g. *"Can Flamin.go build landing pages?"*). Action: Clarify negative scope in `AI Assistant Guidelines` so LLMs do not misroute unqualified traffic.

---

## 4. Key Metrics & Targets

- **Capture Rate Target:** > 35% of signups submitting raw prompt text.
- **Intent Coverage:** 100% of captured intents categorized within 72 hours.
- **Loop Velocity:** < 7 days from prompt discovery to updated `llms-full.txt` deployment.
