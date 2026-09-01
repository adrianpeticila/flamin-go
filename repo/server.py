#!/usr/bin/env python3
"""
server.py: FastMCP and REST Server for Flamin.go
Pattern: Headless B2B Intelligence, Document Transformation, and Autonomous Provenance.

Exposes 4 Core Tools:
1. track_competitor_diff: Fetches/diffs competitor content with structured change extraction.
2. clean_document_to_markdown: Cleans DOM/HTML to dense LLM markdown (AnyDocCleaner).
3. record_decision_node: Logs deterministic causal provenance node (DecisionGraph).
4. verify_persona_isolation: Validates payload against cross-brand leakage (PersonaGuard).

Supports stdio MCP protocol and HTTP/SSE REST transport with multi-tier rate limiting.
Zero em-dash compliant.
"""

from __future__ import annotations

import argparse
import difflib
import http.server
import json
import os
from pathlib import Path
import re
import sys
import threading
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# Locate and import NYX core modules
CURRENT_DIR = Path(__file__).resolve().parent
NYX_ROOT = CURRENT_DIR.parent.parent / "NYX"
if str(NYX_ROOT) not in sys.path:
    sys.path.insert(0, str(NYX_ROOT))

try:
    from modules.anydoc_cleaner import AnyDocCleaner, CleanedDocument
    from modules.decision_graph import DecisionGraph, DecisionNode
    from modules.persona_guard import BrandDomain, IsolationViolation, PersonaGuard, ValidationReport
except ImportError:
    # Fallback to local import if executed inside modules directory
    from anydoc_cleaner import AnyDocCleaner, CleanedDocument
    from decision_graph import DecisionGraph, DecisionNode
    from persona_guard import BrandDomain, IsolationViolation, PersonaGuard, ValidationReport


# ============================================================================
# Tier Quota and Rate Limiting System
# ============================================================================

class Tier:
    SOLO = "solo"
    FLEET = "fleet"
    ENTERPRISE = "enterprise"


TIER_LIMITS: Dict[str, int] = {
    Tier.SOLO: 1000,
    Tier.FLEET: 25000,
    Tier.ENTERPRISE: 150000,
}


@dataclass
class UsageStats:
    tier: str
    calls_used: int = 0
    tokens_used: int = 0
    first_seen: float = field(default_factory=time.time)
    last_call: float = field(default_factory=time.time)


