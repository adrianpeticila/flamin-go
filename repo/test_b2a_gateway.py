#!/usr/bin/env python3
"""
test_b2a_gateway.py: Comprehensive Unit and Integration Test Suite for Flamin.go B2A Paywall
Tests HTTP 402 challenge flow, L402 headers, Base network challenge nonce generation,
replay prevention, expired/malformed nonce defense, and AgentShopper client SDK.

Zero em-dash compliant.
"""

from __future__ import annotations

import base64
import json
import os
import sys
import threading
import time
import unittest
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

# Add repo to sys.path
REPO_DIR = Path(__file__).resolve().parent
if str(REPO_DIR) not in sys.path:
    sys.path.insert(0, str(REPO_DIR))

from b2a_gateway import (
    B2AGateway,
    ChallengeManager,
    DEFAULT_CURRENCY,
    DEFAULT_NETWORK,
    DEFAULT_VAULT_ADDRESS,
    PaymentVerifier,
    ReplayGuard,
    create_fastapi_app,
    start_native_server,
)
from agent_shopper import AgentShopper


class TestB2AGatewayCore(unittest.TestCase):
    """Core unit tests for B2A gateway logic, challenge generation, and payment validation."""

    def setUp(self) -> None:
        self.gateway = B2AGateway(secret_key="test-secret-key-12345", ttl_seconds=60)

    def test_01_health_and_pricing(self) -> None:
        # Health check
        code, _, data = self.gateway.handle_request("GET", "/health", {})
        self.assertEqual(code, 200)
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["service"], "flamin.go-b2a-gateway")

        # Pricing catalog
        code, _, pricing = self.gateway.handle_request("GET", "/api/b2a/pricing", {})
        self.assertEqual(code, 200)
        self.assertEqual(pricing["network"], DEFAULT_NETWORK)
        self.assertEqual(pricing["currency"], DEFAULT_CURRENCY)
        self.assertEqual(len(pricing["endpoints"]), 2)

    def test_02_initial_request_returns_http_402_brand_tokens(self) -> None:
        """Initial unauthenticated request must return HTTP 402 with RFC L402 headers and challenge."""
        code, headers, body = self.gateway.handle_request(
            method="GET",
            path="/api/b2a/brand-tokens",
            headers={},
            query_params={"brand": "FLAMINGO"},
        )

        self.assertEqual(code, 402)
        self.assertIn("WWW-Authenticate", headers)
        self.assertTrue(headers["WWW-Authenticate"].startswith("L402 "))
        self.assertEqual(headers.get("X-Payment-Required"), "L402")
        self.assertEqual(headers.get("X-Network"), "base")
        self.assertEqual(headers.get("X-Price-Amount"), "0.05")
        self.assertEqual(headers.get("X-Price-Currency"), "USDC")
        self.assertIn("X-Challenge-Nonce", headers)

        self.assertEqual(body["status"], "payment_required")
        self.assertEqual(body["code"], 402)
        self.assertIn("payment", body)
        payment = body["payment"]
        self.assertEqual(payment["scheme"], "L402")
        self.assertEqual(payment["network"], "base")
        self.assertEqual(payment["currency"], "USDC")
        self.assertEqual(payment["amount"], 0.05)
        self.assertIn("challenge_nonce", payment)
        self.assertIn("expires_at", payment)
        self.assertIn("macaroon", payment)
        self.assertIn("invoice", payment)

    def test_03_initial_request_returns_http_402_teardown(self) -> None:
        """Initial unauthenticated request to /api/b2a/teardown must return HTTP 402 with 0.10 USDC price."""
        code, headers, body = self.gateway.handle_request(
            method="POST",
            path="/api/b2a/teardown",
            headers={},
            body_data={"target": "competitor.io"},
        )

        self.assertEqual(code, 402)
        self.assertEqual(headers.get("X-Price-Amount"), "0.10")
        self.assertEqual(body["payment"]["amount"], 0.10)

    def test_04_valid_payment_voucher_brand_tokens_returns_200(self) -> None:
        """Providing a valid payment voucher and challenge nonce must return HTTP 200 with dense JSON."""
        # 1. Obtain challenge
        _, challenge_headers, _ = self.gateway.handle_request("GET", "/api/b2a/brand-tokens", {})
        nonce = challenge_headers["X-Challenge-Nonce"]
        voucher = "vch_tx_base_testvoucher1234567890"

        # 2. Submit payment
        auth_headers = {
            "authorization": f"L402 {nonce}:{voucher}",
            "x-payment-voucher": voucher,
            "x-payment-nonce": nonce,
        }
        code, headers, body = self.gateway.handle_request(
            method="GET",
            path="/api/b2a/brand-tokens",
            headers=auth_headers,
            query_params={"brand": "FLAMINGO"},
        )

        self.assertEqual(code, 200)
        self.assertEqual(headers.get("X-Payment-Settled"), "true")
        self.assertEqual(headers.get("X-Settlement-Voucher"), voucher)
        self.assertEqual(body["status"], "success")
        self.assertEqual(body["brand"], "FLAMINGO")
        self.assertIn("intelligence", body)
        self.assertIn("brand_tokens", body["intelligence"])
        self.assertGreater(len(body["intelligence"]["brand_tokens"]), 0)
        self.assertIn("_payment_receipt", body)

    def test_05_valid_payment_voucher_teardown_returns_200(self) -> None:
        """Providing a valid payment voucher for teardown must return HTTP 200 with dense analysis."""
        # 1. Obtain challenge
        _, challenge_headers, _ = self.gateway.handle_request("POST", "/api/b2a/teardown", {})
        nonce = challenge_headers["X-Challenge-Nonce"]
        voucher = "vch_tx_base_teardown_voucher_998877"

        # 2. Submit payment
        auth_headers = {
            "authorization": f'L402 nonce="{nonce}", voucher="{voucher}"',
        }
        code, headers, body = self.gateway.handle_request(
            method="POST",
            path="/api/b2a/teardown",
            headers=auth_headers,
            body_data={"target": "acme-corp.com"},
        )

        self.assertEqual(code, 200)
        self.assertEqual(body["status"], "success")
        self.assertEqual(body["target"], "acme-corp.com")
        self.assertIn("teardown", body)
        self.assertIn("feature_matrix", body["teardown"])
        self.assertIn("pricing_analysis", body["teardown"])

    def test_06_replay_attack_detection(self) -> None:
        """Reusing the same challenge nonce and voucher must be rejected with HTTP 409 Conflict."""
        # 1. First spend (valid)
        _, challenge_headers, _ = self.gateway.handle_request("GET", "/api/b2a/brand-tokens", {})
        nonce = challenge_headers["X-Challenge-Nonce"]
        voucher = "vch_tx_base_unique_voucher_112233"

        auth_headers = {
            "authorization": f"L402 {nonce}:{voucher}",
        }
        code1, _, _ = self.gateway.handle_request("GET", "/api/b2a/brand-tokens", auth_headers)
        self.assertEqual(code1, 200)

        # 2. Second spend attempt with identical nonce & voucher (Replay Attack)
        code2, _, body2 = self.gateway.handle_request("GET", "/api/b2a/brand-tokens", auth_headers)
        self.assertEqual(code2, 409)
        self.assertEqual(body2["status"], "error")
        self.assertIn("Replay attack detected", body2["message"])

    def test_07_expired_nonce_rejected(self) -> None:
        """Expired nonce must be rejected with HTTP 402 Payment Required."""
        # Create a gateway with 0-second TTL (instant expiry)
        fast_expiring_gateway = B2AGateway(secret_key="fast-expire", ttl_seconds=-1)
        challenge = fast_expiring_gateway.challenge_manager.create_challenge("/api/b2a/brand-tokens")

        auth_headers = {
            "authorization": f"L402 {challenge.nonce}:vch_tx_base_voucher_expired",
        }
        code, _, body = fast_expiring_gateway.handle_request("GET", "/api/b2a/brand-tokens", auth_headers)
        self.assertEqual(code, 402)
        self.assertIn("expired", body["message"].lower())

    def test_08_malformed_or_tampered_nonce_rejected(self) -> None:
        """Tampered or corrupted nonce must be rejected with HTTP 400 Bad Request."""
        # 1. Random invalid string
        auth_headers_corrupt = {"authorization": "L402 invalid_base64_string:vch_tx_base_12345678"}
        code1, _, body1 = self.gateway.handle_request("GET", "/api/b2a/brand-tokens", auth_headers_corrupt)
        self.assertEqual(code1, 400)
        self.assertEqual(body1["status"], "error")

        # 2. Tampered endpoint inside nonce
        challenge = self.gateway.challenge_manager.create_challenge("/api/b2a/brand-tokens")
        # Send nonce created for /api/b2a/brand-tokens to /api/b2a/teardown
        auth_headers_tampered = {"authorization": f"L402 {challenge.nonce}:vch_tx_base_12345678"}
        code2, _, body2 = self.gateway.handle_request("POST", "/api/b2a/teardown", auth_headers_tampered)
        self.assertEqual(code2, 400)
        self.assertIn("mismatch", body2["message"].lower())

    def test_09_malformed_auth_header_rejected(self) -> None:
        """Auth headers missing required components must be rejected."""
        # Missing voucher
        auth_headers = {"authorization": "L402 "}
        code, _, body = self.gateway.handle_request("GET", "/api/b2a/brand-tokens", auth_headers)
        self.assertEqual(code, 402)

        # Non-L402 scheme
        auth_headers_bearer = {"authorization": "Bearer some_jwt_token"}
        code, _, _ = self.gateway.handle_request("GET", "/api/b2a/brand-tokens", auth_headers_bearer)
        self.assertEqual(code, 402)


