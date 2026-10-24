# Deployment

Status (2026-10-23): the code is deployment-ready and the full stack was verified **locally
in Docker** (production mode, live Snowflake + Cortex): all containers healthy, the API
rejected requests without its token, and all 27 Playwright tests passed against it. **No
hosted deployment exists yet.** Selected hosts: Vercel (web), Render (API), MongoDB Atlas (database). Steps marked
*unverified* have not been run.

## What gets deployed

| Piece | Runs as | Needs |
|---|---|---|
| Web app (`web/`, Next.js) | `web/Dockerfile` (standalone Node server, port 3000) | MongoDB, the quest API, Google OAuth client |
| Quest API (`api/`, FastAPI) | `api/Dockerfile` (port 8080, `GET /health`) | Snowflake key-pair login |
| MongoDB | `mongo:7` container or a hosted cluster (e.g. MongoDB Atlas) | persistent storage |
| Snowflake procedure + Cortex models | already deployed in account `LHXLXHN-WY63275` | nothing new; redeploy only after `snowflake/python` changes (`snowflake/scripts/lq.py deploy`) |

Only the web app is public. Browsers never call the API: the Next.js server calls it with
`Authorization: Bearer <token>`, and the API refuses `/v1/*` without that token
(`API_AUTH_TOKEN`, required when `APP_ENV=production`) so strangers can't spend Snowflake credits.

## Configuration (names only; values go in the host's secret settings)

API (template: `.env.example`): `APP_ENV=production`, `API_AUTH_TOKEN` (>= 32 chars,
`openssl rand -hex 32`), `AI_PROVIDER=snowflake`, `DATA_PROVIDER=snowflake`, `SNOWFLAKE_ACCOUNT`,
`SNOWFLAKE_USER`, `SNOWFLAKE_ROLE=LQ_APP_RO`, `SNOWFLAKE_WAREHOUSE`, `SNOWFLAKE_DATABASE`,
`SNOWFLAKE_SCHEMA`, and **either** `SNOWFLAKE_PRIVATE_KEY_PATH` (a mounted file) **or**
`SNOWFLAKE_PRIVATE_KEY` (the PEM text; literal `\n` is fine), plus
`SNOWFLAKE_PRIVATE_KEY_PASSPHRASE` if the key is encrypted. Keep `SNOWFLAKE_QUERY_TIMEOUT_S=40`
(route planning with `llama3.3-70b` takes ~20 s). Set `TRUST_PROXY=true` only behind a proxy.

