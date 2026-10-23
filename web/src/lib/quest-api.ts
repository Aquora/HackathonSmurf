import "server-only";
import { z } from "zod";

/**
 * Server-side client for the FastAPI quest backend (api/ROUTES.md, POST /v1/quests).
 * Only the Next.js server calls it, after checking the session, so the browser never
 * needs the API's address and signed-out visitors can't generate quests.
 */

/** Matches api/app/domain/types.py. The API is checked, but its output is still parsed here. */
const locationSchema = z.object({
  name: z.string().min(1).max(300),
  address: z.string().min(1).max(300),
  closingTime: z.string().max(20),
  estimatedCost: z.number().nonnegative().optional(),
});

const taskSchema = z.object({
  id: z.enum(["photo_inside", "photo_building", "review_screenshot"]),
  text: z.string().min(1).max(200),
});

const stopSchema = z.object({
  location: locationSchema,
  arrivalTime: z.string().max(10),
  departureTime: z.string().max(10),
  travelDistance: z.number().nonnegative(),
  task: taskSchema,
  description: z.string().max(500),
});

export const questRouteSchema = z.object({
  startLocation: z.object({ address: z.string().max(300) }),
  quests: z.array(stopSchema).min(1).max(10),
  endLocation: z.object({ address: z.string().max(300) }),
  totalTime: z.number().int().nonnegative().nullish(),
  totalDistance: z.number().nonnegative().nullish(),
  estimatedCost: z.number().nonnegative(),
  mock: z.literal(true).nullish(),
});

export type QuestRoute = z.infer<typeof questRouteSchema>;
export type QuestStop = z.infer<typeof stopSchema>;
export type QuestTaskId = z.infer<typeof taskSchema>["id"];

const preferencesSchema = z.object({
  desiredTime: z.number(),
  desiredBudget: z.number(),
  locationPreference: z.string(),
  travelMethod: z.string(),
});
export type QuestPreferences = z.infer<typeof preferencesSchema>;

const errorBodySchema = z.object({
  error: z.object({
    code: z.string(),
    message: z.string(),
    requestId: z.string().nullish(),
    details: z.unknown().optional(),
  }),
});

export type QuestApiResult =
  | { ok: true; route: QuestRoute }
  | {
      ok: false;
      /** API error code, or NETWORK_ERROR / BAD_RESPONSE for problems reaching or reading the API. */
      code: string;
      message: string;
      requestId: string | null;
      /** What the server understood from the message (422 NO_FEASIBLE_ROUTE only). */
      preferences?: QuestPreferences;
      retryAfterSeconds?: number;
    };

/** Real Cortex planning can take ~30 s; leave room for the API's own timeouts and one repair. */
const REQUEST_TIMEOUT_MS = 90_000;

export function questApiBaseUrl() {
  return (process.env.QUEST_API_URL || "http://localhost:8080").replace(/\/+$/, "");
}

export async function requestQuestRoute(message: string, fetchImpl: typeof fetch = fetch): Promise<QuestApiResult> {
  let res: Response;
  try {
    res = await fetchImpl(`${questApiBaseUrl()}/v1/quests`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ message }),
      signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
      cache: "no-store",
    });
  } catch (error) {
    const timedOut = error instanceof Error && error.name === "TimeoutError";
    return {
      ok: false,
      code: timedOut ? "UPSTREAM_TIMEOUT" : "NETWORK_ERROR",
      message: timedOut
        ? "Planning took too long. Please try again."
        : "The quest planner isn't reachable right now. Please try again in a moment.",
      requestId: null,
    };
  }

  const requestId = res.headers.get("x-request-id") || null;
  let body: unknown;
  try {
    body = await res.json();
  } catch {
    return { ok: false, code: "BAD_RESPONSE", message: "The quest planner sent an unreadable reply. Please try again.", requestId };
  }

  if (res.ok) {
    const parsed = questRouteSchema.safeParse(body);
    if (parsed.success) return { ok: true, route: parsed.data };
    return { ok: false, code: "BAD_RESPONSE", message: "The quest planner sent an unexpected reply. Please try again.", requestId };
  }

  const parsedError = errorBodySchema.safeParse(body);
  if (!parsedError.success) {
    return { ok: false, code: "BAD_RESPONSE", message: "Something went wrong. Please try again.", requestId };
  }
  const { code, message: errorMessage, details } = parsedError.data.error;
  const result: QuestApiResult = { ok: false, code, message: errorMessage, requestId: parsedError.data.error.requestId ?? requestId };
  if (code === "NO_FEASIBLE_ROUTE" && details && typeof details === "object" && "preferences" in details) {
    const prefs = preferencesSchema.safeParse((details as { preferences: unknown }).preferences);
    if (prefs.success) result.preferences = prefs.data;
  }
  if (code === "RATE_LIMITED") {
    const seconds = Number(res.headers.get("retry-after"));
    if (Number.isFinite(seconds) && seconds > 0) result.retryAfterSeconds = seconds;
  }
  return result;
}
