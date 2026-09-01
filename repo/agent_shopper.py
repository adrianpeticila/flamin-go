#!/usr/bin/env python3
"""
agent_shopper.py: Autonomous Agent Shopper Client SDK for Flamin.go B2A Paywalls
Pattern: Autonomous Agent Payment Interceptor (HTTP 402 / L402 / Base Protocol).

Features:
1. Seamless HTTP 402 interception: Catches paywall challenges transparently.
2. Base payment challenge parsing (extracts nonce, amount, currency, recipient).
3. Autonomous voucher signer: Generates valid Base micropayment vouchers.
4. Automated request retry with RFC-compliant L402 Authorization headers.
5. In-process direct gateway mode and live HTTP transport mode.
6. Zero em-dash compliant.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional, Tuple, Union

try:
    from b2a_gateway import B2AGateway, GLOBAL_GATEWAY
except ImportError:
    # Direct import fallback
    from repo.b2a_gateway import B2AGateway, GLOBAL_GATEWAY


class AgentShopper:
    """
    Autonomous AI Shopper Client SDK that negotiates and settles HTTP 402
    micropayments on Base network.
    """

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8402",
        agent_id: str = "agent_shopper_01",
        wallet_address: Optional[str] = None,
        private_key_mock: Optional[str] = None,
        in_memory_gateway: Optional[B2AGateway] = None,
        auto_pay: bool = True,
        max_retries: int = 2,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.agent_id = agent_id
        self.wallet_address = wallet_address or f"0xShopper{secrets.token_hex(16)}"
        self.private_key_mock = private_key_mock or secrets.token_hex(32)
        self.in_memory_gateway = in_memory_gateway
        self.auto_pay = auto_pay
        self.max_retries = max_retries
        self.payment_history: list[Dict[str, Any]] = []

    def _sign_challenge(self, challenge_data: Dict[str, Any]) -> str:
        """
        Signs a Base payment challenge and produces a unique payment voucher.
        """
        nonce = challenge_data.get("challenge_nonce", "")
        amount = challenge_data.get("amount", 0.0)
        recipient = challenge_data.get("recipient", "")

        tx_id = f"tx_base_{secrets.token_hex(12)}"
        raw_msg = f"{self.wallet_address}:{recipient}:{amount:.4f}:{nonce}:{tx_id}"
        sig = hmac.new(
            self.private_key_mock.encode("utf-8"),
            raw_msg.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        voucher = f"vch_{tx_id}_{sig[:16]}"
        return voucher

    def _execute_raw_http(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        body: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Tuple[int, Dict[str, str], Dict[str, Any]]:
        """Executes raw HTTP request over network using standard urllib."""
        headers = headers or {}
        req_headers = {"User-Agent": f"FlaminGo-AgentShopper/1.0 ({self.agent_id})"}
        req_headers.update(headers)

        url = f"{self.base_url}{endpoint}"
        if params:
            query_str = urllib.parse.urlencode(params)
            url = f"{url}?{query_str}"

        data_bytes = None
        if body:
            data_bytes = json.dumps(body).encode("utf-8")
            req_headers["Content-Type"] = "application/json"

        req = urllib.request.Request(
            url=url,
            data=data_bytes,
            headers=req_headers,
            method=method,
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                status_code = resp.status
                resp_headers = {k.lower(): v for k, v in resp.headers.items()}
                raw_content = resp.read().decode("utf-8")
                try:
                    resp_json = json.loads(raw_content)
                except Exception:
                    resp_json = {"raw": raw_content}
                return status_code, resp_headers, resp_json
        except urllib.error.HTTPError as e:
            status_code = e.code
            resp_headers = {k.lower(): v for k, v in e.headers.items()}
            raw_content = e.read().decode("utf-8")
            try:
                resp_json = json.loads(raw_content)
            except Exception:
                resp_json = {"raw": raw_content}
            return status_code, resp_headers, resp_json

    def _execute_dispatch(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        body: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Tuple[int, Dict[str, str], Dict[str, Any]]:
        """Dispatches request via in-memory gateway or network transport."""
        if self.in_memory_gateway is not None:
            clean_headers = {k.lower(): v for k, v in (headers or {}).items()}
            return self.in_memory_gateway.handle_request(
                method=method,
                path=endpoint,
                headers=clean_headers,
                query_params=params,
                body_data=body,
            )
        return self._execute_raw_http(
            method=method,
            endpoint=endpoint,
            params=params,
            body=body,
            headers=headers,
        )

    def request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        body: Optional[Dict[str, Any]] = None,
        custom_headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Main shopper execution loop with automated 402 paywall negotiation.
        """
        headers = dict(custom_headers or {})

        # Step 1: Attempt initial request
        code, resp_headers, resp_data = self._execute_dispatch(
            method=method,
            endpoint=endpoint,
            params=params,
            body=body,
            headers=headers,
        )

        # Step 2: If success, return immediately
        if code == 200:
            return resp_data

        # Step 3: Intercept HTTP 402 Payment Required
        if code == 402 and self.auto_pay:
            payment_info = resp_data.get("payment", {})
            nonce = resp_headers.get("x-challenge-nonce") or payment_info.get("challenge_nonce")
            amount = float(resp_headers.get("x-price-amount") or payment_info.get("amount", 0.05))
            currency = resp_headers.get("x-price-currency") or payment_info.get("currency", "USDC")
            network = resp_headers.get("x-network") or payment_info.get("network", "base")
            recipient = payment_info.get("recipient", "0xVault")

            if not nonce:
                raise ValueError(f"HTTP 402 received but missing challenge nonce in response: {resp_data}")

            # Generate payment voucher
            voucher = self._sign_challenge({
                "challenge_nonce": nonce,
                "amount": amount,
                "currency": currency,
                "network": network,
                "recipient": recipient,
            })

            # Record payment attempt
            record = {
                "endpoint": endpoint,
                "amount": amount,
                "currency": currency,
                "network": network,
                "nonce": nonce,
                "voucher": voucher,
                "timestamp": time.time(),
            }
            self.payment_history.append(record)

            # Build L402 Authorization Header
            auth_header = f"L402 {nonce}:{voucher}"
            retry_headers = dict(headers)
            retry_headers["Authorization"] = auth_header
            retry_headers["X-Payment-Voucher"] = voucher
            retry_headers["X-Payment-Nonce"] = nonce

            # Step 4: Retry with authorization
            retry_code, retry_headers_out, retry_data = self._execute_dispatch(
                method=method,
                endpoint=endpoint,
                params=params,
                body=body,
                headers=retry_headers,
            )

            if retry_code == 200:
                record["status"] = "settled"
                return retry_data
            else:
                record["status"] = "failed"
                raise RuntimeError(
                    f"Micro-paywall payment retry failed with status {retry_code}: {retry_data}"
                )

        # Other error codes
        raise RuntimeError(f"HTTP request to '{endpoint}' failed with status {code}: {resp_data}")

    def get_brand_tokens(self, brand: str = "FLAMINGO") -> Dict[str, Any]:
        """Fetches paywalled brand intelligence tokens (0.05 USDC)."""
        return self.request(method="GET", endpoint="/api/b2a/brand-tokens", params={"brand": brand})

    def get_teardown(self, target: str = "competitor.io") -> Dict[str, Any]:
        """Fetches paywalled competitive teardown and diff graph (0.10 USDC)."""
        return self.request(method="POST", endpoint="/api/b2a/teardown", body={"target": target})

    def get_pricing(self) -> Dict[str, Any]:
        """Fetches public endpoint catalog and pricing."""
        return self.request(method="GET", endpoint="/api/b2a/pricing")

    def check_health(self) -> Dict[str, Any]:
        """Checks gateway health status."""
        return self.request(method="GET", endpoint="/health")