class TestAgentShopperSDK(unittest.TestCase):
    """Unit and flow tests for AgentShopper autonomous payment client SDK."""

    def setUp(self) -> None:
        self.gateway = B2AGateway(secret_key="shopper-test-secret", ttl_seconds=120)
        self.shopper = AgentShopper(in_memory_gateway=self.gateway, agent_id="unit-shopper-01")

    def test_10_shopper_auto_negotiation_brand_tokens(self) -> None:
        """AgentShopper should automatically negotiate 402 paywall and retrieve brand tokens."""
        result = self.shopper.get_brand_tokens("FLAMINGO")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["brand"], "FLAMINGO")
        self.assertIn("_payment_receipt", result)
        self.assertEqual(len(self.shopper.payment_history), 1)
        self.assertEqual(self.shopper.payment_history[0]["status"], "settled")

    def test_11_shopper_auto_negotiation_teardown(self) -> None:
        """AgentShopper should automatically negotiate 402 paywall for competitive teardown."""
        result = self.shopper.get_teardown("target-saas.com")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["target"], "target-saas.com")
        self.assertIn("feature_matrix", result["teardown"])
        self.assertEqual(len(self.shopper.payment_history), 1)

    def test_12_shopper_disabled_auto_pay_raises_error(self) -> None:
        """When auto_pay is disabled, HTTP 402 should raise RuntimeError without payment attempt."""
        shopper_no_pay = AgentShopper(
            in_memory_gateway=self.gateway,
            agent_id="no-pay-agent",
            auto_pay=False,
        )
        with self.assertRaises(RuntimeError) as ctx:
            shopper_no_pay.get_brand_tokens("FLAMINGO")
        self.assertIn("failed with status 402", str(ctx.exception))
        self.assertEqual(len(shopper_no_pay.payment_history), 0)


