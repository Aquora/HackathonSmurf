import { describe, expect, it } from "vitest";
import { requestQuestRoute } from "./quest-api";

// Shape copied from the 200 example in api/ROUTES.md (mock mode).
const ROUTE = {
  startLocation: { address: "3801 W Temple Ave, Pomona, CA 91768" },
  quests: [
    {
      location: { name: "Demo Bean Coffee", address: "101 Example Ave, Demo City, CA 90000", closingTime: "18:00", estimatedCost: 6.0 },
      arrivalTime: "10:20",
      departureTime: "10:40",
      travelDistance: 1.0,
      task: { id: "photo_inside", text: "Take a picture of the inside" },
      description: "[Demo] Stop 1: visit Demo Bean Coffee on your way around the quest.",
    },
  ],
  endLocation: { address: "3801 W Temple Ave, Pomona, CA 91768" },
  totalTime: 100,
  totalDistance: 3.0,
  estimatedCost: 6.0,
  mock: true,
};

function fakeFetch(status: number, body: unknown, headers: Record<string, string> = {}): typeof fetch {
  return (async (_url: string | URL | Request, init?: RequestInit) => {
    expect(JSON.parse(String(init?.body))).toEqual({ message: "coffee" });
    return new Response(typeof body === "string" ? body : JSON.stringify(body), { status, headers });
  }) as typeof fetch;
}

describe("requestQuestRoute", () => {
  it("sends QUEST_API_TOKEN as a bearer token only when it is set", async () => {
    const seen: (string | null)[] = [];
    const recording = (async (_url: string | URL | Request, init?: RequestInit) => {
      seen.push(new Headers(init?.headers).get("authorization"));
      return new Response(JSON.stringify(ROUTE), { status: 200 });
    }) as typeof fetch;
    const previous = process.env.QUEST_API_TOKEN;
    try {
      delete process.env.QUEST_API_TOKEN;
      await requestQuestRoute("coffee", recording);
      process.env.QUEST_API_TOKEN = "secret-token";
      await requestQuestRoute("coffee", recording);
    } finally {
      if (previous === undefined) delete process.env.QUEST_API_TOKEN;
      else process.env.QUEST_API_TOKEN = previous;
    }
    expect(seen).toEqual([null, "Bearer secret-token"]);
  });

  it("returns a parsed route on 200", async () => {
    const result = await requestQuestRoute("coffee", fakeFetch(200, ROUTE));
    expect(result).toEqual({ ok: true, route: ROUTE });
  });

  it("rejects a 200 whose body doesn't match the contract", async () => {
    const bad = { ...ROUTE, quests: [{ ...ROUTE.quests[0], task: { id: "free_coffee", text: "x" } }] };
    const result = await requestQuestRoute("coffee", fakeFetch(200, bad, { "x-request-id": "abc" }));
    expect(result).toMatchObject({ ok: false, code: "BAD_RESPONSE", requestId: "abc" });
  });

  it("passes through NO_FEASIBLE_ROUTE with the understood preferences", async () => {
    const body = {
      error: {
        code: "NO_FEASIBLE_ROUTE",
        message: "No open candidate place has a known cost within your budget. Try a higher budget.",
        requestId: "r1",
        details: {
          preferences: { desiredTime: 120, desiredBudget: 2, locationPreference: "coffee", travelMethod: "walk" },
          reason: "NONE_WITHIN_BUDGET",
          proven: true,
        },
      },
    };
    const result = await requestQuestRoute("coffee", fakeFetch(422, body));
    expect(result).toMatchObject({
      ok: false,
      code: "NO_FEASIBLE_ROUTE",
      requestId: "r1",
      preferences: { desiredBudget: 2, travelMethod: "walk" },
    });
  });

  it("reads retry-after on RATE_LIMITED", async () => {
    const body = { error: { code: "RATE_LIMITED", message: "Too many requests.", requestId: "r2" } };
    const result = await requestQuestRoute("coffee", fakeFetch(429, body, { "retry-after": "42" }));
    expect(result).toMatchObject({ ok: false, code: "RATE_LIMITED", retryAfterSeconds: 42 });
  });

  it("reports an unreachable API as NETWORK_ERROR", async () => {
    const failing = (async () => {
      throw new TypeError("fetch failed");
    }) as typeof fetch;
    expect(await requestQuestRoute("coffee", failing)).toMatchObject({ ok: false, code: "NETWORK_ERROR" });
  });

  it("handles a non-JSON error page", async () => {
    const result = await requestQuestRoute("coffee", fakeFetch(502, "<html>Bad gateway</html>"));
    expect(result).toMatchObject({ ok: false, code: "BAD_RESPONSE" });
  });
});
