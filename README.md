# TradeReviewDesk MVP Scaffold

TradeReviewDesk is an AI-powered workflow platform for self-directed traders. This repository scaffolds the first production-minded MVP from the startup brief in `trade_noc_startup_brief_and_codex_build_plan.md`.

## What is included

- `apps/web`: Next.js marketing site plus authenticated app shell
- `apps/api`: FastAPI backend scaffold with route groups, models, and report service stubs
- `packages/schemas`: shared TypeScript schemas for AI report payloads
- `packages/types`: shared product-facing types
- `packages/ui`: simple reusable UI primitives for the web app
- `packages/config`: shared constants and navigation metadata
- `infra`: local Docker services for Postgres and Redis

## Product boundaries

TradeReviewDesk is not a signal service, not a brokerage, and not an auto-execution tool. The UI and API scaffolds intentionally frame outputs as workflow support, review assistance, and process discipline.

The Agent Desk (below) keeps that boundary: it rehearses your rules with paper fills, on a synthetic tape or real historical bars, and has no path to a broker.

## Quick start

### Web app

1. Ensure Node.js 24+ is installed
2. Copy `.env.example` to `.env.local` as needed
3. Run `corepack pnpm install`
4. Run `npm run dev:web`

### Auth setup

- Leave `AUTH_MODE=disabled` for the current single-user local demo path
- Set `AUTH_MODE=clerk` to enable production auth wiring
- Add `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` and `CLERK_SECRET_KEY` for the web app
- Set the same `AUTH_INTERNAL_SHARED_SECRET` in both the web and API environments so the Next server can sign user identity for FastAPI
- When `AUTH_MODE=clerk`, `/app/*` and the web proxy API routes require an authenticated Clerk session
- In production, auth now fails closed: the app should not be published with `AUTH_MODE=disabled` or a placeholder `AUTH_INTERNAL_SHARED_SECRET`

### Billing setup

- Billing now reads Stripe configuration from the shared env file
- Local development stays safe in stub mode when `STRIPE_SECRET_KEY` or the Stripe price IDs still use placeholder values
- For live billing, set:
  - `APP_URL`
  - `STRIPE_SECRET_KEY`
  - `STRIPE_WEBHOOK_SECRET`
  - `STRIPE_PRICE_ID_PRO`
  - `STRIPE_PRICE_ID_ELITE`
- The web pricing page and app settings page both use the same billing API routes
- Premium workflow gating currently applies to checklist creation/runs plus debrief and weekly-review generation
- In production, Stripe now fails closed: checkout, portal, and webhook routes should not be published with placeholder billing configuration

### LLM provider setup

- Report generation now uses the OpenAI provider path when `LLM_API_KEY` is set to a real key
- Recommended starting model:
  - `LLM_MODEL_NAME=gpt-4.1-mini`
- Optional timeout control:
  - `LLM_REQUEST_TIMEOUT_SECONDS=30`
- If `LLM_API_KEY` is still a placeholder, the app falls back to the deterministic local provider so local scaffolding stays usable
- The report pipeline still preserves schema validation, retry-on-malformed-output, and compliance-oriented prompting
- In production, report generation now fails closed if `LLM_API_KEY` is still placeholder or missing

### Persistence modes

- `PERSISTENCE_MODE=database` is now the default and expected local/prod runtime path
- `PERSISTENCE_MODE=file` is available as an explicit recovery/dev fallback when you do not want to run Postgres
- The legacy JSON store reset script still works for file mode:
  `.\.venv\Scripts\python.exe apps\api\scripts\reset_state.py --reset`

### API app

1. Create a Python 3.11+ virtual environment
2. Install backend requirements from `apps/api/requirements.txt`
3. Copy `.env.example` values into your API environment
4. Start local dependencies with `docker compose -f infra/docker-compose.yml up -d`
   This project maps Postgres to `localhost:55432` and Redis to `localhost:56379` so it can coexist with other local stacks.
5. Run `uvicorn app.main:app --reload --app-dir apps/api`
6. Run migrations from the API directory:
   `cd apps/api`
   `..\.venv\Scripts\python.exe -m alembic -c alembic.ini upgrade head`
7. Optional but recommended for local demo data:
   `.\.venv\Scripts\python.exe apps\api\scripts\seed_database.py --reset-demo-user`
