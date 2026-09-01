# FLAMIN.GO MASTER CONTEXT & PRODUCT ARCHITECTURE

**Status:** ACTIVE ARCHITECTURE & REVENUE ENGINE (2026-2027) - Ready for Sunday evening execution.
**Classification:** Headless Autonomous Intelligence & Monetization Platform  
**Entity Isolation:** Crimson Venus SRL (B2B Infrastructure, Headless API, Enterprise Licenses) / Strict Anonymous Sub-Nodes (Micro-SaaS, Visual Generators)  
**Execution Standard:** OPUS_DOCTRINE (Zero fluff, verified root cause, deterministic code, zero em-dash)  

---

## 1. PRODUCT VISION: HEADLESS AGENT API + OPERATOR UI

Flamin.go is an autonomous intelligence and revenue execution engine built for the post-GUI era. Most enterprise software forces human operators to click through bloated dashboards. Flamin.go reverses the paradigm:

1. **Headless-First (Agent Interface):** Native MCP (Model Context Protocol) server and lightweight REST API designed for autonomous AI agents (Claude Code, Cursor, Codex, OpenClaw, custom LangGraph swarms). Agents discover capabilities via `/llms.txt`, inspect schemas via `/llms-full.txt`, and execute jobs without rendering HTML.
2. **Operator Cockpit (Human Interface):** A brutalist, ultra-fast dashboard for configuration, kill-switches, financial telemetry, and edge-case human-in-the-loop approvals.

### Core Value Proposition
- Turn manual workflows into deterministic agent tools.
- Monitor competitors, scrape unstructured market data, and orchestrate revenue funnels asynchronously.
- Bill agents where they consume value: programmatic interaction caps, not seat licenses.

---

## 2. DUAL-INTERFACE ARCHITECTURE

```
+-------------------------------------------------------------------------+
|                           FLAMIN.GO CORE                                |
|   - Deterministic Decision Engine (Semantica DAG)                       |
|   - Identity Isolation Boundary (PersonaGuard)                          |
|   - Headless Task Queue & Ingestion Pipeline                            |
+------------------------------------+------------------------------------+
| [HEADLESS AGENT TIER]              | [OPERATOR COCKPIT TIER]            |
| - FastMCP / Stream Server          | - Serverless Edge UI (Cloudflare)  |
| - REST OpenAPI Endpoints           | - Real-time SSE Log Stream         |
| - Machine-readable llms.txt        | - Budget & Usage Kill Switches     |
| - Structured JSON Outputs          | - Visual Causal Decision Explorer  |
+------------------------------------+------------------------------------+
```

### Agent Integration Stack
- **Standard Discovery:** Root `/llms.txt` and `/ai-info` endpoints formatted specifically for LLM search indexing and engine retrieval.
- **Protocol:** FastMCP over stdio and SSE for seamless integration into agent IDEs.
- **Payload Sanitization:** Firecrawl-style document extraction into pristine markdown without DOM clutter or tracker noise.

---

## 3. PRICING TIERS: INTERACTION CAPS & CONSUMPTION

Traditional SaaS charges per human seat. Flamin.go charges per agent interaction cap and autonomous job throughput:

| Tier | Base Price | Target Audience | Agent Interaction Cap | Included Capabilities | Overage Rate |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Solo Operator** | $29 / mo | Solo devs, indie hackers | 1,000 tool calls / mo | Operator UI, 1 Agent MCP token, Standard rate limits | $0.03 / call |
| **Autonomous Fleet** | $199 / mo | Growth teams, boutique agencies | 25,000 tool calls / mo | Full Headless API, 5 Concurrent Agent Workers, Webhooks, Sentinel Crawler | $0.01 / call |
| **Enterprise Swarm** | $799 / mo | High-volume ops, scaleups | 150,000 tool calls / mo | Dedicated proxy rotation, Custom MCP tools, Priority SLA, Decision Graph Audit trails | $0.005 / call |

*Note on Interaction Definition:* An interaction is defined as one atomic tool execution or structured endpoint resolution. Internal retries due to provider timeouts do not consume quota.

---

## 4. GO-TO-MARKET (GTM) PLAYBOOK

Flamin.go rejects bloated enterprise sales cycles. Distribution relies on deterministic inbound engines and viral technical artifacts:

1. **AEO Dominance (Answer Engine Optimization):**
   - Public `/ai-info` and `/llms-full.txt` structured specifically for ChatGPT Search, Perplexity, and Claude citations.
   - Onboarding reverse-prompt capture to continuously mine queries that convert.
2. **Praise-Led Outreach Campaigns:**
   - Programmatic curation of "Top 50 Agentic Workflows / AI Tools" badges.
   - Reaching out to tool builders with technical breakdowns, earning backlinks and social endorsements without cold spamming.
3. **Mini-Tools Lead Magnets:**
   - 11ty-powered zero-latency micro-utilities (e.g. Prompt Cost Forecaster, MCP Schema Validator, Token-to-VRAM Calculator).
   - Zero signup barrier for basic use; one-click upgrade to Headless API token.
4. **Agent ROI Wrapped (Viral Data Bomb):**
   - Shareable visual cards generated monthly showing autonomous hours saved, compute efficiency ratios, and dollar-per-task metrics.

---

## 5. STRICT BRAND & IDENTITY ISOLATION

Every deployment follows the isolation boundaries defined in `CONSTITUTION.md`:
- **Entity:** Commercial software licensing and API services operate strictly under Crimson Venus SRL.
- **Air-Gap:** No personal developer credentials or internal monorepo identifiers leaked into client-facing artifacts or public endpoints.
- **Zero Fluff:** All documentation, logs, and interfaces must remain concise, technical, and free of generic AI promotional filler.

---

## 6. CURRENT STATUS & NEXT STEPS (21 Aug 2026)

**Current Status (S326):**
- NYX Command OS Dashboard app created and native macOS bundle compiled.
- Overlap bug diagnosed and cleanly unified into 8 isolated tabs.
- 9,216 files synced into `nyx_vault_data.json`.
- Jarvis protocol codified in `AGENT_COORDINATION.md` Rule 12.

**Next Steps Ready for Execution:**
1. Monitor autonomous agent telemetry via the new NYX Dashboard tabs.
2. Finalize pricing endpoint logic for the Headless API.
3. Deploy initial AEO landing pages for Flamin.go using 11ty.

- Newly operational modules: b2a_gateway.py and agent_shopper.py.