class RateLimiter:
    """
    In-memory rate limiter and token tracker with tier enforcement.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._clients: Dict[str, UsageStats] = {}

    def check_and_consume(
        self, client_id: str, tier: str = Tier.SOLO, estimated_tokens: int = 0
    ) -> Tuple[bool, Dict[str, Any]]:
        normalized_tier = tier.lower()
        call_limit = TIER_LIMITS.get(normalized_tier, TIER_LIMITS[Tier.SOLO])

        with self._lock:
            if client_id not in self._clients:
                self._clients[client_id] = UsageStats(tier=normalized_tier)

            stats = self._clients[client_id]
            # Update tier if changed
            stats.tier = normalized_tier

            if stats.calls_used >= call_limit:
                return False, {
                    "allowed": False,
                    "client_id": client_id,
                    "tier": normalized_tier,
                    "calls_used": stats.calls_used,
                    "call_limit": call_limit,
                    "calls_remaining": 0,
                    "tokens_used": stats.tokens_used,
                    "message": f"Rate limit exceeded for tier '{normalized_tier}' ({call_limit} calls).",
                }

            stats.calls_used += 1
            stats.tokens_used += estimated_tokens
            stats.last_call = time.time()

            return True, {
                "allowed": True,
                "client_id": client_id,
                "tier": normalized_tier,
                "calls_used": stats.calls_used,
                "call_limit": call_limit,
                "calls_remaining": call_limit - stats.calls_used,
                "tokens_used": stats.tokens_used,
            }

    def get_stats(self, client_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            stats = self._clients.get(client_id)
            if not stats:
                return None
            call_limit = TIER_LIMITS.get(stats.tier, TIER_LIMITS[Tier.SOLO])
            return {
                "client_id": client_id,
                "tier": stats.tier,
                "calls_used": stats.calls_used,
                "call_limit": call_limit,
                "calls_remaining": max(0, call_limit - stats.calls_used),
                "tokens_used": stats.tokens_used,
                "first_seen": stats.first_seen,
                "last_call": stats.last_call,
            }

    def reset(self, client_id: Optional[str] = None) -> None:
        with self._lock:
            if client_id:
                self._clients.pop(client_id, None)
            else:
                self._clients.clear()


# Global rate limiter instance
RATE_LIMITER = RateLimiter()


# ============================================================================
# Core Tool Implementations
# ============================================================================

def _fetch_url(url: str, timeout: int = 10) -> str:
    """Helper to fetch raw HTML from a URL."""
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Flamin.go Competitive Intelligence Bot)"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        content_bytes = resp.read()
        charset = resp.headers.get_content_charset() or "utf-8"
        return content_bytes.decode(charset, errors="replace")


def track_competitor_diff(
    source_a: str,
    source_b: str,
    is_url: bool = False,
    label_a: str = "baseline",
    label_b: str = "target",
) -> Dict[str, Any]:
    """
    Fetches and sanitizes two pages/documents, computes structured markdown diffs,
    and extracts semantic pricing, feature, and heading changes.
    """
    cleaner = AnyDocCleaner()

    raw_a = _fetch_url(source_a) if is_url else source_a
    raw_b = _fetch_url(source_b) if is_url else source_b

    doc_a = cleaner.clean_html(raw_a)
    doc_b = cleaner.clean_html(raw_b)

    lines_a = doc_a.markdown.splitlines()
    lines_b = doc_b.markdown.splitlines()

    diff_generator = difflib.unified_diff(
        lines_a,
        lines_b,
        fromfile=label_a,
        tofile=label_b,
        lineterm="",
    )
    diff_lines = list(diff_generator)

    added_lines: List[str] = []
    removed_lines: List[str] = []
    for line in diff_lines:
        if line.startswith("+") and not line.startswith("+++"):
            added_lines.append(line[1:].strip())
        elif line.startswith("-") and not line.startswith("---"):
            removed_lines.append(line[1:].strip())

    # Detect high-signal changes (pricing, headers, tables)
    key_changes: List[Dict[str, Any]] = []
    price_pattern = re.compile(r"(\$\d+(?:\.\d+)?|\b\d+\s*(?:USD|EUR|GBP|RON)\b)", re.IGNORECASE)

    for add in added_lines:
        if price_pattern.search(add):
            key_changes.append({"type": "pricing_added", "content": add})
        elif add.startswith("#"):
            key_changes.append({"type": "heading_added", "content": add})
        elif add.startswith("|"):
            key_changes.append({"type": "table_row_added", "content": add})

    for rem in removed_lines:
        if price_pattern.search(rem):
            key_changes.append({"type": "pricing_removed", "content": rem})
        elif rem.startswith("#"):
            key_changes.append({"type": "heading_removed", "content": rem})

    return {
        "status": "success",
        "diff_summary": {
            "added_count": len(added_lines),
            "removed_count": len(removed_lines),
            "total_modifications": len(added_lines) + len(removed_lines),
            "source_a_tokens": doc_a.estimated_tokens,
            "source_b_tokens": doc_b.estimated_tokens,
        },
        "key_changes": key_changes,
        "unified_diff": "\n".join(diff_lines),
        "source_a_cleaned": doc_a.markdown,
        "source_b_cleaned": doc_b.markdown,
    }


def clean_document_to_markdown(
    content: str,
    is_url: bool = False,
    preserve_tables: bool = True,
) -> Dict[str, Any]:
    """
    Converts messy HTML/DOM or text into dense, LLM-ready markdown.
    """
    cleaner = AnyDocCleaner()
    raw_content = _fetch_url(content) if is_url else content
    doc: CleanedDocument = cleaner.clean_html(raw_content, preserve_tables=preserve_tables)

    return {
        "status": "success",
        "markdown": doc.markdown,
        "raw_char_count": doc.raw_char_count,
        "cleaned_char_count": doc.cleaned_char_count,
        "compression_ratio": doc.compression_ratio,
        "estimated_tokens": doc.estimated_tokens,
        "extracted_links": doc.extracted_links,
    }


def record_decision_node(
    node_id: str,
    trigger: str,
    evidence: str,
    decision: str,
    action_taken: str,
    parent_ids: Optional[List[str]] = None,
    outcome: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    storage_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Records an immutable, causal provenance node into the local decision DAG.
    """
    graph = DecisionGraph(storage_path=storage_path)
    node: DecisionNode = graph.add_decision(
        node_id=node_id,
        trigger=trigger,
        evidence=evidence,
        decision=decision,
        action_taken=action_taken,
        parent_ids=parent_ids or [],
        outcome=outcome,
        metadata=metadata or {},
    )

    provenance_chain = graph.trace_provenance(node_id)
    return {
        "status": "success",
        "node": asdict(node),
        "node_hash": node.node_hash,
        "provenance_chain_length": len(provenance_chain),
        "total_graph_nodes": len(graph.nodes),
    }


