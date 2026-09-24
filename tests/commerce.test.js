/**
 * Comprehensive verification test suite for Flamin.go M2M Agentic Commerce.
 * Verifies catalog 7-key schema, x402 headers, stripe_hosted 200, HMAC webhook,
 * $20 USD daily programmatic cap, rate limiting, and zero em-dash compliance.
 */

import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import {
  CATALOG,
  MemoryKV,
  createHmacSignature,
  handleCatalogRequest,
  handleBuyRequest,
  handleWebhookRequest
} from "../lib/commerce.js";
import worker from "../worker.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT_DIR = path.resolve(__dirname, "..");

let passed = 0;
let failed = 0;

async function test(name, fn) {
  try {
    await fn();
    console.log(`[PASS] ${name}`);
    passed++;
  } catch (err) {
    console.error(`[FAIL] ${name}`);
    console.error(err);
    failed++;
  }
}

async function runTests() {
  console.log("Starting Flamin.go M2M Agentic Commerce Verification Suite...\n");

  // 1. Catalog schema verification
  await test("1. Catalog schema has exact 7 contract keys for all products", async () => {
    const requiredKeys = [
      "id",
      "name",
      "price_cents",
      "currency",
      "description",
      "sample_output_url",
      "checkout_type"
    ];

    assert.equal(CATALOG.length, 3, "Catalog must contain exactly 3 products");

    for (const item of CATALOG) {
      const keys = Object.keys(item).sort();
      assert.deepEqual(
        keys,
        [...requiredKeys].sort(),
        `Product ${item.id} must have exactly the 7 contract keys`
      );
      assert.equal(typeof item.id, "string");
      assert.equal(typeof item.name, "string");
      assert.equal(typeof item.price_cents, "number");
      assert.equal(item.currency, "USD");
      assert.equal(typeof item.description, "string");
      assert.equal(typeof item.sample_output_url, "string");
      assert.ok(
        item.checkout_type === "stripe_hosted" || item.checkout_type === "x402",
        `Unknown checkout_type: ${item.checkout_type}`
      );
    }

    const adConcept = CATALOG.find((p) => p.id === "ad-concept-pack");
    assert.ok(adConcept, "ad-concept-pack must exist");
    assert.equal(adConcept.price_cents, 9900);
    assert.equal(adConcept.checkout_type, "stripe_hosted");

    const visualHook = CATALOG.find((p) => p.id === "visual-hook-matrix");
    assert.ok(visualHook, "visual-hook-matrix must exist");
    assert.equal(visualHook.price_cents, 4900);
    assert.equal(visualHook.checkout_type, "stripe_hosted");

    const microHook = CATALOG.find((p) => p.id === "micro-hook-query");
    assert.ok(microHook, "micro-hook-query must exist");
    assert.equal(microHook.price_cents, 500);
    assert.equal(microHook.checkout_type, "x402");
  });

  // 2. Static catalog file matches dynamic catalog
  await test("2. Static api/catalog.json exists and matches CATALOG definition", async () => {
    const staticPath = path.join(ROOT_DIR, "api", "catalog.json");
    const publicPath = path.join(ROOT_DIR, "public", "api", "catalog.json");
    assert.ok(fs.existsSync(staticPath), "api/catalog.json must exist");
    assert.ok(fs.existsSync(publicPath), "public/api/catalog.json must exist");

    const staticData = JSON.parse(fs.readFileSync(staticPath, "utf8"));
    const publicData = JSON.parse(fs.readFileSync(publicPath, "utf8"));
    assert.deepEqual(staticData, CATALOG);
    assert.deepEqual(publicData, CATALOG);
  });

  // 3. GET /api/catalog.json
  await test("3. GET /api/catalog.json returns 200 with CORS and cache headers", async () => {
    const req = new Request("https://flamin-go.pages.dev/api/catalog.json", {
      method: "GET"
    });
    const res = await handleCatalogRequest(req, {});
    assert.equal(res.status, 200);
    assert.equal(res.headers.get("Content-Type"), "application/json");
    assert.equal(res.headers.get("Access-Control-Allow-Origin"), "*");
    assert.equal(res.headers.get("Cache-Control"), "public, max-age=300");

    const data = await res.json();
    assert.equal(data.length, 3);
  });

  // 4. OPTIONS request handling
  await test("4. OPTIONS preflight returns 204 with CORS headers", async () => {
    const req = new Request("https://flamin-go.pages.dev/api/catalog.json", {
      method: "OPTIONS"
    });
    const res = await handleCatalogRequest(req, {});
    assert.equal(res.status, 204);
    assert.equal(res.headers.get("Access-Control-Allow-Origin"), "*");
  });

  // 5. POST /api/agent/buy validation
  await test("5. POST /api/agent/buy requires product_id and returns 400 if missing", async () => {
    const env = { AGENT_STORE: new MemoryKV() };
    const req = new Request("https://flamin-go.pages.dev/api/agent/buy", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({})
    });
    const res = await handleBuyRequest(req, env);
    assert.equal(res.status, 400);
    const body = await res.json();
    assert.equal(body.error, "Missing required field: product_id");
  });

  await test("6. POST /api/agent/buy returns 404 for unknown product", async () => {
    const env = { AGENT_STORE: new MemoryKV() };
    const req = new Request("https://flamin-go.pages.dev/api/agent/buy", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ product_id: "non-existent-product" })
    });
    const res = await handleBuyRequest(req, env);
    assert.equal(res.status, 404);
  });

  // 6. POST /api/agent/buy stripe_hosted products
  await test("7. POST /api/agent/buy for stripe_hosted product returns 200 with checkout URL", async () => {
    const env = { AGENT_STORE: new MemoryKV() };

    // Test ad-concept-pack ($99)
    const req1 = new Request("https://flamin-go.pages.dev/api/agent/buy", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ product_id: "ad-concept-pack" })
    });
    const res1 = await handleBuyRequest(req1, env);
    assert.equal(res1.status, 200);
    assert.equal(res1.headers.get("X-Checkout-Type"), "stripe_hosted");
    const body1 = await res1.json();
    assert.equal(body1.status, "checkout_ready");
    assert.equal(body1.checkout_type, "stripe_hosted");
    assert.equal(body1.product_id, "ad-concept-pack");
    assert.equal(body1.price_cents, 9900);
    assert.equal(body1.currency, "USD");
    assert.ok(body1.checkout_url.includes("https://buy.stripe.com/"));

    // Test visual-hook-matrix ($49)
    const req2 = new Request("https://flamin-go.pages.dev/api/agent/buy", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ product_id: "visual-hook-matrix" })
    });
    const res2 = await handleBuyRequest(req2, env);
    assert.equal(res2.status, 200);
    assert.equal(res2.headers.get("X-Checkout-Type"), "stripe_hosted");
    const body2 = await res2.json();
    assert.equal(body2.price_cents, 4900);
    assert.equal(body2.checkout_type, "stripe_hosted");
  });

  // 7. POST /api/agent/buy x402 programmatic rail (quote / challenge)
  await test("8. POST /api/agent/buy for micro-hook-query returns HTTP 402 with required x402 headers", async () => {
    const env = { AGENT_STORE: new MemoryKV() };
    const req = new Request("https://flamin-go.pages.dev/api/agent/buy", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ product_id: "micro-hook-query" })
    });
    const res = await handleBuyRequest(req, env);
    assert.equal(res.status, 402, "Initial x402 buy request must return 402 Payment Required");

    // Verify all mandatory x402 headers
    assert.equal(res.headers.get("X-Payment-Required"), "true");
    assert.equal(res.headers.get("X-Payment-Amount"), "500");
    assert.equal(res.headers.get("X-Payment-Currency"), "USD");
    assert.equal(res.headers.get("X-Payment-Product-Id"), "micro-hook-query");
    assert.equal(res.headers.get("X-Payment-Rail"), "x402");
    assert.ok(res.headers.get("X-Payment-Invoice").startsWith("inv_"));
    assert.equal(res.headers.get("X-402-Price-Cents"), "500");
    assert.equal(res.headers.get("X-402-Currency"), "USD");
    assert.ok(res.headers.get("WWW-Authenticate").startsWith("L402 invoice="));

    const body = await res.json();
    assert.equal(body.status, 402);
    assert.equal(body.checkout_type, "x402");
    assert.equal(body.payment.amount_cents, 500);
    assert.equal(body.payment.currency, "USD");
    assert.equal(body.payment.rail, "x402");
  });

  // 8. POST /api/agent/buy x402 programmatic rail with payment proof
  await test("9. POST /api/agent/buy for micro-hook-query with payment proof returns 200 paid", async () => {
    const env = { AGENT_STORE: new MemoryKV() };
    const req = new Request("https://flamin-go.pages.dev/api/agent/buy", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Payment-Proof": "x402_proof_token_abc123"
      },
      body: JSON.stringify({ product_id: "micro-hook-query" })
    });
    const res = await handleBuyRequest(req, env);
    assert.equal(res.status, 200);
    assert.equal(res.headers.get("X-Payment-Rail"), "x402");
    assert.ok(res.headers.get("X-Order-Id").startsWith("ord_"));

    const body = await res.json();
    assert.equal(body.status, "paid");
    assert.equal(body.settlement_rail, "x402");
    assert.equal(body.amount_cents, 500);
    assert.ok(body.fulfillment.access_url.includes("micro-hook-query.json?order="));
  });

  // 9. Rate limiting test
  await test("10. POST /api/agent/buy enforces rate limiting with 429", async () => {
    const env = {
      AGENT_STORE: new MemoryKV(),
      RATE_LIMIT_MAX_PER_MINUTE: "3"
    };

    for (let i = 0; i < 3; i++) {
      const req = new Request("https://flamin-go.pages.dev/api/agent/buy", {
        method: "POST",
        headers: { "Content-Type": "application/json", "CF-Connecting-IP": "192.168.1.50" },
        body: JSON.stringify({ product_id: "ad-concept-pack" })
      });
      const res = await handleBuyRequest(req, env);
      assert.equal(res.status, 200);
    }

    // 4th request must be rejected
    const blockedReq = new Request("https://flamin-go.pages.dev/api/agent/buy", {
      method: "POST",
      headers: { "Content-Type": "application/json", "CF-Connecting-IP": "192.168.1.50" },
      body: JSON.stringify({ product_id: "ad-concept-pack" })
    });
    const blockedRes = await handleBuyRequest(blockedReq, env);
    assert.equal(blockedRes.status, 429);
    assert.equal(blockedRes.headers.get("Retry-After"), "60");
  });

  // 10. Idempotency test
  await test("11. POST /api/agent/buy replays cached response when Idempotency-Key is provided", async () => {
    const env = { AGENT_STORE: new MemoryKV() };
    const idemKey = "test-idem-flamin-key-999";

    const req1 = new Request("https://flamin-go.pages.dev/api/agent/buy", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Idempotency-Key": idemKey
      },
      body: JSON.stringify({ product_id: "visual-hook-matrix" })
    });
    const res1 = await handleBuyRequest(req1, env);
    assert.equal(res1.status, 200);
    const body1 = await res1.json();

    const req2 = new Request("https://flamin-go.pages.dev/api/agent/buy", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Idempotency-Key": idemKey
      },
      body: JSON.stringify({ product_id: "visual-hook-matrix" })
    });
    const res2 = await handleBuyRequest(req2, env);
    assert.equal(res2.status, 200);
    assert.equal(res2.headers.get("X-Cache"), "HIT-IDEMPOTENT");
    const body2 = await res2.json();
    assert.deepEqual(body1, body2);
  });

  // 11. Webhook HMAC signature rejection
  await test("12. Webhook rejects missing or invalid HMAC signature with 401", async () => {
    const secret = "test_flamin_webhook_secret_key";
    const payload = JSON.stringify({
      event: "payment.succeeded",
      payment_id: "pay_test_001",
      product_id: "ad-concept-pack",
      amount_cents: 9900,
      rail: "stripe"
    });

    // Missing signature
    const reqMissing = new Request("https://flamin-go.pages.dev/api/agent/payments/webhook", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: payload
    });
    const resMissing = await handleWebhookRequest(reqMissing, { PAYMENT_WEBHOOK_SECRET: secret });
    assert.equal(resMissing.status, 401);

    // Invalid signature
    const reqBad = new Request("https://flamin-go.pages.dev/api/agent/payments/webhook", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Signature-SHA256": "bad_hex_signature"
      },
      body: payload
    });
    const resBad = await handleWebhookRequest(reqBad, { PAYMENT_WEBHOOK_SECRET: secret });
    assert.equal(resBad.status, 401);
  });

  // 12. Webhook valid HMAC signature acceptance
  await test("13. Webhook accepts valid HMAC-SHA256 signature with 200", async () => {
    const secret = "test_flamin_webhook_secret_key";
    const payload = JSON.stringify({
      event: "payment.succeeded",
      payment_id: "pay_test_002",
      product_id: "ad-concept-pack",
      amount_cents: 9900,
      rail: "stripe"
    });

    const signature = await createHmacSignature(payload, secret);
    const req = new Request("https://flamin-go.pages.dev/api/agent/payments/webhook", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Signature-SHA256": signature
      },
      body: payload
    });
    const res = await handleWebhookRequest(req, { PAYMENT_WEBHOOK_SECRET: secret });
    assert.equal(res.status, 200);
    const body = await res.json();
    assert.equal(body.received, true);
    assert.equal(body.status, "processed");
    assert.equal(body.payment_id, "pay_test_002");
  });

  // 13. $20 Programmatic daily cap verification
  await test("14. $20 programmatic daily cap restricts programmatic rail and allows hosted payments", async () => {
    const secret = "test_flamin_webhook_secret_key";
    const env = {
      AGENT_STORE: new MemoryKV(),
      PAYMENT_WEBHOOK_SECRET: secret,
      DAILY_PROGRAMMATIC_CAP_CENTS: "2000" // $20.00 USD = 2000 cents
    };

    // First programmatic micro-hook-query payment ($5.00 = 500 cents) -> must succeed
    const payload1 = JSON.stringify({
      event: "payment.succeeded",
      payment_id: "pay_prog_1",
      product_id: "micro-hook-query",
      amount_cents: 500,
      rail: "x402"
    });
    const sig1 = await createHmacSignature(payload1, secret);
    const req1 = new Request("https://flamin-go.pages.dev/api/agent/payments/webhook", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Signature-SHA256": sig1 },
      body: payload1
    });
    const res1 = await handleWebhookRequest(req1, env);
    assert.equal(res1.status, 200);
    const body1 = await res1.json();
    assert.equal(body1.daily_spent_cents, 500);

    // Second programmatic payment ($10.00 = 1000 cents) -> total $15 -> must succeed
    const payload2 = JSON.stringify({
      event: "payment.succeeded",
      payment_id: "pay_prog_2",
      product_id: "micro-hook-query",
      amount_cents: 1000,
      rail: "x402"
    });
    const sig2 = await createHmacSignature(payload2, secret);
    const req2 = new Request("https://flamin-go.pages.dev/api/agent/payments/webhook", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Signature-SHA256": sig2 },
      body: payload2
    });
    const res2 = await handleWebhookRequest(req2, env);
    assert.equal(res2.status, 200);
    const body2 = await res2.json();
    assert.equal(body2.daily_spent_cents, 1500);

    // Third programmatic payment ($10.00 = 1000 cents) -> total $25 > $20 cap -> MUST FAIL WITH 429
    const payload3 = JSON.stringify({
      event: "payment.succeeded",
      payment_id: "pay_prog_3",
      product_id: "micro-hook-query",
      amount_cents: 1000,
      rail: "x402"
    });
    const sig3 = await createHmacSignature(payload3, secret);
    const req3 = new Request("https://flamin-go.pages.dev/api/agent/payments/webhook", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Signature-SHA256": sig3 },
      body: payload3
    });
    const res3 = await handleWebhookRequest(req3, env);
    assert.equal(res3.status, 429, "Exceeding $20 programmatic daily cap must return 429");
    const body3 = await res3.json();
    assert.ok(body3.error.includes("daily cap of $20.00 USD exceeded"));

    // Hosted stripe payment ($99.00 = 9900 cents) is NOT restricted by programmatic cap -> must succeed
    const payloadStripe = JSON.stringify({
      event: "payment.succeeded",
      payment_id: "pay_stripe_1",
      product_id: "ad-concept-pack",
      amount_cents: 9900,
      rail: "stripe_hosted"
    });
    const sigStripe = await createHmacSignature(payloadStripe, secret);
    const reqStripe = new Request("https://flamin-go.pages.dev/api/agent/payments/webhook", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Signature-SHA256": sigStripe },
      body: payloadStripe
    });
    const resStripe = await handleWebhookRequest(reqStripe, env);
    assert.equal(resStripe.status, 200, "Hosted stripe payment must succeed despite programmatic cap");
  });

  // 14. Worker router fetch tests
  await test("15. worker.js router dispatches /api/catalog.json, /api/agent/buy, and /api/agent/payments/webhook", async () => {
    // Route /api/catalog.json
    const reqCatalog = new Request("https://flamin-go.pages.dev/api/catalog.json", { method: "GET" });
    const resCatalog = await worker.fetch(reqCatalog, {});
    assert.equal(resCatalog.status, 200);

    // Route /api/agent/buy
    const reqBuy = new Request("https://flamin-go.pages.dev/api/agent/buy", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ product_id: "ad-concept-pack" })
    });
    const resBuy = await worker.fetch(reqBuy, {});
    assert.equal(resBuy.status, 200);

    // Route /api/agent/payments/webhook without signature -> 401
    const reqHook = new Request("https://flamin-go.pages.dev/api/agent/payments/webhook", {
      method: "POST",
      body: "{}"
    });
    const resHook = await worker.fetch(reqHook, {});
    assert.equal(resHook.status, 401);

    // Non-existent route
    const reqNotFound = new Request("https://flamin-go.pages.dev/non-existent-path", { method: "GET" });
    const resNotFound = await worker.fetch(reqNotFound, {});
    assert.equal(resNotFound.status, 404);
  });

  // 15. Zero em-dash audit
  await test("16. Zero em-dashes and en-dashes across all commerce code and catalog files", async () => {
    const filesToCheck = [
      "api/catalog.json",
      "public/api/catalog.json",
      "public/samples/ad-concept-pack.json",
      "public/samples/visual-hook-matrix.json",
      "public/samples/micro-hook-query.json",
      "lib/commerce.js",
      "worker.js",
      "_worker.js",
      "functions/api/catalog.json.js",
      "functions/api/catalog.js",
      "functions/api/agent/buy.js",
      "functions/api/agent/payments/webhook.js",
      "tests/commerce.test.js"
    ];

    for (const relativeFile of filesToCheck) {
      const fullPath = path.join(ROOT_DIR, relativeFile);
      assert.ok(fs.existsSync(fullPath), `File must exist: ${relativeFile}`);
      const content = fs.readFileSync(fullPath, "utf8");

      for (let i = 0; i < content.length; i++) {
        const code = content.charCodeAt(i);
        if (code === 8211 || code === 8212) {
          throw new Error(
            `Forbidden dash character (code ${code}) found in ${relativeFile} at position ${i}`
          );
        }
      }
    }
  });

  console.log("\n========================================");
  console.log(`Summary: ${passed} passed, ${failed} failed`);
  console.log("========================================\n");

  if (failed > 0) {
    process.exit(1);
  }
}

runTests();
