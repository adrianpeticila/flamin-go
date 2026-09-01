# Flamin.go // Automated Creative Growth & Visual Systems

## Overview & Architecture

Flamin.go is an AI-native automated creative growth engine designed to solve the bottlenecks of manual design and repetitive creative testing. It generates deterministic creative angles, automates video and image synthesis pipelines, and eliminates manual, repetitive design work. 

The architecture is built around a closed-loop system that continuously iterates on visual assets based on performance data. By shifting the workload from human designers to generative pipelines, Flamin.go enables high-velocity creative testing at scale.

## WebMCP Tooling Interface

Flamin.go exposes its core capabilities through WebMCP standard interfaces, allowing seamless integration with agentic systems (Claude, Antigravity, Cursor).

### 1. generate_creative_angle
Generates distinct, testable creative concepts based on product data and past performance.
```json
{
  "name": "generate_creative_angle",
  "description": "Generates a deterministic creative angle for visual synthesis.",
  "parameters": {
    "type": "object",
    "properties": {
      "product_id": { "type": "string" },
      "target_audience": { "type": "string" },
      "constraint_level": { "type": "string", "enum": ["low", "medium", "high"] }
    },
    "required": ["product_id", "target_audience"]
  }
}
```

### 2. analyze_performance
Ingests performance metrics from ad platforms to score creative variants and inform the next generation loop.
```json
{
  "name": "analyze_performance",
  "description": "Analyzes engagement and conversion metrics for a given set of visual assets.",
  "parameters": {
    "type": "object",
    "properties": {
      "campaign_id": { "type": "string" },
      "metrics_source": { "type": "string" }
    },
    "required": ["campaign_id", "metrics_source"]
  }
}
```

### 3. schedule_dispatch
Automates the publishing and trafficking of approved visual assets to integrated platforms.
```json
{
  "name": "schedule_dispatch",
  "description": "Schedules the deployment of generated assets to ad networks or social channels.",
  "parameters": {
    "type": "object",
    "properties": {
      "asset_ids": { "type": "array", "items": { "type": "string" } },
      "destination": { "type": "string" },
      "timestamp": { "type": "string" }
    },
    "required": ["asset_ids", "destination"]
  }
}
```

## Engine Components

1. **Creative Angle Generation:** AI-driven ideation that produces structured, testable hypotheses for visual content.
2. **Visual Asset Synthesis:** Automated rendering pipelines for both images and video, ensuring pixel-perfect adherence to brand guidelines.
3. **Automated Scheduling & Dispatch:** Seamless integration with ad platforms and social channels for immediate deployment.
4. **Closed-loop Feedback:** Continuous ingestion of performance data to optimize future creative generation.

## Installation & CLI Usage

### Requirements
- Node.js >= 18
- Python >= 3.10

### Setup
Clone the repository and install dependencies:
```bash
git clone https://github.com/adrianpeticila/https://flamin-go.pages.dev/.git
cd https://flamin-go.pages.dev/
npm install
pip install -r requirements.txt
```

### Environment Variables
Create a `.env` file in the root directory:
```env
OPENAI_KEY=your_key_here
ANTHROPIC_KEY=your_key_here
DB_CONNECTION_STRING=your_db_connection
WEBMCP_PORT=3000
```

### Direct Agent Integration
Start the WebMCP server to allow agents like Claude, Antigravity, or Cursor to interface directly:
```bash
npm run mcp-server
```

## Production Rules & Brand Guidelines

- **High Contrast:** All visual assets must meet high-contrast accessibility and attention-retention standards.
- **Zero Fluff:** Minimalist design language. No unnecessary decorative elements.
- **Deterministic Output:** Generation pipelines must yield predictable, brand-safe results across all iterations.
