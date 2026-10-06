# Flamin.go // The B2A Intelligence Toolkit for Solopreneurs & Micro-SaaS

> Turn raw market signals and competitor gaps into automated customer acquisition pipelines. Zero enterprise bloat. Built for indie founders.

Live Platform: [https://flamin-go.pages.dev](https://flamin-go.pages.dev)  
Full LLM Documentation: [https://flamin-go.pages.dev/llms-full.txt](https://flamin-go.pages.dev/llms-full.txt)  
WebMCP / FastMCP Specs: [https://flamin-go.pages.dev/api/catalog.json](https://flamin-go.pages.dev/api/catalog.json)

---

## Overview & Architecture

Flamin.go is an autonomous B2A (Business-to-Agent) intelligence and revenue execution engine designed for solopreneurs, bootstrappers, and micro-SaaS operators. It eliminates manual competitor monitoring, messy document parsing, and fragmented agent actions by providing deterministic FastMCP servers, REST endpoints, and machine-to-machine commerce rails.

```
┌─────────────────────────────────────────────────────────────┐
│                       Agent Operator                        │
│             (Claude, Antigravity, Cursor, CLI)              │
└──────────────────────────────┬──────────────────────────────┘
                               │ FastMCP / REST Bearer Auth
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                    Flamin.go Edge Gateway                   │
│   - Competitor Sentinel (DOM & Pricing Diffing)             │
│   - Anydoc Cleaner (HTML/PDF to Context Markdown)           │
│   - Decision Graph (Causal DAG Provenance Tracking)         │
│   - Persona Guard (Brand Boundary & Leak Interceptor)       │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                   M2M Agentic Commerce                      │
│   - Programmatic Catalog (/api/catalog.json)                │
│   - HTTP 402 Settlement Rails (Stripe Hosted & x402)        │
│   - Tokenized Deliverables (/api/agent/deliveries/{token})  │
└─────────────────────────────────────────────────────────────┘
```

---

## Core Capabilities & FastMCP Tools

Flamin.go exposes its core capabilities through FastMCP and WebMCP standard interfaces:

### 1. `track_competitor_diff`
Monitors target URLs, extracts DOM diffs, analyzes positioning shifts, and generates executive teardowns.
- **Parameters**: `target_url` (string), `comparison_baseline_id` (optional string), `extract_pricing` (boolean).
- **Output**: Structured positioning change vectors and pricing adjustments.

### 2. `clean_document_to_markdown`
Sanitizes messy HTML, PDF, or Word documents into clean, LLM-ready markdown optimized for prompt context windows.
- **Parameters**: `source_content` (string), `content_type` (html/pdf/docx), `strip_navigation` (boolean).
- **Output**: Clean markdown and token count estimate.

### 3. `record_decision_node`
Appends a deterministic decision node to the causal provenance DAG for multi-agent workflows.
- **Parameters**: `node_id` (string), `trigger_event` (string), `reasoning` (string), `action_taken` (string).
- **Output**: Graph node confirmation and timestamp.

### 4. `verify_persona_isolation`
Validates outbound payloads against cross-brand contamination and identity leakage before external delivery.
- **Parameters**: `brand_context` (string), `outbound_payload` (string).
- **Output**: Validation boolean and violation details.

---

## M2M Agentic Commerce & Pricing

| Tier | Price | Interactions | Access Mode |
| :--- | :--- | :--- | :--- |
| **Indie CLI / Free** | **$0** | Unlimited local | Self-hosted CLI & MCP |
| **Studio Pack** | **$49 one-time** | Full tool matrix | Stripe Hosted / x402 |
| **Autonomous Fleet** | **$199/month** | 25,000 calls | Programmatic API key |

- **Catalog Endpoint**: `https://flamin-go.pages.dev/api/catalog.json`
- **Purchase Gateway**: `POST https://flamin-go.pages.dev/api/agent/buy`
- **Settlement Rails**: Dual-rail architecture supporting standard Stripe hosted checkout and native HTTP 402 micropayment headers.

---

## Installation & CLI Usage

### Requirements
- Node.js >= 18
- Python >= 3.10

### Setup
Clone the repository and install dependencies:
```bash
git clone https://github.com/adrianpeticila/flamin-go.git
cd flamin-go
npm install
pip install -r requirements.txt
```

### Direct Agent Integration
Start the FastMCP / WebMCP server:
```bash
python server.py
# or
npm run mcp-server
```

---

## Production Rules

- **Zero Corporate Slop**: Pure signal. No marketing jargon or ungrounded claims.
- **High Contrast**: Minimalist, accessible visual tokens.
- **Strict Brand Isolation**: Identity boundaries are enforced mechanically at the protocol layer.

---

## License

MIT License. Built by Adrian M. Peticila.