Web (template: `web/.env.example`): `AUTH_SECRET` (new value per environment, `npx auth secret`),
`AUTH_GOOGLE_ID`, `AUTH_GOOGLE_SECRET`, `DATABASE_URL`, `QUEST_API_URL`, `QUEST_API_TOKEN`
(= the API's `API_AUTH_TOKEN`), `AUTH_TRUST_HOST=true` (anywhere except Vercel), and
`TRUST_PROXY=true` behind a proxy so sign-in rate limits use the real client IP.

Google Cloud Console: add `https://<your-domain>/api/auth/callback/google` to the OAuth
client's authorized redirect URIs, or Google sign-in fails on the deployed site.

## Option A: one server with Docker Compose (verified locally)

Any Linux VM with Docker (e.g. a small cloud VM) runs the whole stack from `docker-compose.yml`.

1. Install Docker, clone the repo, and copy the Snowflake `.p8` key onto the server
   (outside the repo, `chmod 600`).
2. Create `.env` from `.env.example` (production values above; `SNOWFLAKE_PRIVATE_KEY_PATH`
   = the key's path on the server) and `web/.env.local` from `web/.env.example`.
   Compose overrides `DATABASE_URL`, `QUEST_API_URL`, `QUEST_API_TOKEN`, and the key path.
3. `docker compose up -d --build`, then `docker compose ps` until all three are `healthy`.
4. Put HTTPS in front of port 3000 (e.g. Caddy: `your-domain { reverse_proxy localhost:3000 }`)
   and set `TRUST_PROXY=true` for the web app. Auth.js cookies are `Secure` on HTTPS.
5. Run the smoke check below.

Verified 2026-10-23 on macOS Docker Desktop at commit `1420c2e` + these changes (port 3100):
healthy containers, 401 without token, live quest in ~21 s, `/docs` hidden, 27/27 Playwright.

## Option B (selected 2026-10-23): Vercel + Render + MongoDB Atlas (unverified)

Web app on **Vercel** (root directory `web`), quest API on **Render** (`render.yaml`, Docker,
region Ohio), database on **MongoDB Atlas** (free M0). All three deploy from GitHub `main`.
Do them in this order, because each step needs a value from the one before.

1. **Snowflake service user for Render** (least privilege; never put `ERICY`'s key on a host).
   On your Mac: `openssl genrsa 2048 | openssl pkcs8 -topk8 -nocrypt -out ~/.snowflake/keys/lq_api_render.p8`
   and `openssl rsa -in ~/.snowflake/keys/lq_api_render.p8 -pubout`. In a Snowflake worksheet:
   `USE ROLE SECURITYADMIN; CREATE USER IF NOT EXISTS LQ_API_RENDER TYPE = SERVICE DEFAULT_ROLE = LQ_APP_RO DEFAULT_WAREHOUSE = LQ_WH;`
   `ALTER USER LQ_API_RENDER SET RSA_PUBLIC_KEY = '<public key body, no BEGIN/END lines>';`
   `GRANT ROLE LQ_APP_RO TO USER LQ_API_RENDER;` (revoke any time with `DROP USER LQ_API_RENDER;`).
2. **MongoDB Atlas:** create a free M0 cluster, a database user, and under Network Access allow
   `0.0.0.0/0` (Vercel has no fixed IPs on Hobby). Copy the connection string and add the
   database name: `mongodb+srv://USER:PASS@CLUSTER/localquest?retryWrites=true&w=majority`.
   (Vercel's MongoDB Atlas integration can create the cluster too, but it names the variable
   `MONGODB_URI`; the app reads `DATABASE_URL`, so copy the value into `DATABASE_URL`.)
3. **Render (API):** New → Blueprint → this repo. Enter `SNOWFLAKE_USER=LQ_API_RENDER` and paste
   the whole `lq_api_render.p8` text into `SNOWFLAKE_PRIVATE_KEY`. When it's live, open
   `https://<service>.onrender.com/health` (expect `{"status":"ok"}`) and copy the generated
   `API_AUTH_TOKEN` from the service's Environment tab.
4. **Vercel (web):** Add New → Project → import the GitHub repo, set **Root Directory** to `web`
   (framework Next.js is detected). Environment variables (Production): `AUTH_SECRET` (new),
   `AUTH_GOOGLE_ID`, `AUTH_GOOGLE_SECRET`, `DATABASE_URL` (Atlas), `QUEST_API_URL`
   (`https://<service>.onrender.com`), `QUEST_API_TOKEN` (= Render's `API_AUTH_TOKEN`),
   `TRUST_PROXY=true`. Do not set `AUTH_TRUST_HOST` on Vercel. Deploy.
5. **Google OAuth:** add `https://<project>.vercel.app/api/auth/callback/google` (and any custom
   domain) to the OAuth client's authorized redirect URIs.
6. Run the smoke check below against `https://<project>.vercel.app`.

Notes: the quest form's server action may wait up to 90 s for the API; `web/src/app/quests/page.tsx`
sets `maxDuration = 120` (Vercel Hobby allows up to 300 s). Render's free plan sleeps after ~15
minutes idle, so the first quest after a nap can time out: open `/health` a minute before a demo,
or switch `plan` in `render.yaml` to `starter`. Render deploys after GitHub CI passes
(`autoDeployTrigger: checksPass`); Vercel deploys every push to `main` and makes a preview URL
for every branch. Rate limits are in memory per instance (Vercel may run several), so treat them
as best effort.

Record the URLs and who can deploy: Vercel project [TO FILL], Render service [TO FILL],
Atlas cluster [TO FILL].

## Before every deploy

1. CI is green on the commit (`.github/workflows/ci.yml`: API tests, web lint/build/typecheck/
   unit tests with MongoDB, both Docker builds). To make it required, enable branch protection
   for `main` in GitHub settings; the workflow file alone doesn't enforce it.
2. No data migration is needed: MongoDB collections and indexes are created on first use
   (`data/ACCOUNTS.md`); quests saved before Start/Finish existed still load.
3. Note the commit SHA you deploy, the Snowflake `ranking_version` (`osm_hybrid_v6`), and the
   prompt version (`2026-10-23.4`, `api/app/adapters/llm/model_adapter.py`).

## Smoke check (after every deploy)

1. `https://<domain>/` loads; the API health check (`GET /health` -> `{"status":"ok"}`) passes
   on the host. `POST /v1/quests` without the token returns `401`.
2. Register (or sign in with Google), plan "I want food and coffee": a live (not "Demo") route
   from Cal Poly Pomona appears within ~40 s.
3. Start quest, check in at every stop, Finish quest; XP and the quest log update on Profile.
4. A $0 request returns the "nothing fits" explanation, not a fake route.
Record the date, URL, commit, and results under **Result**.

## Rollback

- **Docker Compose:** `git checkout <last good SHA> && docker compose up -d --build`. MongoDB
  data is in the `mongo-data` volume and survives (`docker compose down -v` would delete it).
- **Vercel:** Deployments → the last good production deployment → Instant Rollback.
- **Render:** the service's Events/Deploys list → "Rollback" on the last good deploy.
- **Snowflake ranking:** check out the previous `snowflake/python/lq_snowflake` files and run
  `snowflake/.venv/bin/python snowflake/scripts/lq.py deploy` (code only; data untouched).
- Re-run the smoke check after any rollback.

## Costs and limits

Snowflake: warehouse `LQ_WH` (XS, 60 s auto-suspend, 10-credit resource monitor) plus Cortex
`AI_COMPLETE`/`AI_EMBED` per quest (each quest makes 2-3 model calls). Limits: 10 quests per
player per 10 minutes (web) and `RATE_LIMIT_PER_MINUTE` per IP (API). Rate limits are in memory,
so they reset on restart and aren't shared across multiple instances.

## Result
Record who deployed, when, the commit, the URL, checks that passed or failed, and the demo
URL. Do not describe a planned or simulated step as verified. [TO FILL]

## Demo and submission

This is a proposed script, not a claim of working functionality.

### Short demonstration
1. Explain the problem: finding an affordable, interesting short outing takes effort.
2. Enter interests, time, and budget; omit a field to show its disclosed default.
3. Show Snowflake returning up to 10 candidates and AI proposing a three-stop order;
   show the backend-verified route returned to the frontend as JSON.
4. Explain one grounded challenge and its source place fact.
5. Change a constraint and show a feasible new result or honest infeasibility response.
6. Scan a simulated stop QR, earn a passport stamp, and show the analytics update.
7. Identify Snowflake retrieval/analytics and the actual open-weight model used.

### Evidence for prize entries
- Show a real Snowflake query and resulting application behavior.
- Show AI contribution, model identity, license link, and evaluation examples.
- Publish source with a selected open-source license and reproducible setup.
- Label simulated check-ins/offers/data; do not imply merchant partnerships.
- Confirm event eligibility, submission fields/deadline, and permitted advance work.

### Advance-work record
2026-10-22: project documentation prepared from brainstorming. No application code,
verified business dataset, or deployment created by this documentation task.

### Backup
Record a truthful demo video once the live journey works. If live services fail,
label the recording or offline fixture mode instead of presenting it as live.
