import {
  handleCatalogRequest,
  handleBuyRequest,
  handleWebhookRequest,
  CORS_HEADERS
} from "./lib/commerce.js";
import { runCanaryDiagnostic } from "./lib/canary.js";

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    if (url.pathname === "/api/catalog.json" || url.pathname === "/api/catalog") {
      return handleCatalogRequest(request, env);
    }

    if (url.pathname === "/api/agent/buy") {
      return handleBuyRequest(request, env);
    }

    if (url.pathname === "/api/agent/payments/webhook") {
      return handleWebhookRequest(request, env);
    }

    if (url.pathname === "/api/canary/check" || url.pathname === "/api/canary") {
      if (request.method === "OPTIONS") {
        return new Response(null, { status: 204, headers: CORS_HEADERS });
      }

      let domain = "";
      let subject = "";
      let bodyText = "";

      if (request.method === "POST") {
        try {
          const payload = await request.json();
          domain = payload.domain || "";
          subject = payload.subject || "";
          bodyText = payload.body || "";
        } catch {
          return new Response(JSON.stringify({ status: "error", message: "Invalid JSON payload" }), {
            status: 400,
            headers: { ...CORS_HEADERS, "Content-Type": "application/json" }
          });
        }
      } else if (request.method === "GET") {
        domain = url.searchParams.get("domain") || "";
        subject = url.searchParams.get("subject") || "";
        bodyText = url.searchParams.get("body") || "";
      } else {
        return new Response("Method Not Allowed", { status: 405, headers: CORS_HEADERS });
      }

      const result = await runCanaryDiagnostic(domain, subject, bodyText);
      return new Response(JSON.stringify(result, null, 2), {
        status: result.status === "error" ? 400 : 200,
        headers: {
          ...CORS_HEADERS,
          "Content-Type": "application/json",
          "Cache-Control": "no-store"
        }
      });
    }

    if (env && env.ASSETS && typeof env.ASSETS.fetch === "function") {
      return env.ASSETS.fetch(request);
    }

    return new Response("Not Found", { status: 404 });
  }
};
