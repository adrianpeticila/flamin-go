/**
 * Flamin.go B2A Headless API Endpoint
 * Route: /api/teardown
 * High-density competitor teardown & AEO readiness audit for AI coding agents.
 */

const CORS_HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, Authorization",
  "Content-Type": "application/json; charset=utf-8",
};

export async function onRequestOptions() {
  return new Response(null, {
    status: 204,
    headers: CORS_HEADERS,
  });
}

function normalizeUrl(rawUrl) {
  if (!rawUrl || typeof rawUrl !== "string") return null;
  let target = rawUrl.trim();
  if (!target.startsWith("http://") && !target.startsWith("https://")) {
    target = "https://" + target;
  }
  try {
    return new URL(target);
  } catch {
    return null;
  }
}

function extractBrandName(hostname) {
  if (!hostname) return "Target Brand";
  const cleaned = hostname.replace(/^www\./i, "");
  const parts = cleaned.split(".");
  const name = parts[0] || cleaned;
  return name.charAt(0).toUpperCase() + name.slice(1);
}

export async function onRequest(context) {
  const { request } = context;

  if (request.method === "OPTIONS") {
    return onRequestOptions();
  }

  let targetUrlStr = null;

  if (request.method === "GET") {
    const urlObj = new URL(request.url);
    targetUrlStr = urlObj.searchParams.get("url") || urlObj.searchParams.get("domain");
  } else if (request.method === "POST") {
    try {
      const contentType = request.headers.get("content-type") || "";
      if (contentType.includes("application/json")) {
        const body = await request.json();
        targetUrlStr = body.url || body.domain;
      } else if (
        contentType.includes("application/x-www-form-urlencoded") ||
        contentType.includes("multipart/form-data")
      ) {
        const formData = await request.formData();
        targetUrlStr = formData.get("url") || formData.get("domain");
      } else {
        const text = await request.text();
        try {
          const body = JSON.parse(text);
          targetUrlStr = body.url || body.domain;
        } catch {
          targetUrlStr = text;
        }
      }
    } catch {
      const urlObj = new URL(request.url);
      targetUrlStr = urlObj.searchParams.get("url");
    }
  }

  if (!targetUrlStr) {
    return new Response(
      JSON.stringify(
        {
          error: "Missing required parameter: 'url'",
          usage: "GET /api/teardown?url=example.com or POST { \"url\": \"https://example.com\" }",
          b2a_meta: {
            provider: "Flamin.go B2A",
            docs: "https://flamin-go.pages.dev",
            upgrade_pass: "https://buy.stripe.com/4gM5kwbA75w0avzdjI5AQ00",
          },
        },
        null,
        2
      ),
      {
        status: 400,
        headers: CORS_HEADERS,
      }
    );
  }

  const parsedUrl = normalizeUrl(targetUrlStr);
  if (!parsedUrl) {
    return new Response(
      JSON.stringify(
        {
          error: `Invalid URL format: '${targetUrlStr}'`,
          b2a_meta: {
            provider: "Flamin.go B2A",
            docs: "https://flamin-go.pages.dev",
            upgrade_pass: "https://buy.stripe.com/4gM5kwbA75w0avzdjI5AQ00",
          },
        },
        null,
        2
      ),
      {
        status: 400,
        headers: CORS_HEADERS,
      }
    );
  }

  const domain = parsedUrl.hostname.replace(/^www\./i, "");
  const brandName = extractBrandName(parsedUrl.hostname);
  const targetOrigin = parsedUrl.origin;

  let htmlContent = "";
  let llmsTxtFound = false;
  let hasJsonLd = false;
  let foundSchemas = [];
  let metaDescription = "";
  let pageTitle = "";

  // Perform lightweight real-time probe with timeout
  try {
    const fetchController = new AbortController();
    const timeout = setTimeout(() => fetchController.abort(), 3500);

    const [pageRes, llmsRes] = await Promise.allSettled([
      fetch(parsedUrl.toString(), {
        signal: fetchController.signal,
        headers: {
          "User-Agent": "Flamin-go-B2A-Audit/1.0 (AEO Readiness Inspector; +https://flamin-go.pages.dev)",
          "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
      }),
      fetch(`${targetOrigin}/llms.txt`, {
        signal: fetchController.signal,
        headers: {
          "User-Agent": "Flamin-go-B2A-Audit/1.0 (AEO Readiness Inspector; +https://flamin-go.pages.dev)",
        },
      }),
    ]);

    clearTimeout(timeout);

    if (llmsRes.status === "fulfilled" && llmsRes.value && llmsRes.value.ok) {
      llmsTxtFound = true;
    }

    if (pageRes.status === "fulfilled" && pageRes.value && pageRes.value.ok) {
      htmlContent = await pageRes.value.text();

      // Extract title
      const titleMatch = htmlContent.match(/<title[^>]*>([^<]+)<\/title>/i);
      if (titleMatch) pageTitle = titleMatch[1].trim();

      // Extract description
      const metaMatch =
        htmlContent.match(/<meta[^>]+name=["']description["'][^>]+content=["']([^"']+)["']/i) ||
        htmlContent.match(/<meta[^>]+content=["']([^"']+)["'][^>]+name=["']description["']/i);
      if (metaMatch) metaDescription = metaMatch[1].trim();

      // Extract JSON-LD scripts
      const jsonLdRegex = /<script[^>]+type=["']application\/ld\+json["'][^>]*>([\s\S]*?)<\/script>/gi;
      let match;
      while ((match = jsonLdRegex.exec(htmlContent)) !== null) {
        hasJsonLd = true;
        try {
          const parsed = JSON.parse(match[1]);
          if (parsed["@type"]) {
            foundSchemas.push(parsed["@type"]);
          } else if (Array.isArray(parsed["@graph"])) {
            parsed["@graph"].forEach((item) => {
              if (item && item["@type"]) foundSchemas.push(item["@type"]);
            });
          }
        } catch {
          foundSchemas.push("CustomJSONLD");
        }
      }
    }
  } catch {
    // Network/probe error - continue with deterministic heuristic analysis
  }

  // Flatten found schemas
  foundSchemas = Array.from(new Set(foundSchemas.flat().filter(Boolean)));

  // Identify Schema.org gaps
  const expectedSchemas = ["SoftwareApplication", "Organization", "FAQPage", "AggregateRating"];
  const schemaGaps = expectedSchemas.filter((s) => !foundSchemas.includes(s));

  // Compute AEO Readiness Score (0-100)
  let aeoScore = 20; // Base score for reachable domain
  if (hasJsonLd) aeoScore += 25;
  if (foundSchemas.includes("SoftwareApplication") || foundSchemas.includes("Product")) aeoScore += 15;
  if (foundSchemas.includes("Organization")) aeoScore += 10;
  if (foundSchemas.includes("FAQPage")) aeoScore += 10;
  if (llmsTxtFound) aeoScore += 20;
  if (metaDescription) aeoScore += 5;
  aeoScore = Math.min(100, aeoScore);

  // Recommended JSON-LD snippet
  const recommendedJsonLd = {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "SoftwareApplication",
        "@id": `${targetOrigin}/#software`,
        "name": brandName,
        "url": targetOrigin,
        "description": metaDescription || `${brandName} platform and services.`,
        "applicationCategory": "BusinessApplication",
        "operatingSystem": "All",
        "offers": {
          "@type": "Offer",
          "price": "0",
          "priceCurrency": "USD",
          "availability": "https://schema.org/InStock",
        },
      },
      {
        "@type": "Organization",
        "@id": `${targetOrigin}/#organization`,
        "name": brandName,
        "url": targetOrigin,
        "logo": `${targetOrigin}/favicon.ico`,
        "sameAs": [],
      },
      {
        "@type": "FAQPage",
        "@id": `${targetOrigin}/#faq`,
        "mainEntity": [
          {
            "@type": "Question",
            "name": `What is ${brandName}?`,
            "acceptedAnswer": {
              "@type": "Answer",
              "text": `${brandName} provides optimized workflows and measurable business outcomes.`,
            },
          },
        ],
      },
    ],
  };

  // 3 Surgical code fixes prioritized for AI coding agents
  const surgicalFixes = [
    {
      priority: 1,
      target_file: "public/llms.txt",
      action: "CREATE_LLMS_TXT",
      description: "Deploy an llms.txt file in public root to expose system capabilities and high-signal docs to LLM crawlers.",
      snippet: `# ${brandName} Documentation\n> ${metaDescription || brandName + ' official documentation for AI agents and LLM scrapers.'}\n\n## Core Capabilities\n- System architecture and API endpoints\n- Machine-readable pricing and feature specifications\n\n## Optional Context\n- Full documentation: ${targetOrigin}/docs\n`,
    },
    {
      priority: 2,
      target_file: "index.html",
      action: "INJECT_SCHEMA_JSONLD",
      description: "Inject structured Schema.org JSON-LD in <head> covering SoftwareApplication, Organization, and FAQPage.",
      snippet: `<script type="application/ld+json">\n${JSON.stringify(recommendedJsonLd, null, 2)}\n</script>`,
    },
    {
      priority: 3,
      target_file: "_headers (or server config)",
      action: "ADD_AEO_CORS_HEADERS",
      description: "Allow LLM scrapers and agentic tool-calling runtimes to consume structured public endpoints without CORS blocks.",
      snippet: `/llms.txt\n  Content-Type: text/plain; charset=utf-8\n  Access-Control-Allow-Origin: *\n  Cache-Control: public, max-age=3600\n`,
    },
  ];

  const responsePayload = {
    brand: domain,
    brand_display: brandName,
    target_url: parsedUrl.toString(),
    aeo_readiness_score: aeoScore,
    schema_org_detected: foundSchemas,
    schema_org_gaps: schemaGaps,
    llms_txt_status: llmsTxtFound ? "discovered" : "missing",
    recommended_jsonld: recommendedJsonLd,
    surgical_fixes: surgicalFixes,
    b2a_meta: {
      provider: "Flamin.go B2A",
      docs: "https://flamin-go.pages.dev",
      upgrade_pass: "https://buy.stripe.com/4gM5kwbA75w0avzdjI5AQ00",
    },
  };

  return new Response(JSON.stringify(responsePayload, null, 2), {
    status: 200,
    headers: CORS_HEADERS,
  });
}
