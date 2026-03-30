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

## MVP coverage in this scaffold

- monorepo structure
- landing and pricing pages
- authenticated dashboard shell
- onboarding/profile/watchlist/checklist/trade/report/billing workflows
- SQLAlchemy models aligned to the startup brief schema
- Pydantic and Zod schemas for report payloads
- job-based report pipeline, CSV import validation, and Stripe-ready billing scaffolding

## Next implementation steps

1. Expand billing from stub-safe local mode into live Stripe checkout and webhook deployment config
2. Add token usage and per-report cost instrumentation around the live LLM path
3. Extend automated tests into hosted-environment and browser-level workflows
