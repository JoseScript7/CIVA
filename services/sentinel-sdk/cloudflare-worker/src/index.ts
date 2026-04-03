// CIVA Sentinel — Cloudflare Worker Edge Pre-filter
// Runs at CDN edge before traffic reaches origin server.
// Sub-5ms processing budget.

export interface Env {
  CIVA_KV: KVNamespace;
  ORIGIN_URL: string;
  VELOCITY_WINDOW_SEC: string;
  VELOCITY_THRESHOLD: string;
}

interface EdgeSignals {
  clientIP: string;
  country: string;
  asn: number;
  ja3Hash: string;
  isBot: boolean;
  botScore: number;
  threatScore: number;
  requestVelocity: number;
  timestamp: number;
}

export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const startTime = Date.now();

    // ---- Extract Edge Signals ----
    const cf = request.cf as any;
    const signals: EdgeSignals = {
      clientIP: request.headers.get("CF-Connecting-IP") || "unknown",
      country: cf?.country || "unknown",
      asn: cf?.asn || 0,
      ja3Hash: cf?.tlsJA3Hash || "",
      isBot: cf?.botManagement?.verified_bot || false,
      botScore: cf?.botManagement?.score || 100,
      threatScore: cf?.threatScore || 0,
      requestVelocity: 0,
      timestamp: Date.now(),
    };

    // ---- Compute Request Velocity from Edge KV ----
    const velocityKey = `velocity:${signals.clientIP}`;
    const windowSec = parseInt(env.VELOCITY_WINDOW_SEC || "60");
    const threshold = parseInt(env.VELOCITY_THRESHOLD || "100");

    try {
      const stored = await env.CIVA_KV.get(velocityKey, "json") as { count: number; windowStart: number } | null;
      const now = Math.floor(Date.now() / 1000);

      if (stored && (now - stored.windowStart) < windowSec) {
        stored.count++;
        signals.requestVelocity = stored.count;
        await env.CIVA_KV.put(velocityKey, JSON.stringify(stored), {
          expirationTtl: windowSec * 2,
        });
      } else {
        const newEntry = { count: 1, windowStart: now };
        signals.requestVelocity = 1;
        await env.CIVA_KV.put(velocityKey, JSON.stringify(newEntry), {
          expirationTtl: windowSec * 2,
        });
      }
    } catch (e) {
      // KV failures are non-blocking — continue with velocity = 0
      console.error("KV velocity tracking error:", e);
    }

    // ---- Enrich Request Headers for Origin ----
    const enrichedHeaders = new Headers(request.headers);
    enrichedHeaders.set("X-CIVA-Client-IP", signals.clientIP);
    enrichedHeaders.set("X-CIVA-Country", signals.country);
    enrichedHeaders.set("X-CIVA-ASN", signals.asn.toString());
    enrichedHeaders.set("X-CIVA-JA3", signals.ja3Hash);
    enrichedHeaders.set("X-CIVA-Bot-Score", signals.botScore.toString());
    enrichedHeaders.set("X-CIVA-Threat-Score", signals.threatScore.toString());
    enrichedHeaders.set("X-CIVA-Velocity", signals.requestVelocity.toString());
    enrichedHeaders.set("X-CIVA-Edge-Time", (Date.now() - startTime).toString());
    enrichedHeaders.set("X-CIVA-Timestamp", signals.timestamp.toString());

    // ---- Early Rejection (extreme cases only) ----
    // Block requests with Cloudflare threat score > 80 at edge
    if (signals.threatScore > 80) {
      return new Response(
        JSON.stringify({
          error: "Access denied",
          code: "EDGE_BLOCKED",
          request_id: crypto.randomUUID(),
        }),
        {
          status: 403,
          headers: { "Content-Type": "application/json" },
        }
      );
    }

    // ---- Forward to Origin ----
    const originUrl = new URL(request.url);
    originUrl.hostname = env.ORIGIN_URL || originUrl.hostname;

    const originRequest = new Request(originUrl.toString(), {
      method: request.method,
      headers: enrichedHeaders,
      body: request.body,
      redirect: "follow",
    });

    const response = await fetch(originRequest);

    // ---- Add Edge Timing Header to Response ----
    const enrichedResponse = new Response(response.body, response);
    enrichedResponse.headers.set("X-CIVA-Edge-Latency", `${Date.now() - startTime}ms`);

    return enrichedResponse;
  },
};