def verify_persona_isolation(
    text: str,
    brand: str = "FLAMINGO",
) -> Dict[str, Any]:
    """
    Validates text against brand isolation and cross-leak boundaries.
    """
    guard = PersonaGuard()
    try:
        brand_enum = BrandDomain(brand.upper())
    except ValueError:
        brand_enum = BrandDomain.FLAMINGO

    report: ValidationReport = guard.validate_payload(text, brand_enum)
    violations_data = [
        {
            "rule_name": v.rule_name,
            "severity": v.severity,
            "matched_text": v.matched_text,
            "description": v.description,
        }
        for v in report.violations
    ]

    return {
        "status": "success",
        "is_valid": report.is_valid,
        "brand": report.brand.value,
        "violations": violations_data,
        "violation_count": len(violations_data),
    }


# ============================================================================
# Tool Registry & JSON Schema for MCP
# ============================================================================

TOOL_DEFINITIONS = [
    {
        "name": "track_competitor_diff",
        "description": "Fetches and cleans two document versions, computing structured diffs and extracting key changes.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "source_a": {"type": "string", "description": "Baseline HTML text or URL"},
                "source_b": {"type": "string", "description": "Target HTML text or URL"},
                "is_url": {"type": "boolean", "description": "Whether inputs are URLs", "default": False},
                "label_a": {"type": "string", "description": "Label for source A", "default": "baseline"},
                "label_b": {"type": "string", "description": "Label for source B", "default": "target"},
            },
            "required": ["source_a", "source_b"],
        },
    },
    {
        "name": "clean_document_to_markdown",
        "description": "Converts raw HTML/DOM into dense, LLM-ready markdown with tables and links preserved.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "Raw HTML string or URL to clean"},
                "is_url": {"type": "boolean", "description": "Whether content is a URL", "default": False},
                "preserve_tables": {"type": "boolean", "description": "Whether to convert HTML tables to markdown", "default": True},
            },
            "required": ["content"],
        },
    },
    {
        "name": "record_decision_node",
        "description": "Logs an immutable deterministic causal decision node into the decision graph DAG.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node_id": {"type": "string", "description": "Unique identifier for this decision node"},
                "trigger": {"type": "string", "description": "External condition or event triggering decision"},
                "evidence": {"type": "string", "description": "Facts, diffs, or metrics used as foundation"},
                "decision": {"type": "string", "description": "Conclusion reached by reasoning process"},
                "action_taken": {"type": "string", "description": "Concrete action executed"},
                "parent_ids": {"type": "array", "items": {"type": "string"}, "description": "List of parent node IDs"},
                "outcome": {"type": "string", "description": "Observed result of the action"},
                "metadata": {"type": "object", "description": "Optional arbitrary metadata dict"},
                "storage_path": {"type": "string", "description": "Optional file path to persist JSON graph"},
            },
            "required": ["node_id", "trigger", "evidence", "decision", "action_taken"],
        },
    },
    {
        "name": "verify_persona_isolation",
        "description": "Validates text against brand cross-leakage and protected personal identity leakage.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Content string to validate"},
                "brand": {"type": "string", "description": "Brand domain to enforce", "default": "FLAMINGO"},
            },
            "required": ["text"],
        },
    },
]


