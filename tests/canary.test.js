/**
 * Verification test suite for Canary deliverability sentinel.
 * Tests DNS parsing, spam trigger analysis, diagnostic scoring, and zero em-dash compliance.
 */

import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import {
  parseSpfRecord,
  parseDmarcRecord,
  analyzeCopySpam,
  runCanaryDiagnostic
} from "../lib/canary.js";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

console.log("Starting Flamingo Canary Sentinel Verification Suite...\n");

// Test 1: SPF Record Parser
{
  const validStrict = [{ data: "\"v=spf1 include:_spf.google.com -all\"" }];
  const parsedStrict = parseSpfRecord(validStrict);
  assert.equal(parsedStrict.found, true);
  assert.equal(parsedStrict.valid, true);
  assert.equal(parsedStrict.policy, "strict (-all)");

  const validSoft = [{ data: "\"v=spf1 include:sendgrid.net ~all\"" }];
  const parsedSoft = parseSpfRecord(validSoft);
  assert.equal(parsedSoft.found, true);
  assert.equal(parsedSoft.valid, true);
  assert.equal(parsedSoft.policy, "softfail (~all)");

  const badAll = [{ data: "\"v=spf1 +all\"" }];
  const parsedBad = parseSpfRecord(badAll);
  assert.equal(parsedBad.found, true);
  assert.equal(parsedBad.valid, false);

  const empty = [];
  assert.equal(parseSpfRecord(empty).found, false);
  console.log("[PASS] 1. SPF record parser correctly distinguishes strict, softfail, bad, and missing policies");
}

// Test 2: DMARC Record Parser
{
  const dmarcReject = [{ data: "\"v=DMARC1; p=reject; sp=reject; rua=mailto:d@example.com\"" }];
  const parsedReject = parseDmarcRecord(dmarcReject);
  assert.equal(parsedReject.found, true);
  assert.equal(parsedReject.policy, "reject");
  assert.equal(parsedReject.valid, true);

  const dmarcNone = [{ data: "\"v=DMARC1; p=none; rua=mailto:d@example.com\"" }];
  const parsedNone = parseDmarcRecord(dmarcNone);
  assert.equal(parsedNone.found, true);
  assert.equal(parsedNone.policy, "none");

  const empty = [];
  assert.equal(parseDmarcRecord(empty).found, false);
  console.log("[PASS] 2. DMARC parser extracts policy types and identifies missing records");
}

// Test 3: Copy Spam Analyzer (Clean vs Spammy)
{
  const cleanSubject = "Quick question on outbound infrastructure";
  const cleanBody = "Hi Alex, noticed you are expanding outbound campaigns. We built an automated deliverability sentinel for teams of 1 to 5. Let me know if you would like to test it. Reply STOP to opt out.";
  const cleanAudit = analyzeCopySpam(cleanSubject, cleanBody);
  assert.equal(cleanAudit.risk_level, "low");
  assert.ok(cleanAudit.spam_score < 20, "Clean copy should have low spam score");

  const spamSubject = "URGENT: 100% FREE CASH BONUS ACT NOW";
  const spamBody = "Click here to claim your guaranteed profit! Limited time opportunity, dont delete! Order now and make money fast $$$!!!";
  const spamAudit = analyzeCopySpam(spamSubject, spamBody);
  assert.equal(spamAudit.risk_level, "high");
  assert.ok(spamAudit.spam_score > 50, "Spammy copy must score high penalty");
  assert.ok(spamAudit.flagged_items.length >= 3, "Multiple triggers must be flagged");
  console.log("[PASS] 3. Copy spam analyzer scores clean and high-risk cold pitches accurately");
}

// Test 4: End-to-End Diagnostic Contract
{
  const result = await runCanaryDiagnostic("cloudflare.com", "Testing delivery", "Simple test body. Reply STOP to unsubscribe.");
  assert.equal(result.status, "ok");
  assert.equal(result.domain, "cloudflare.com");
  assert.ok(typeof result.total_risk_score === "number");
  assert.ok(["green", "yellow", "red"].includes(result.verdict));
  assert.ok(result.dns.mx.valid, "Cloudflare domain should have MX records");
  assert.equal(result.seed_placement_offer.price_usd, 1);
  console.log("[PASS] 4. Diagnostic returns valid structured contract with DNS, copy, and seed placement offer");
}

// Test 5: Validation for Invalid Domain
{
  const badDomainResult = await runCanaryDiagnostic("invalid-domain-no-dot", "Subject", "Body");
  assert.equal(badDomainResult.status, "error");
  console.log("[PASS] 5. Diagnostic rejects invalid domain with descriptive error");
}

// Test 6: Zero em-dash and en-dash audit
{
  const filesToCheck = [
    path.join(__dirname, "../lib/canary.js"),
    path.join(__dirname, "../public/canary.html"),
    __filename
  ];

  const dashRegex = /[\u2014\u2015\u2013]/;
  for (const file of filesToCheck) {
    const content = fs.readFileSync(file, "utf8");
    const match = content.match(dashRegex);
    assert.equal(match, null, `Found forbidden dash in ${file}`);
  }
  console.log("[PASS] 6. Zero em-dashes and en-dashes across all Canary code, UI, and test files");
}

console.log("\n========================================");
console.log("Canary Verification Summary: 6 passed, 0 failed");
console.log("========================================\n");