8. If auth is enabled, set `AUTH_MODE=clerk` and the same `AUTH_INTERNAL_SHARED_SECRET` used by the web app

### Runtime health checks

- Liveness:
  - API root: `/healthz`
  - Versioned API: `/api/v1/health`
- Readiness:
  - API root: `/readyz`
  - Versioned API: `/api/v1/ready`
- In `PERSISTENCE_MODE=database`, readiness will fail until the database is reachable
- Redis is reported in the readiness payload for visibility, but database availability is the primary readiness gate for the current MVP

### Regression test suite

- Run the current API launch-safety regression suite from the repo root:
  `npm run test:api`
- The suite covers auth enforcement, user isolation, billing gates, checklist flows, CSV import, and report generation behavior against isolated local test state

### Deployment checklist

See [DEPLOYMENT_ENV_MATRIX.md](C:\Users\shado\CodexProjects\Trade_NOC\DEPLOYMENT_ENV_MATRIX.md) for the exact hosted variable matrix for Vercel, Railway, Clerk, Stripe, OpenAI, and DNS.

For any hosted environment, use absolute HTTPS URLs and configure the web and API independently.

1. Web deployment
   - Recommended path: Vercel or any Node host that supports Next.js 15
   - Required env:
     - `NEXT_PUBLIC_APP_URL=https://app.tradereviewdesk.com`
     - `API_BASE_URL=https://api.tradereviewdesk.com`
     - auth and billing vars as needed
   - The web app includes a Node-host-friendly Dockerfile and production build/start path for non-Vercel deployments
2. API deployment
   - Recommended path: Render, Fly.io, Railway, or a container-capable host
   - Required env:
     - `APP_ENV=production`
     - `APP_URL=https://app.tradereviewdesk.com`
     - `PORT=8000` or the host-provided port
     - `DATABASE_URL`
     - `REDIS_URL`
     - `CORS_ORIGINS=https://app.tradereviewdesk.com`
     - `AUTH_INTERNAL_SHARED_SECRET`
     - auth, billing, and LLM vars as needed
   - Health check target: `/readyz`
3. Database and cache
   - Use managed Postgres for production
   - Redis is optional for the current MVP, but provision it now if you want parity with the existing env shape and room for background jobs
4. Migrations
   - Run before promoting a deploy:
     `cd apps/api`
     `..\..\.venv\Scripts\python.exe -m alembic -c alembic.ini upgrade head`
5. Seed data
   - Do not run the demo seed script in production
   - Use the seed/reset scripts only for local development and staging resets

### Container entrypoints

- `apps/web/Dockerfile` builds and serves the production Next.js app for self-hosting
- `apps/api/Dockerfile` provides a simple FastAPI container baseline
- `.dockerignore` keeps local caches, builds, and secrets out of image contexts

### Billing webhook notes

- Stripe webhooks post to `/api/v1/billing/webhooks/stripe`
- The API currently handles:
  - `checkout.session.completed`
  - `customer.subscription.created`
  - `customer.subscription.updated`
  - `customer.subscription.deleted`
- In stub mode, checkout and portal actions redirect back into the app so billing UX can still be exercised locally without live Stripe calls

### Reset local API state

- Show the active seed/store files:
  `.\.venv\Scripts\python.exe apps\api\scripts\reset_state.py --show-paths`
- Reset the persisted local API store back to the seeded demo data:
  `.\.venv\Scripts\python.exe apps\api\scripts\reset_state.py --reset`
- Reseed the Postgres-backed demo user after migrations:
  `.\.venv\Scripts\python.exe apps\api\scripts\seed_database.py --reset-demo-user`

### CSV trade import expectations

- Upload UTF-8 CSV files with a header row
- Supported header aliases are broker-agnostic and currently include:
  `date`/`trade_date`, `symbol`/`ticker`, `side`/`action`, `qty`/`quantity`, `entry_price`, `exit_price`, `pnl`, `fees`, `tags`, and `notes`
- Side values such as `buy` and `long` normalize to `long`; `sell` and `short` normalize to `short`
- Asset type is optional and defaults to `stock`; supported values include `stock`, `option`, and `other`
- Valid rows are imported immediately and invalid rows are returned with row-level errors