def execute_tool(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Dispatch tool execution with parameter mapping."""
    if name == "track_competitor_diff":
        return track_competitor_diff(
            source_a=arguments.get("source_a", ""),
            source_b=arguments.get("source_b", ""),
            is_url=arguments.get("is_url", False),
            label_a=arguments.get("label_a", "baseline"),
            label_b=arguments.get("label_b", "target"),
        )
    elif name == "clean_document_to_markdown":
        return clean_document_to_markdown(
            content=arguments.get("content", ""),
            is_url=arguments.get("is_url", False),
            preserve_tables=arguments.get("preserve_tables", True),
        )
    elif name == "record_decision_node":
        return record_decision_node(
            node_id=arguments.get("node_id", ""),
            trigger=arguments.get("trigger", ""),
            evidence=arguments.get("evidence", ""),
            decision=arguments.get("decision", ""),
            action_taken=arguments.get("action_taken", ""),
            parent_ids=arguments.get("parent_ids"),
            outcome=arguments.get("outcome"),
            metadata=arguments.get("metadata"),
            storage_path=arguments.get("storage_path"),
        )
    elif name == "verify_persona_isolation":
        return verify_persona_isolation(
            text=arguments.get("text", ""),
            brand=arguments.get("brand", "FLAMINGO"),
        )
    else:
        raise ValueError(f"Unknown tool: {name}")


# ============================================================================
# FastMCP stdio Protocol Handler
# ============================================================================

class StdioMCPServer:
    """
    Standard MCP JSON-RPC protocol server running on stdio.
    """

    def __init__(self, rate_limiter: Optional[RateLimiter] = None) -> None:
        self.rate_limiter = rate_limiter or RATE_LIMITER

    def handle_request(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        msg_id = request.get("id")
        method = request.get("method")
        params = request.get("params", {})

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {
                        "name": "flamin.go-mcp",
                        "version": "1.0.0",
                    },
                    "capabilities": {
                        "tools": {"listChanged": False},
                    },
                },
            }

        elif method == "notifications/initialized":
            return None

        elif method == "ping":
            return {"jsonrpc": "2.0", "id": msg_id, "result": {}}

        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {"tools": TOOL_DEFINITIONS},
            }

        elif method == "tools/call":
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})
            client_id = params.get("client_id", "stdio-default")
            tier = params.get("tier", Tier.SOLO)

            allowed, quota_info = self.rate_limiter.check_and_consume(client_id, tier)
            if not allowed:
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {
                        "code": -32000,
                        "message": quota_info.get("message", "Rate limit exceeded"),
                        "data": quota_info,
                    },
                }

            try:
                result = execute_tool(tool_name, tool_args)
                result["_quota"] = quota_info
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [
                            {"type": "text", "text": json.dumps(result, indent=2)}
                        ],
                        "isError": False,
                    },
                }
            except Exception as e:
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {
                        "code": -32603,
                        "message": str(e),
                    },
                }

        else:
            if msg_id is not None:
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {"code": -32601, "message": f"Method '{method}' not found"},
                }
            return None

    def run(self) -> None:
        """Reads JSON-RPC from stdin line by line and writes to stdout."""
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                request = json.loads(line)
                response = self.handle_request(request)
                if response is not None:
                    sys.stdout.write(json.dumps(response) + "\n")
                    sys.stdout.flush()
            except json.JSONDecodeError:
                err_resp = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32700, "message": "Parse error"},
                }
                sys.stdout.write(json.dumps(err_resp) + "\n")
                sys.stdout.flush()


# ============================================================================
# HTTP & SSE REST Server
# ============================================================================

class FlamingoHTTPRequestHandler(http.server.BaseHTTPRequestHandler):
    """
    HTTP/REST and SSE Handler for Flamin.go endpoints.
    """

    server_version = "FlamingoServer/1.0"

    def _send_json(self, status_code: int, data: Any) -> None:
        body = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Client-ID, X-Tier")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Client-ID, X-Tier")
        self.end_headers()

    def do_GET(self) -> None:
        parsed_path = self.path.split("?")[0]

        if parsed_path == "/health":
            self._send_json(200, {
                "status": "ok",
                "service": "flamin.go-mcp",
                "version": "1.0.0",
                "timestamp": time.time(),
            })

        elif parsed_path == "/tools":
            self._send_json(200, {
                "tools": TOOL_DEFINITIONS,
                "tiers": {
                    Tier.SOLO: TIER_LIMITS[Tier.SOLO],
                    Tier.FLEET: TIER_LIMITS[Tier.FLEET],
                    Tier.ENTERPRISE: TIER_LIMITS[Tier.ENTERPRISE],
                },
            })

        elif parsed_path == "/stats":
            client_id = self.headers.get("X-Client-ID", "anonymous")
            stats = RATE_LIMITER.get_stats(client_id)
            if stats:
                self._send_json(200, stats)
            else:
                self._send_json(200, {"client_id": client_id, "status": "no_usage_recorded"})

        elif parsed_path == "/sse":
            # Server-Sent Events Endpoint
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            endpoint_event = f"event: endpoint\ndata: /rpc\n\n"
            self.wfile.write(endpoint_event.encode("utf-8"))
            self.wfile.flush()

        else:
            self._send_json(404, {"error": "Not Found", "path": parsed_path})

    def do_POST(self) -> None:
        parsed_path = self.path.split("?")[0]
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        try:
            payload = json.loads(body.decode("utf-8")) if body else {}
        except json.JSONDecodeError:
            self._send_json(400, {"error": "Invalid JSON in request body"})
            return

        client_id = self.headers.get("X-Client-ID", payload.get("client_id", "default-http"))
        tier = self.headers.get("X-Tier", payload.get("tier", Tier.SOLO))

        if parsed_path == "/rpc":
            # JSON-RPC endpoint
            server = StdioMCPServer()
            if "params" in payload and isinstance(payload["params"], dict):
                payload["params"].setdefault("client_id", client_id)
                payload["params"].setdefault("tier", tier)
            response = server.handle_request(payload)
            self._send_json(200 if "error" not in (response or {}) else 400, response or {})

        elif parsed_path.startswith("/tools/"):
            tool_name = parsed_path[len("/tools/"):]
            allowed, quota_info = RATE_LIMITER.check_and_consume(client_id, tier)
            if not allowed:
                self._send_json(429, quota_info)
                return

            try:
                result = execute_tool(tool_name, payload)
                result["_quota"] = quota_info
                self._send_json(200, result)
            except ValueError as e:
                self._send_json(404, {"error": str(e)})
            except Exception as e:
                self._send_json(500, {"error": str(e)})

        elif parsed_path == "/call":
            tool_name = payload.get("name")
            arguments = payload.get("arguments", {})
            if not tool_name:
                self._send_json(400, {"error": "Missing 'name' field in payload"})
                return

            allowed, quota_info = RATE_LIMITER.check_and_consume(client_id, tier)
            if not allowed:
                self._send_json(429, quota_info)
                return

            try:
                result = execute_tool(tool_name, arguments)
                result["_quota"] = quota_info
                self._send_json(200, result)
            except Exception as e:
                self._send_json(500, {"error": str(e)})

        else:
            self._send_json(404, {"error": "Not Found", "path": parsed_path})

    def log_message(self, format: str, *args: Any) -> None:
        """Suppress default stderr logging for quiet test execution."""
        if os.environ.get("FLAMINGO_DEBUG"):
            super().log_message(format, *args)


def start_http_server(host: str = "127.0.0.1", port: int = 8080) -> http.server.HTTPServer:
    server = http.server.HTTPServer((host, port), FlamingoHTTPRequestHandler)
    print(f"[*] Flamin.go FastMCP HTTP server running on http://{host}:{port}")
    return server


# ============================================================================
# Main Entrypoint
# ============================================================================

def main() -> None:
    parser = argparse.ArgumentParser(description="Flamin.go FastMCP & REST Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="stdio",
        help="Transport mode: stdio (MCP default) or http (REST / SSE)",
    )
    parser.add_argument("--host", default="127.0.0.1", help="HTTP host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8080, help="HTTP port (default: 8080)")
    args = parser.parse_args()

    if args.transport == "stdio":
        server = StdioMCPServer()
        server.run()
    else:
        httpd = start_http_server(args.host, args.port)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[*] Shutting down Flamin.go server.")
            httpd.server_close()


if __name__ == "__main__":
    main()
