# Flamin.go // Automated Creative Growth & Visual Workflows

AI-native visual automation engine for brand growth, content generation, and dynamic creative assets.

## Overview
Flamin.go is built for modern marketing teams, portfolio operators, and digital creators looking to scale their visual production automatically. It integrates seamlessly into your creative operations.

## WebMCP Tooling Interface
The engine relies on a standard WebMCP spec that exposes these core tools:

- **generate_creative_angle** : Crafts specialized visual positioning strategies.
- **analyze_performance** : Measures impact and provides actionable metrics on visual output.
- **schedule_dispatch** : Orchestrates dynamic asset publication and rotation.

*(Check out `flamingo_webmcp.json` for the complete specification).*

## Usage Guide & API Integration

### Setup
1. Clone this repository locally.
2. Initialize the WebMCP server pointing to your instance URL.

### API Integration
Use the exposed tools through standard MCP JSON-RPC calls.

Example:
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "call_tool",
  "params": {
    "name": "generate_creative_angle",
    "arguments": {
      "brand_identity": "bold_tech",
      "target_audience": "b2b_executives"
    }
  }
}
```

Connect your favorite AI agent or automated script to the local MCP runtime to enable fully autonomous visual workflows.
