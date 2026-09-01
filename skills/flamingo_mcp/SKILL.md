---
name: flamingo-mcp
description: Model Context Protocol (MCP) tool integration for the Flamin.go autonomous intelligence engine. Enables agents to track competitors, parse documents, trace causal decision graphs, and manage async funnels.
---

# Flamingo MCP Skill

## Overview

The `flamingo-mcp` skill connects autonomous agents directly to the Flamin.go headless backend. It provides deterministic tools for market intelligence, document-to-markdown extraction, and causal graph auditing without requiring web browser automation or human dashboard interaction.

## Environment & Configuration

To configure the skill, set the following environment variable in your agent environment or `.env` file:

```bash
export FLAMINGO_API_KEY="flm_live_xxxxxxxxxxxxxxxxxxxxxxxx"
export FLAMINGO_ENDPOINT="https://api.flamin.go/v1"
```

## Available Tools

### 1. `flamingo_competitor_diff`
Tracks positioning changes, pricing shifts, and new feature announcements on competitor web assets.

**Parameters:**
- `target_url` (string, required): The URL to monitor.
- `comparison_baseline_id` (string, optional): ID of previous snapshot.
- `extract_pricing` (boolean, default: true): Extract structured pricing.

**Example Agent Usage:**
```json
{
  "target_url": "https://competitor.com/pricing",
  "extract_pricing": true
}
```

### 2. `flamingo_anydoc_cleaner`
Cleans raw HTML, PDF, or Word inputs into token-dense, zero-noise markdown.

**Parameters:**
- `source_content` (string, required): Raw text or HTML markup.
- `preserve_tables` (boolean, default: true): Retain markdown table structures.

**Example Agent Usage:**
```json
{
  "source_content": "<html><body><nav>Ignore</nav><main><h1>Title</h1><p>Content</p></main></body></html>",
  "preserve_tables": true
}
```

### 3. `flamingo_decision_node`
Logs an agent decision to the Semantica-style deterministic DAG for causal audit trails.

**Parameters:**
- `node_id` (string, required): Unique identifier for this decision.
- `parent_node_ids` (array of strings, optional): Parent nodes in the causal DAG.
- `trigger_event` (string, required): What prompted this decision.
- `reasoning` (string, required): Root causal justification.
- `action_taken` (string, required): Exact code change, API call, or file written.

### 4. `flamingo_persona_guard`
Validates outbound communication against brand leakage and identity rules.

**Parameters:**
- `brand_context` (string, required): Target brand name (e.g. `FLAMINGO`, `ZERO_HYPE`).
- `outbound_payload` (string, required): The text to be verified before sending.

## Safety & Rate Limiting Guidelines

1. **Deterministic Execution:** Always inspect returned JSON status fields before chaining subsequent tool calls.
2. **Quota Awareness:** Check the `interaction_quota_remaining` header to avoid unexpected throttle events.
3. **No Fluff:** Do not summarize raw JSON unless explicitly requested by the operator. Return structured outputs directly.