class TestLiveHTTPServer(unittest.TestCase):
    """Live integration tests running B2AGateway over an actual HTTP socket."""

    server_thread: threading.Thread
    http_server: Any
    server_port: int = 8922
    base_url: str

    @classmethod
    def setUpClass(cls) -> None:
        cls.test_gateway = B2AGateway(secret_key="live-http-test-key", ttl_seconds=120)
        cls.http_server = start_native_server(
            host="127.0.0.1",
            port=cls.server_port,
            gateway=cls.test_gateway,
        )
        cls.server_thread = threading.Thread(target=cls.http_server.serve_forever, daemon=True)
        cls.server_thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.server_port}"
        time.sleep(0.1)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.http_server.shutdown()
        cls.http_server.server_close()

    def test_13_live_http_health(self) -> None:
        req = urllib.request.Request(f"{self.base_url}/health")
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data["status"], "ok")

    def test_14_live_http_agent_shopper_full_loop(self) -> None:
        """AgentShopper over live HTTP network socket."""
        shopper = AgentShopper(base_url=self.base_url, agent_id="live-http-shopper")
        tokens = shopper.get_brand_tokens("FLAMINGO")
        self.assertEqual(tokens["status"], "success")
        self.assertEqual(tokens["brand"], "FLAMINGO")
        self.assertIn("differentiation_index", tokens["intelligence"])

        teardown = shopper.get_teardown("live-target.io")
        self.assertEqual(teardown["status"], "success")
        self.assertEqual(teardown["target"], "live-target.io")

    def test_15_live_http_replay_rejection(self) -> None:
        """Replaying spent voucher over live HTTP socket returns HTTP 409."""
        shopper = AgentShopper(base_url=self.base_url, agent_id="live-replay-shopper")
        shopper.get_brand_tokens("FLAMINGO")
        last_payment = shopper.payment_history[-1]

        # Attempt to replay the exact same nonce and voucher
        req = urllib.request.Request(
            f"{self.base_url}/api/b2a/brand-tokens?brand=FLAMINGO",
            headers={"Authorization": f"L402 {last_payment['nonce']}:{last_payment['voucher']}"},
            method="GET",
        )
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(req)
        self.assertEqual(ctx.exception.code, 409)


class TestFormattingAndIsolation(unittest.TestCase):
    """Verifies strict zero em-dash compliance and brand isolation across all files."""

    def test_16_zero_em_dash_compliance(self) -> None:
        target_files = [
            REPO_DIR / "b2a_gateway.py",
            REPO_DIR / "agent_shopper.py",
            REPO_DIR / "test_b2a_gateway.py",
        ]
        forbidden_chars = ["\u2014", "\u2013"]  # Em-dash and En-dash

        for file_path in target_files:
            if not file_path.exists():
                continue
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                for line_idx, line in enumerate(content.splitlines(), start=1):
                    for char in forbidden_chars:
                        self.assertNotIn(
                            char,
                            line,
                            f"Forbidden dash character found in {file_path.name}:{line_idx} -> {line}",
                        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
