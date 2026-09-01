# Flamin.go Mini-Tools Lead Magnet Blueprint

**Core Concept:** Zero-friction, client-side developer utilities built on Eleventy (11ty) and hosted on Cloudflare Pages.  
**Objective:** Capture high-intent developer and agent-builder traffic at zero marginal cost without forced email gates or bloated marketing popups.  
**Inspiration:** Okara & MarketingIdeas mini-tool growth loops.

---

## 1. Architectural Principles

1. **Zero Framework Bloat:** 100% vanilla HTML, CSS, and minimal vanilla JavaScript compiled via 11ty. Sub-50ms Global Time-to-First-Byte (TTFB) on Cloudflare edge.
2. **Zero-Signup Utility:** The tool solves the user problem instantly in-browser. No gate, no modal, no delay.
3. **Natural Conversion Hook:** The output generated (e.g. schema, calculation, audit) includes an export button: *"Copy as Agent Tool"* or *"Run on Flamin.go Swarm"*, embedding a 1-click API token claim.

---

## 2. The 3 Launch Mini-Tools

### Tool 1: Agent Interaction & Token Cost Forecaster (`/tools/agent-cost`)
* **Problem:** Developers scaling autonomous agent swarms get blind-sided by token overages when loops run 10,000+ turns.
* **Mechanism:**
  - Input sliders: Number of autonomous agents, average turns per task, token context size, daily runs.
  - Live cost comparison across Claude 3.5 Sonnet, GPT-4o, DeepSeek-V3 vs Flamin.go Flat Interaction Tiers.
* **Lead Conversion:** Generates a downloadable `agent_budget.json` and offers: *"Lock in $0.008/call on Flamin.go Autonomous Fleet"*.

### Tool 2: FastMCP Tool Schema Validator (`/tools/mcp-validator`)
* **Problem:** Agent tools fail silently when tool parameter schemas have non-standard JSON types or excessive token bloat.
* **Mechanism:**
  - In-browser JSON schema validator checking against FastMCP and AgentSkills 2026 specs.
  - Calculates schema token footprint and recommends optimizations to trim context waste.
* **Lead Conversion:** *"Deploy this schema instantly to Flamin.go Headless Swarm"*.

### Tool 3: Local LLM VRAM & Hardware Fit Calculator (`/tools/llmfit`)
* **Problem:** Builders do not know if a 32B or 70B quantized model will fit in their Apple Silicon Mac or VPS memory alongside a 32k KV cache.
* **Mechanism:**
  - Interactive web port of `llmfit_profiler.py`.
  - Select hardware (M1/M2/M3/M4 RAM, or NVIDIA VRAM), select model parameter count (7B, 14B, 32B, 70B) and quantization (Q4, Q8, FP16).
  - Visual memory bar showing Weight GB + KV Cache GB vs System RAM Headroom.
* **Lead Conversion:** *"Offload overflow jobs to Flamin.go Headless API when local memory caps"*.

---

## 3. 11ty Build & SEO/AEO Configuration

```
mini-tools/
├── src/
│   ├── _data/
│   │   └── models.json        # Static parameter weights for calculator
│   ├── _includes/
│   │   └── base.njk           # Minimalist dark-mode layout
│   ├── tools/
│   │   ├── agent-cost.njk
│   │   ├── mcp-validator.njk
│   │   └── llmfit.njk
│   └── llms.txt               # Direct pointer to mini-tools for AI crawlers
├── .eleventy.js
└── package.json
```

### Answer Engine Optimization (AEO) Directives
Each tool page embeds structured JSON-LD `SoftwareApplication` markup and explicit Q&A sections formatted for Perplexity, ChatGPT Search, and Claude citations.