## Agent Desk (paper)

`/app/desk` runs a six-agent pipeline over your rules, bar by bar, and replays it like a live session:

| Agent | Job |
|---|---|
| Scout | Scans each closed 5-minute bar for breakouts, liquidity sweeps that reclaim, trend pullbacks, and mean-reversion stretches |
| Filter | Kills setups that break your hard rules: opening/closing windows, daily loss limit, loss-streak cooldown, symbol already working, max open positions, stop distance, minimum reward:risk |
| Analyst | Scores survivors and keeps a Beta-posterior win rate per setup: a stated starting assumption, plus your tagged journal trades, plus this run's results |
| Risk | Sizes each trade with the smaller of your risk cap and fractional Kelly, splits buying power across open slots, and trails stops (tighten only) |
| Executor | Paper fills at the next bar's open with slippage and fees; stop is checked before target inside a bar; flat by the bell |
| Logger | Records a reason for every decision so a run can be audited |

What makes it honest rather than a screenshot generator:

- **Two tapes.** The synthetic tape (`apps/api/app/services/desk/market.py`) is a seeded regime-switching random walk with no edge baked in, so results show how your rules behave in noise. The Polygon tape replays real split-adjusted 5-minute bars for completed sessions (see below).
- **No lookahead.** Setups are detected on a closed bar and filled at the next open; tests assert it.
- **Stops never widen.** The "stops widened" stat is audited per trade, not hard-coded.
- **Deterministic.** Same seed and rules give the identical run, so sessions can be replayed and compared.
- **Expectancy fan.** A 500-path bootstrap of the run's per-trade returns shows the spread of the next 100 trades, and a "screenshot reality check" turns viral "$142 → $2,870 in 6 days" claims into the daily return they imply.

API: `GET /api/v1/desk/defaults`, `POST /api/v1/desk/runs`, `GET /api/v1/desk/runs`, `GET /api/v1/desk/runs/{id}`. Runs persist in the `desk_runs` table (migration `0009_desk_runs`), or in the JSON store in file mode (last 5 per user).

API also exposes `GET /api/v1/desk/sources`, which reports whether historical data is available.

### Historical replays (Polygon)

Set `POLYGON_API_KEY` on the API (the free plan works), then choose **Polygon historical** under Desk rules → Market data and pick the last session to replay.

- Bars come from Polygon's `/v2/aggs` 5-minute aggregates, split-adjusted, with the key sent as a bearer header.
- Only NYSE regular hours are replayed (09:30–16:00 ET). Holidays drop out because they have no bars, and the scheduled 1:00 pm early closes (July 3, the day after Thanksgiving, December 24) replay as shorter sessions.
- One extra trading day before the first session is loaded as indicator warmup and never traded.
- A 5-minute slot with no trades becomes a flat, zero-volume bar at the last close. Symbols with fewer than half their slots traded on any replayed day are dropped, and the Logger says so.
- Each symbol's window is cached on disk (`MARKET_DATA_CACHE_DIR`) once fetched, so replays cost no requests. If Polygon's 5-requests-a-minute free limit is hit, symbols already loaded stay cached and the next run picks up the rest.
- Fills are still simulated at the next bar's open with your slippage and fees, so historical results show how the rules behaved on those days, not what live execution would have returned.

The agents only see `Bar` objects through the `MarketFeed` protocol in `market.py`, so another provider fits behind the same shape.

## MVP coverage in this scaffold

- monorepo structure
- landing and pricing pages
- authenticated dashboard shell
- onboarding/profile/watchlist/checklist/trade/report/billing workflows
- SQLAlchemy models aligned to the startup brief schema
- Pydantic and Zod schemas for report payloads
- job-based report pipeline, CSV import validation, and Stripe-ready billing scaffolding
- paper Agent Desk with a synthetic tape or Polygon historical bars, six-agent pipeline, replayable runs, and Monte Carlo expectancy fan

## Next implementation steps

1. Expand billing from stub-safe local mode into live Stripe checkout and webhook deployment config
2. Add token usage and per-report cost instrumentation around the live LLM path
3. Extend automated tests into hosted-environment and browser-level workflows
4. Agent Desk: decide whether a broker paper-trading API belongs in scope before anything touches live execution
