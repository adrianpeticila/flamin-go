#!/usr/bin/env python3
"""
test_server.py: Comprehensive Unit and Integration Test Suite for Flamin.go Server
Tests all 4 core tools, rate limiter tiers, FastMCP stdio protocol, and HTTP/SSE REST endpoints.

Zero em-dash compliant.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import threading
import time
import unittest
import urllib.request
from pathlib import Path

# Ensure repo and NYX are in path
REPO_DIR = Path(__file__).resolve().parent
NYX_ROOT = REPO_DIR.parent.parent / "NYX"
for p in [str(REPO_DIR), str(NYX_ROOT)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from server import (
    FlamingoHTTPRequestHandler,
    RateLimiter,
    StdioMCPServer,
    Tier,
    TIER_LIMITS,
    clean_document_to_markdown,
    execute_tool,
    record_decision_node,
    track_competitor_diff,
    verify_persona_isolation,
)


class TestCoreTools(unittest.TestCase):
    """Unit tests for the 4 core tools."""

    def test_01_track_competitor_diff(self) -> None:
        doc_v1 = """
        <html>
            <body>
                <h1>Product Pricing</h1>
                <p>Starter plan costs $29/mo.</p>
                <table>
                    <tr><th>Feature</th><th>Availability</th></tr>
                    <tr><td>API Access</td><td>Yes</td></tr>
                </table>
            </body>
        </html>
        """

        doc_v2 = """
        <html>
            <body>
                <h1>Product Pricing 2026</h1>
                <p>Starter plan costs $49/mo.</p>
                <p>Enterprise tier available on request.</p>
                <table>
                    <tr><th>Feature</th><th>Availability</th></tr>
                    <tr><td>API Access</td><td>Yes</td></tr>
                    <tr><td>Custom ML Models</td><td>Yes</td></tr>
                </table>
            </body>
        </html>
        """

        result = track_competitor_diff(source_a=doc_v1, source_b=doc_v2)
        self.assertEqual(result["status"], "success")
        summary = result["diff_summary"]
        self.assertGreater(summary["added_count"], 0)
        self.assertGreater(summary["removed_count"], 0)
        self.assertIn("unified_diff", result)
        self.assertIn("key_changes", result)

        # Check key changes extracted
        change_types = [c["type"] for c in result["key_changes"]]
        self.assertTrue(any("pricing" in t or "heading" in t for t in change_types))

    def test_02_clean_document_to_markdown(self) -> None:
        raw_html = """
        <html>
            <head><script>console.log('noise');</script></head>
            <body>
                <nav><a href="/home">Home</a></nav>
                <main>
                    <h2>System Overview</h2>
                    <p>Clean and dense extraction with <strong>zero overhead</strong>.</p>
                    <table>
                        <tr><th>Param</th><th>Value</th></tr>
                        <tr><td>Latency</td><td>12ms</td></tr>
                    </table>
                    <p>See <a href="https://flamin.go/docs">Docs</a> for more.</p>
                </main>
                <footer><p>Footer boilerplate</p></footer>
            </body>
        </html>
        """

        result = clean_document_to_markdown(raw_html)
        self.assertEqual(result["status"], "success")
        self.assertIn("## System Overview", result["markdown"])
        self.assertIn("| Latency | 12ms |", result["markdown"])
        self.assertNotIn("console.log", result["markdown"])
        self.assertNotIn("Footer boilerplate", result["markdown"])
        self.assertIn("https://flamin.go/docs", result["extracted_links"])
        self.assertGreater(result["compression_ratio"], 0)
        self.assertGreater(result["estimated_tokens"], 0)

    def test_03_record_decision_node(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_file = os.path.join(tmpdir, "test_decision_graph.json")

            # Node 1 (Root)
            r1 = record_decision_node(
                node_id="NODE-001",
                trigger="Competitor dropped price to $19",
                evidence="Diff detected price reduction on competitor landing page",
                decision="Hold price and emphasize sub-millisecond latency",
                action_taken="Updated landing page hero copy",
                storage_path=storage_file,
            )
            self.assertEqual(r1["status"], "success")
            self.assertEqual(r1["node"]["node_id"], "NODE-001")
            self.assertEqual(r1["provenance_chain_length"], 1)

            # Node 2 (Child)
            r2 = record_decision_node(
                node_id="NODE-002",
                trigger="Conversion rate increased by 14%",
                evidence="Posthog analytics 48h window",
                decision="Expand latency benchmarking campaign",
                action_taken="Published benchmark suite",
                parent_ids=["NODE-001"],
                storage_path=storage_file,
            )
            self.assertEqual(r2["status"], "success")
            self.assertEqual(r2["node"]["node_id"], "NODE-002")
            self.assertEqual(r2["provenance_chain_length"], 2)
            self.assertEqual(r2["total_graph_nodes"], 2)

    def test_04_verify_persona_isolation(self) -> None:
        # Valid clean text
        valid_res = verify_persona_isolation(
            text="Flamin.go provides high-throughput headless intelligence APIs.",
            brand="FLAMINGO",
        )
        self.assertTrue(valid_res["is_valid"])
        self.assertEqual(valid_res["violation_count"], 0)

        # Violation: prohibited personal string
        leak_res = verify_persona_isolation(
            text="Maintained by adrian peticila for testing.",
            brand="FLAMINGO",
        )
        self.assertFalse(leak_res["is_valid"])
        self.assertGreater(leak_res["violation_count"], 0)
        self.assertTrue(any(v["rule_name"] == "PROHIBITED_GLOBAL_STRING" for v in leak_res["violations"]))

        # Violation: API key leak
        key_res = verify_persona_isolation(
            text="Using token sk-1234567890abcdef1234567890 for API calls.",
            brand="FLAMINGO",
        )
        self.assertFalse(key_res["is_valid"])
        self.assertTrue(any(v["rule_name"] == "SECRET_PATTERN_LEAK" for v in key_res["violations"]))


class TestRateLimiter(unittest.TestCase):
    """Tests for tier enforcement and rate limiting."""

    def setUp(self) -> None:
        self.limiter = RateLimiter()

    def test_tier_limits_configuration(self) -> None:
        self.assertEqual(TIER_LIMITS[Tier.SOLO], 1000)
        self.assertEqual(TIER_LIMITS[Tier.FLEET], 25000)
        self.assertEqual(TIER_LIMITS[Tier.ENTERPRISE], 150000)

    def test_rate_limiting_quota_consumption(self) -> None:
        client_id = "test-client-solo"
        for i in range(10):
            allowed, info = self.limiter.check_and_consume(client_id, Tier.SOLO, estimated_tokens=50)
            self.assertTrue(allowed)
            self.assertEqual(info["calls_used"], i + 1)
            self.assertEqual(info["calls_remaining"], 1000 - (i + 1))
            self.assertEqual(info["tokens_used"], (i + 1) * 50)

        stats = self.limiter.get_stats(client_id)
        self.assertIsNotNone(stats)
        self.assertEqual(stats["calls_used"], 10)
        self.assertEqual(stats["tokens_used"], 500)

    def test_rate_limit_exceeded(self) -> None:
        client_id = "test-client-exhaust"
        # Artificially set calls_used to limit
        self.limiter._clients[client_id] = server_UsageStats(
            tier=Tier.SOLO,
            calls_used=1000,
            tokens_used=5000,
        )
        allowed, info = self.limiter.check_and_consume(client_id, Tier.SOLO)
        self.assertFalse(allowed)
        self.assertEqual(info["calls_remaining"], 0)
        self.assertIn("Rate limit exceeded", info["message"])


# Helper import for UsageStats in test
from server import UsageStats as server_UsageStats


class TestFastMCPProtocol(unittest.TestCase):
    """Tests for stdio JSON-RPC MCP implementation."""

    def setUp(self) -> None:
        self.limiter = RateLimiter()
        self.mcp = StdioMCPServer(rate_limiter=self.limiter)

    def test_initialize(self) -> None:
        req = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
        resp = self.mcp.handle_request(req)
        self.assertEqual(resp["id"], 1)
        self.assertEqual(resp["result"]["serverInfo"]["name"], "flamin.go-mcp")

    def test_tools_list(self) -> None:
        req = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
        resp = self.mcp.handle_request(req)
        tools = resp["result"]["tools"]
        tool_names = [t["name"] for t in tools]
        self.assertIn("track_competitor_diff", tool_names)
        self.assertIn("clean_document_to_markdown", tool_names)
        self.assertIn("record_decision_node", tool_names)
        self.assertIn("verify_persona_isolation", tool_names)

    def test_tools_call_clean_document(self) -> None:
        req = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "clean_document_to_markdown",
                "arguments": {"content": "<h1>Test Header</h1><p>Sample paragraph</p>"},
                "client_id": "stdio-tester",
                "tier": "solo",
            },
        }
        resp = self.mcp.handle_request(req)
        self.assertEqual(resp["id"], 3)
        self.assertFalse(resp["result"]["isError"])
        content_json = json.loads(resp["result"]["content"][0]["text"])
        self.assertEqual(content_json["status"], "success")
        self.assertIn("# Test Header", content_json["markdown"])

    def test_tools_call_record_decision(self) -> None:
        req = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "record_decision_node",
                "arguments": {
                    "node_id": "MCP-DEC-001",
                    "trigger": "Automated ingestion alert",
                    "evidence": "Payload size > 50kb",
                    "decision": "Split document into chunks",
                    "action_taken": "Executed map-reduce summarizer",
                },
                "client_id": "stdio-tester",
            },
        }
        resp = self.mcp.handle_request(req)
        self.assertEqual(resp["id"], 4)
        content_json = json.loads(resp["result"]["content"][0]["text"])
        self.assertEqual(content_json["status"], "success")
        self.assertEqual(content_json["node"]["node_id"], "MCP-DEC-001")


class TestHTTPServerIntegration(unittest.TestCase):
    """Integration tests for HTTP / REST and SSE server."""

    @classmethod
    def setUpClass(cls) -> None:
        import http.server
        import socket

        # Find free port
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(("127.0.0.1", 0))
        cls.port = sock.getsockname()[1]
        sock.close()

        cls.httpd = http.server.HTTPServer(("127.0.0.1", cls.port), FlamingoHTTPRequestHandler)
        cls.server_thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.server_thread.start()
        time.sleep(0.1)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def _url(self, path: str) -> str:
        return f"http://127.0.0.1:{self.port}{path}"

    def test_http_health(self) -> None:
        req = urllib.request.Request(self._url("/health"))
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data["status"], "ok")
            self.assertEqual(data["service"], "flamin.go-mcp")

    def test_http_tools_list(self) -> None:
        req = urllib.request.Request(self._url("/tools"))
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            self.assertIn("tools", data)
            self.assertIn("tiers", data)
            self.assertEqual(data["tiers"]["fleet"], 25000)

    def test_http_call_tool_endpoint(self) -> None:
        payload = json.dumps({
            "name": "verify_persona_isolation",
            "arguments": {"text": "Flamin.go headless intelligence platform", "brand": "FLAMINGO"},
        }).encode("utf-8")

        req = urllib.request.Request(
            self._url("/call"),
            data=payload,
            headers={
                "Content-Type": "application/json",
                "X-Client-ID": "http-tester-1",
                "X-Tier": "fleet",
            },
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data["status"], "success")
            self.assertTrue(data["is_valid"])
            self.assertIn("_quota", data)
            self.assertEqual(data["_quota"]["tier"], "fleet")

    def test_http_direct_tool_path(self) -> None:
        payload = json.dumps({
            "content": "<h1>Direct Endpoint</h1><p>Cleaned</p>",
            "preserve_tables": True,
        }).encode("utf-8")

        req = urllib.request.Request(
            self._url("/tools/clean_document_to_markdown"),
            data=payload,
            headers={"Content-Type": "application/json", "X-Client-ID": "http-tester-2"},
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data["status"], "success")
            self.assertIn("# Direct Endpoint", data["markdown"])

    def test_http_json_rpc(self) -> None:
        payload = json.dumps({
            "jsonrpc": "2.0",
            "id": 99,
            "method": "tools/list",
            "params": {},
        }).encode("utf-8")

        req = urllib.request.Request(
            self._url("/rpc"),
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data["id"], 99)
            self.assertEqual(len(data["result"]["tools"]), 4)

    def test_http_stats(self) -> None:
        req = urllib.request.Request(
            self._url("/stats"),
            headers={"X-Client-ID": "http-tester-1"},
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data["client_id"], "http-tester-1")
            self.assertGreater(data["calls_used"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
