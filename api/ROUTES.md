# Local Quest API routes

Reference for every HTTP route the backend exposes: what to send and what comes back.
All examples below are actual responses from the running app (mock mode).

- Base URL (local): `http://localhost:8080`
- Bodies are JSON (`Content-Type: application/json`), field names are camelCase.
- No authentication yet.
- Browser calls must come from an origin listed in `CORS_ORIGINS`.

| Method | Path | Purpose |
|---|---|---|
| `GET` | [`/health`](#get-health) | Liveness check |
| `POST` | [`/v1/quests`](#post-v1quests) | Generate a round-trip quest |
| `GET` | [`/docs`](#built-in-docs-routes) | Interactive Swagger UI (not in production) |
| `GET` | [`/openapi.json`](#built-in-docs-routes) | OpenAPI schema (not in production) |

Building the frontend? Jump to [Using the API from the frontend](#using-the-api-from-the-frontend).

---

## `GET /health`

Confirms the server process is up. It does **not** check Cursor or Snowflake.
Not rate-limited.

**Input:** none.

**Returns:** `200`

```json
{ "status": "ok" }
```

---

## `POST /v1/quests`

Turns a free-text request and a starting address into a quest route that starts and
ends at that address.

### Input

```json
{
  "message": "I have 2 hours and $25. Coffee and art, walking please",
  "location": { "address": "123 Main St, Pomona, CA" }
}
```

| Field | Type | Rules |
|---|---|---|
| `message` | string | Required. 1–2000 characters after trimming whitespace. |
| `location.address` | string | Required. 3–300 characters after trimming whitespace. |

The whole body must be 16 KB or less.

What happens to the message: the model reads it for time, budget, place preference and
travel method. Anything it can't find uses a default:

| Preference | Default |
|---|---|
| `desiredTime` (minutes) | `90` |
| `desiredBudget` (US dollars) | `30` |
| `locationPreference` | `"random"` |
| `travelMethod` | `"drive"` (others: `"walk"`, `"bike"`, `"transit"`) |

### Returns: `200` — `QuestRoute`

```json
{
  "startLocation": { "address": "123 Main St, Pomona, CA" },
  "quests": [
    {
      "location": {
        "name": "Demo Bean Coffee",
        "address": "101 Example Ave, Demo City, CA 90000",
        "closingTime": "18:00"
      },
      "arrivalTime": "10:20",
      "departureTime": "10:40",
      "travelDistance": 1.0
    },
    {
      "location": {
        "name": "Demo Gallery of Art",
        "address": "202 Sample St, Demo City, CA 90000",
        "closingTime": "17:00"
      },
      "arrivalTime": "11:00",
      "departureTime": "11:20",
      "travelDistance": 1.0
    }
  ],
  "endLocation": { "address": "123 Main St, Pomona, CA" },
  "totalTime": 100,
  "totalDistance": 3.0,
  "estimatedCost": 16.0,
  "mock": true
}
```

| Field | Type | Always present? | Meaning |
|---|---|---|---|
| `startLocation.address` | string | yes | Always the request's address. |
| `quests` | array | yes | At least one stop, at most 10, in visiting order. |
| `quests[].location.name` | string | yes | Place name from Snowflake. |
| `quests[].location.address` | string | yes | Place address from Snowflake. |
| `quests[].location.closingTime` | string | yes | Local closing time, usually `"HH:MM"` (24-hour). |
| `quests[].arrivalTime` | string | yes | Local `"HH:MM"` (24-hour). |
| `quests[].departureTime` | string | yes | Local `"HH:MM"` (24-hour), before the place closes. |
| `quests[].travelDistance` | number | yes | Miles from the previous point to this stop. |
| `endLocation.address` | string | yes | Always the request's address. |
| `totalTime` | integer | no | Estimated minutes for the whole trip, including the return. |
| `totalDistance` | number | no | Estimated miles, including the return. |
| `estimatedCost` | number | no | Estimated spend in US dollars. |
| `mock` | `true` | no | Only present when fake demo data was used. Show a "demo" label if it is. |

Things the server guarantees (it checks them, not just the model):

- Every stop is one of the 10 places Snowflake returned. There are no invented places and no repeats.
- Times are in order, and you leave each stop before it closes.
- The quest starts at the server's current local time (`QUEST_TIMEZONE`, default `America/Los_Angeles`).

Time and budget are targets the model tries to meet. They are not hard limits, so
compare `totalTime` and `estimatedCost` with what the user asked for if that matters to you.

### Errors

Every error uses the same shape:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Human-readable message, safe to show users.",
    "requestId": "f560a1fae5bc4d5794f6339002481854",
    "details": "optional, depends on the error"
  }
}
```

`requestId` is also sent as the `x-request-id` response header. Include it in bug reports.

| Status | `code` | When | Retry? |
|---|---|---|---|
| `400` | `VALIDATION_ERROR` | Missing/invalid fields, or malformed JSON | No, fix the request |
| `413` | `VALIDATION_ERROR` | Body larger than 16 KB | No |
| `422` | `NO_FEASIBLE_ROUTE` | No stop fits the time, budget and opening hours | Ask the user to loosen limits |
| `429` | `RATE_LIMITED` | Too many requests from this IP (default 30/min) | After `retry-after` seconds |
| `502` | `UPSTREAM_INVALID_RESPONSE` | Snowflake or the model returned bad data | Yes, once |
| `503` | `UPSTREAM_UNAVAILABLE` | Snowflake or the model is unreachable | Yes, with backoff |
| `504` | `UPSTREAM_TIMEOUT` | Snowflake or the model took too long | Yes, with backoff |
| `500` | `INTERNAL_ERROR` | Unexpected server error | Yes, once |

Examples:

**400** invalid fields: `details` lists each problem by field path.

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request body.",
    "requestId": "f560a1fae5bc4d5794f6339002481854",
    "details": [
      { "path": "message", "message": "String should have at least 1 character" },
      { "path": "location", "message": "Field required" }
    ]
  }
}
```

**400** malformed JSON:

```json
{ "error": { "code": "VALIDATION_ERROR", "message": "Malformed JSON body.", "requestId": "0f0862b390d24d95a17665f085f9c02e" } }
```

**413** body too large (`requestId` is `null` because the request is rejected before an ID is assigned):

```json
{ "error": { "code": "VALIDATION_ERROR", "message": "Request body is too large.", "requestId": null } }
```

**422** no feasible route: `details.preferences` shows what the server understood, so the UI can suggest changes.

```json
{
  "error": {
    "code": "NO_FEASIBLE_ROUTE",
    "message": "No stops fit your time, budget, and opening hours right now. Try allowing more time or budget, or a different preference.",
    "requestId": "3bc41961f9c9408186d10b66aba2cf3d",
    "details": {
      "preferences": { "desiredTime": 120, "desiredBudget": 25.0, "locationPreference": "coffee, art", "travelMethod": "walk" }
    }
  }
}
```

**429** rate limited (also sends a `retry-after: 59` header):

```json
{ "error": { "code": "RATE_LIMITED", "message": "Too many requests. Try again in 59 seconds.", "requestId": "3534b23a83cd461da0a4541ae41d7eb3" } }
```

**502** bad upstream data: `details.upstream` is `"cursor"` or `"snowflake"`.

```json
{
  "error": {
    "code": "UPSTREAM_INVALID_RESPONSE",
    "message": "The snowflake service returned an invalid response: location list failed validation",
    "requestId": "dbba49c6f2f643f79eeb2b14335b71ac",
    "details": { "upstream": "snowflake", "issues": ["expected exactly 10 locations, received 0"] }
  }
}
```

**503** upstream unavailable:

```json
{ "error": { "code": "UPSTREAM_UNAVAILABLE", "message": "The cursor service is unavailable. Please try again.", "requestId": "445bca87d028436e9d27f4a3436f125a", "details": { "upstream": "cursor" } } }
```

**504** upstream timeout:

```json
{ "error": { "code": "UPSTREAM_TIMEOUT", "message": "The snowflake service timed out. Please try again.", "requestId": "4acb8a0027d543e0b7ea14555c798af4", "details": { "upstream": "snowflake" } } }
```

**500** unexpected (no internal details are returned):

```json
{ "error": { "code": "INTERNAL_ERROR", "message": "Something went wrong. Please try again.", "requestId": "…" } }
```

### Example call

```bash
curl -s -X POST http://localhost:8080/v1/quests \
  -H 'content-type: application/json' \
  -d '{"message":"2 hours, $25, coffee and art, walking","location":{"address":"123 Main St, Pomona, CA"}}'
```

For a complete frontend client, see [Using the API from the frontend](#using-the-api-from-the-frontend).

---

## Using the API from the frontend

### 1. Setup

- **Base URL:** read it from frontend config, for example `VITE_API_BASE_URL` (Vite) or
  `NEXT_PUBLIC_API_BASE_URL` (Next.js). Use `http://localhost:8080` locally.
- **CORS:** the backend must list your frontend origin in `CORS_ORIGINS`, for example
  `CORS_ORIGINS=http://localhost:3000,http://localhost:5173`. If the browser console shows
  a CORS error, this setting is the cause.
- **No secrets in the browser:** the frontend never needs Cursor or Snowflake keys. Only call
  this API.

### 2. The user journey

```text
[Form: message + start address]
        │  POST /v1/quests
        ▼
[Loading: "Planning your quest…"]   (several seconds, sometimes ~30 s)
        │
        ├── 200 → show the route: start → stop 1 → stop 2 … → back to start
        ├── 400 → show field errors next to the inputs
        ├── 422 → "Nothing fits" + suggest more time/budget (use details.preferences)
        ├── 429 → "Too many requests, try again in N s" (retry-after header)
        └── 5xx → "Something went wrong" + a Try again button
```

### 3. TypeScript types

These mirror `api/app/domain/types.py`. You can also generate them from `GET /openapi.json`.

```ts
export interface QuestRequest {
  message: string;              // 1–2000 chars
  location: { address: string } // 3–300 chars
}

export interface Location {
  name: string;
  address: string;
  closingTime: string;          // usually "HH:MM", 24-hour, local time
}

export interface Quest {
  location: Location;
  arrivalTime: string;          // "HH:MM", 24-hour, local time
  departureTime: string;        // "HH:MM", 24-hour, local time
  travelDistance: number;       // miles from the previous point
}

export interface QuestRoute {
  startLocation: { address: string };
  quests: Quest[];
  endLocation: { address: string };
  totalTime?: number;           // minutes
  totalDistance?: number;       // miles
  estimatedCost?: number;       // US dollars
  mock?: true;                  // demo data: show a "Demo" badge
}

export type ApiErrorCode =
  | "VALIDATION_ERROR" | "NO_FEASIBLE_ROUTE" | "RATE_LIMITED"
  | "UPSTREAM_INVALID_RESPONSE" | "UPSTREAM_UNAVAILABLE" | "UPSTREAM_TIMEOUT"
  | "NOT_FOUND" | "INTERNAL_ERROR";

export interface ApiErrorBody {
  error: { code: ApiErrorCode; message: string; requestId: string | null; details?: unknown };
}
```

### 4. API client

```ts
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8080";

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: ApiErrorCode | "NETWORK_ERROR",
    message: string,
    public requestId: string | null = null,
    public details?: unknown,
    public retryAfterSeconds?: number,
  ) {
    super(message);
  }
}

export async function createQuest(req: QuestRequest, signal?: AbortSignal): Promise<QuestRoute> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}/v1/quests`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: req.message.trim(), location: { address: req.location.address.trim() } }),
      // The server retries the model internally, so allow up to ~2 minutes.
      signal: signal ?? AbortSignal.timeout(120_000),
    });
  } catch (err) {
    const name = (err as Error).name;
    if (name === "AbortError") throw err; // user cancelled
    if (name === "TimeoutError") {
      throw new ApiError(0, "NETWORK_ERROR", "Planning took too long. Please try again.");
    }
    throw new ApiError(0, "NETWORK_ERROR", "Can't reach the server. Check your connection and try again.");
  }

  if (res.ok) return (await res.json()) as QuestRoute;

  const body = (await res.json().catch(() => null)) as ApiErrorBody | null;
  const retryAfter = Number(res.headers.get("retry-after")) || undefined;
  throw new ApiError(
    res.status,
    body?.error.code ?? "INTERNAL_ERROR",
    body?.error.message ?? "Something went wrong. Please try again.",
    body?.error.requestId ?? res.headers.get("x-request-id"),
    body?.error.details,
    retryAfter,
  );
}
```

### 5. Handling each result

```ts
try {
  setLoading(true);
  const route = await createQuest({ message, location: { address } });
  setRoute(route);
} catch (e) {
  if (!(e instanceof ApiError)) return; // aborted
  switch (e.code) {
    case "VALIDATION_ERROR": {
      // details is [{ path: "message" | "location.address" | ..., message }]
      const fieldErrors = Array.isArray(e.details) ? e.details : [];
      setFieldErrors(Object.fromEntries(fieldErrors.map((d: any) => [d.path, d.message])));
      break;
    }
    case "NO_FEASIBLE_ROUTE": {
      // details.preferences shows what the server understood, e.g. { desiredTime: 30, desiredBudget: 5, ... }
      const prefs = (e.details as any)?.preferences;
      showMessage(`${e.message}${prefs ? ` (We understood: ${prefs.desiredTime} min, $${prefs.desiredBudget}.)` : ""}`);
      break;
    }
    case "RATE_LIMITED":
      showMessage(`Too many requests. Try again in ${e.retryAfterSeconds ?? 60} seconds.`);
      break;
    default:
      // 5xx and network errors: e.message is safe to show. Offer a manual "Try again" button.
      showMessage(e.message, { retry: true, reference: e.requestId });
  }
} finally {
  setLoading(false);
}
```

### 6. Rules of thumb

- **Disable the submit button while a request is in flight.** Each request runs the model and
  Snowflake, so it costs money and counts toward the rate limit.
- **Don't auto-retry in a loop.** The server already retries Cursor. For `502`/`503`/`504`,
  show a "Try again" button. Never retry `400` or `422` without the user changing something.
- **Cancel on navigation.** Pass an `AbortController` signal and call `abort()` when the user
  leaves the page or edits and resubmits.
- **Show error messages as-is.** `error.message` is written for users and never contains
  internal details. Show `requestId` small (for example "Ref: 3bc4…") so bugs can be traced.
- **Keep the request in frontend state.** There is no GET route to fetch the message or
  address later, and the response does not echo the message. Store what the user typed if
  you need to show "You asked for: …".

### 7. Rendering the route

- **Order:** draw `startLocation` → each `quests[i]` in array order → `endLocation`. Start and
  end are always the address the user typed.
- **Times** are plain `"HH:MM"` strings in the server's time zone (`America/Los_Angeles`
  by default). Show them as-is, or format them, for example `"13:05"` → `1:05 PM`. Don't
  parse them as dates in the browser's time zone.
- **Per-stop card:** name, address, `arrivalTime`–`departureTime`, "Closes `closingTime`",
  and `travelDistance` miles from the previous point.
- **Summary:** `totalTime` minutes, `totalDistance` miles, `estimatedCost` dollars. These may
  be missing; hide the row instead of showing `undefined`. Label them as estimates.
- **Demo badge:** if `mock === true`, clearly show that the places are demo data and not real.
- **Maps:** the API returns addresses, not coordinates. Geocode them in the frontend with your
  map provider, or ask for coordinates to be added to the API.

```ts
const formatClock = (hhmm: string) => {
  const [h, m] = hhmm.split(":").map(Number);
  if (Number.isNaN(h) || Number.isNaN(m)) return hhmm; // not a clock time, show as-is
  return `${((h + 11) % 12) + 1}:${String(m).padStart(2, "0")} ${h < 12 ? "AM" : "PM"}`;
};
```

---

## Built-in docs routes

FastAPI provides these automatically. They are turned off when `APP_ENV=production`.

| Method | Path | Returns |
|---|---|---|
| `GET` | `/docs` | Swagger UI page for trying the API in a browser |
| `GET` | `/docs/oauth2-redirect` | Helper page used by Swagger UI |
| `GET` | `/openapi.json` | OpenAPI 3 schema (can generate frontend types from it) |

---

## Anything else

Unknown paths return `404`:

```json
{ "error": { "code": "NOT_FOUND", "message": "Route not found.", "requestId": "30a7b4b7b52242b59a3c3ea90deb6c10" } }
```

A known path with the wrong method (for example `GET /v1/quests`) returns `405` with
`"code": "VALIDATION_ERROR"` and `"message": "Method Not Allowed"`.

Every response includes an `x-request-id` header, except the `413` too-large response.
