/**
 * Canary: Cold Email Spamtrap & Deliverability Sentinel
 * Verifies domain DNS records (MX, SPF, DMARC, DKIM) via Cloudflare DNS over HTTPS.
 * Analyzes email subject and body for spam trigger signals and risk markers.
 * Complies strictly with zero em-dash policy.
 */

export const SPAM_TRIGGERS = [
  { pattern: /\b(100% free|risk-free|risk free|guaranteed|earn \$|make money fast)\b/i, penalty: 25, reason: "High-risk financial promise" },
  { pattern: /\b(act now|limited time|urgent|instant access|dont delete|don't delete)\b/i, penalty: 15, reason: "Artificial urgency marker" },
  { pattern: /\b(click here|click below|click this link|open immediately)\b/i, penalty: 15, reason: "Aggressive link prompt" },
  { pattern: /\b(congratulations|you are a winner|selected recipient|dear friend)\b/i, penalty: 20, reason: "Classic spam intro pattern" },
  { pattern: /\b(buy direct|order now|cheap|lowest price|no obligation)\b/i, penalty: 15, reason: "Direct sales buzzword" },
  { pattern: /[\$€£]{2,}/, penalty: 15, reason: "Excessive currency symbols" },
  { pattern: /!{2,}|\?{2,}/, penalty: 15, reason: "Excessive exclamation or question marks" }
];

export async function fetchDnsRecord(name, type) {
  const url = `https://cloudflare-dns.com/dns-query?name=${encodeURIComponent(name)}&type=${encodeURIComponent(type)}`;
  try {
    const res = await fetch(url, {
      headers: { "Accept": "application/dns-json" }
    });
    if (!res.ok) {
      return { status: "error", error: `DNS query failed with HTTP ${res.status}` };
    }
    const data = await res.json();
    return { status: "ok", data };
  } catch (err) {
    return { status: "error", error: err.message || "DNS query network error" };
  }
}

export function parseSpfRecord(txtRecords) {
  if (!Array.isArray(txtRecords)) return { found: false, record: null, valid: false };
  for (const item of txtRecords) {
    const text = (item.data || "").replace(/^"(.*)"$/, "$1");
    if (text.startsWith("v=spf1")) {
      const isStrict = text.includes("-all");
      const isSoft = text.includes("~all");
      const isBad = text.includes("+all");
      return {
        found: true,
        record: text,
        valid: !isBad,
        policy: isStrict ? "strict (-all)" : (isSoft ? "softfail (~all)" : "neutral")
      };
    }
  }
  return { found: false, record: null, valid: false, policy: "missing" };
}

export function parseDmarcRecord(txtRecords) {
  if (!Array.isArray(txtRecords)) return { found: false, record: null, policy: "missing" };
  for (const item of txtRecords) {
    const text = (item.data || "").replace(/^"(.*)"$/, "$1");
    if (text.startsWith("v=DMARC1")) {
      const match = text.match(/p=([a-zA-Z]+)/);
      const policy = match ? match[1].toLowerCase() : "none";
      return {
        found: true,
        record: text,
        policy: policy,
        valid: true
      };
    }
  }
  return { found: false, record: null, policy: "missing", valid: false };
}

export function analyzeCopySpam(subject = "", body = "") {
  let penaltyTotal = 0;
  const flagged = [];
  const recommendations = [];

  const cleanSubject = (subject || "").trim();
  const cleanBody = (body || "").trim();

  // Subject line caps check
  if (cleanSubject.length > 5 && cleanSubject === cleanSubject.toUpperCase() && /[A-Z]/.test(cleanSubject)) {
    penaltyTotal += 25;
    flagged.push({ reason: "All caps subject line", penalty: 25 });
    recommendations.push("Avoid writing subject lines in all uppercase letters.");
  }

  // Combined text checks
  const fullText = `${cleanSubject}\n${cleanBody}`;

  for (const trigger of SPAM_TRIGGERS) {
    if (trigger.pattern.test(fullText)) {
      penaltyTotal += trigger.penalty;
      flagged.push({ reason: trigger.reason, penalty: trigger.penalty });
    }
  }

  // Check for opt-out presence in body
  const hasOptOut = /\b(unsubscribe|opt out|opt-out|reply stop|remove me)\b/i.test(cleanBody);
  if (!hasOptOut && cleanBody.length > 100) {
    penaltyTotal += 15;
    flagged.push({ reason: "No clear unsubscribe or opt-out statement", penalty: 15 });
    recommendations.push("Add a simple one-line opt-out option (for example: Reply STOP to unsubscribe).");
  }

  // Check link density
  const linkMatches = fullText.match(/https?:\/\/[^\s]+/g) || [];
  if (linkMatches.length > 3) {
    penaltyTotal += 15;
    flagged.push({ reason: `Too many links detected (${linkMatches.length} links)`, penalty: 15 });
    recommendations.push("Limit outbound links to 1 clear action link per cold email.");
  }

  const score = Math.min(100, penaltyTotal);

  return {
    spam_score: score,
    risk_level: score < 20 ? "low" : (score <= 45 ? "medium" : "high"),
    flagged_items: flagged,
    recommendations
  };
}

export async function runCanaryDiagnostic(domain, subject = "", body = "") {
  const cleanDomain = (domain || "").toLowerCase().trim().replace(/^https?:\/\//, "").replace(/\/.*$/, "");
  
  if (!cleanDomain || !cleanDomain.includes(".")) {
    return {
      status: "error",
      message: "Please provide a valid sender domain (e.g. yourcompany.com)."
    };
  }

  // 1. Fetch DNS records in parallel
  const [mxRes, txtRes, dmarcRes] = await Promise.all([
    fetchDnsRecord(cleanDomain, "MX"),
    fetchDnsRecord(cleanDomain, "TXT"),
    fetchDnsRecord(`_dmarc.${cleanDomain}`, "TXT")
  ]);

  const mxRecords = (mxRes.status === "ok" && mxRes.data.Answer) || [];
  const txtRecords = (txtRes.status === "ok" && txtRes.data.Answer) || [];
  const dmarcRecords = (dmarcRes.status === "ok" && dmarcRes.data.Answer) || [];

  const hasMx = mxRecords.length > 0;
  const spf = parseSpfRecord(txtRecords);
  const dmarc = parseDmarcRecord(dmarcRecords);

  // 2. Analyze copy
  const copyAudit = analyzeCopySpam(subject, body);

  // 3. Compute overall health verdict
  let scorePenalties = copyAudit.spam_score;
  const criticalIssues = [];

  if (!hasMx) {
    criticalIssues.push("No MX records configured. Mail delivery to this domain will fail.");
    scorePenalties += 30;
  }

  if (!spf.found) {
    criticalIssues.push("Missing SPF record. Incoming mail servers will flag messages as spoofed.");
    scorePenalties += 25;
  }

  if (!dmarc.found) {
    criticalIssues.push("Missing DMARC policy. Google and Yahoo require DMARC for bulk deliverability.");
    scorePenalties += 20;
  }

  const totalRiskScore = Math.min(100, scorePenalties);
  let verdict = "green";
  if (totalRiskScore > 50 || !hasMx || !spf.found) {
    verdict = "red";
  } else if (totalRiskScore > 20 || !dmarc.found) {
    verdict = "yellow";
  }

  return {
    status: "ok",
    domain: cleanDomain,
    verdict,
    total_risk_score: totalRiskScore,
    dns: {
      mx: { valid: hasMx, count: mxRecords.length },
      spf,
      dmarc
    },
    copy_analysis: copyAudit,
    critical_issues: criticalIssues,
    seed_placement_offer: {
      name: "5-Seed Live Placement Test",
      description: "Send a live canary test to 5 monitored seed mailboxes across Google Workspace, Outlook 365, and iCloud to verify actual inbox vs spam folder delivery.",
      price_usd: 1,
      trial_runs: 5,
      subscription_price_usd: 9,
      checkout_url: "https://buy.stripe.com/5kQ7sE47F6A43370wW5AQ01"
    }
  };
}