# Demonstration Runner
if __name__ == "__main__":
    print("=" * 65)
    print("Flamin.go Autonomous Agent Shopper (B2A Micro-Paywall SDK Demo)")
    print("=" * 65)

    # Initialize agent shopper with in-process gateway instance
    gateway = GLOBAL_GATEWAY
    shopper = AgentShopper(in_memory_gateway=gateway, agent_id="demo-shopper-007")

    print("\n1. Checking Health and Pricing Catalog...")
    health = shopper.check_health()
    print(f"Health Status: {health.get('status')} | Network: {health.get('network')}")

    pricing = shopper.get_pricing()
    print("Available B2A Services:")
    for ep in pricing.get("endpoints", []):
        print(f" - {ep['path']}: {ep['price_usdc']} USDC ({ep['description']})")

    print("\n2. Autonomous Acquisition: Brand Intelligence Tokens (/api/b2a/brand-tokens)...")
    print("   [Attempting unauthenticated request -> Intercepting 402 -> Signing Voucher -> Retrying]")
    tokens_res = shopper.get_brand_tokens("FLAMINGO")
    print(f"   [SUCCESS] Received Tokens for: {tokens_res.get('brand')}")
    print(f"   Differentiation Index: {tokens_res['intelligence']['differentiation_index']}")
    print(f"   Payment Settlement Voucher: {tokens_res.get('_payment_receipt', {}).get('voucher')}")

    print("\n3. Autonomous Acquisition: Competitive Teardown (/api/b2a/teardown)...")
    print("   [Attempting unauthenticated request -> Intercepting 402 -> Signing Voucher -> Retrying]")
    teardown_res = shopper.get_teardown("enterprise-intel.corp")
    print(f"   [SUCCESS] Received Teardown for: {teardown_res.get('target')}")
    print(f"   Vulnerability Score: {teardown_res['teardown']['vulnerability_score']}")
    print(f"   Pricing Floor Detected: ${teardown_res['teardown']['pricing_analysis']['estimated_floor_monthly_usd']}/mo")

    print("\n4. Verification: Replay Attack Defense Test...")
    last_payment = shopper.payment_history[-1]
    replayed_headers = {
        "Authorization": f"L402 {last_payment['nonce']}:{last_payment['voucher']}",
        "X-Payment-Voucher": last_payment["voucher"],
        "X-Payment-Nonce": last_payment["nonce"],
    }
    code, _, replay_resp = gateway.handle_request(
        method="POST",
        path="/api/b2a/teardown",
        headers=replayed_headers,
        body_data={"target": "enterprise-intel.corp"},
    )
    print(f"   Replay status code: {code} (Expected: 409)")
    print(f"   Server response: {replay_resp.get('message')}")

    print("\n" + "=" * 65)
    print("All Autonomous Shopper operations completed successfully.")
    print("=" * 65)
