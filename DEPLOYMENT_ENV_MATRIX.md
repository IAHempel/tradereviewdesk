# TradeReviewDesk Deployment Env Matrix

Use this file as the source of truth when you configure production hosting for:

- Vercel
- Railway
- Clerk
- Stripe
- OpenAI

Recommended production domains:

- Web app: `https://app.tradereviewdesk.com`
- API: `https://api.tradereviewdesk.com`

## Vercel

Project target:

- [apps/web](C:\Users\shado\CodexProjects\Trade_NOC\apps\web)

Set these environment variables in Vercel:

| Variable | Example value | Required | Notes |
| --- | --- | --- | --- |
| `APP_ENV` | `production` | Yes | Enables production-safe behavior in the web app. |
| `NEXT_PUBLIC_APP_URL` | `https://app.tradereviewdesk.com` | Yes | Public app URL used by the frontend. |
| `API_BASE_URL` | `https://api.tradereviewdesk.com` | Yes | Server-side base URL for the Next proxy routes. |
| `AUTH_MODE` | `clerk` | Yes | Must be `clerk` in production. |
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | `pk_live_...` | Yes | Public Clerk browser key. |
| `CLERK_SECRET_KEY` | `sk_live_...` | Yes | Used by the web server for Clerk SSR/session helpers. |
| `AUTH_INTERNAL_SHARED_SECRET` | `long-random-secret` | Yes | Must exactly match Railway API value. |

Optional:

| Variable | Example value | Notes |
| --- | --- | --- |
| `PORT` | `3000` | Usually managed by Vercel, not required manually. |

## Railway API

Service target:

- [apps/api](C:\Users\shado\CodexProjects\Trade_NOC\apps\api)

Set these environment variables in Railway:

| Variable | Example value | Required | Notes |
| --- | --- | --- | --- |
| `APP_ENV` | `production` | Yes | Required for fail-closed production behavior. |
| `PORT` | `8000` | Yes | Railway may override this automatically. |
| `APP_URL` | `https://app.tradereviewdesk.com` | Yes | Used for billing return URLs and app-aware server behavior. |
| `DATABASE_URL` | `postgresql+psycopg://...` | Yes | Railway Postgres connection string. |
| `REDIS_URL` | `redis://default:...` | Recommended | Optional for current MVP, but recommended for parity. |
| `PERSISTENCE_MODE` | `database` | Yes | Production should remain database-backed. |
| `AUTH_MODE` | `clerk` | Yes | Must be `clerk` in production. |
| `AUTH_INTERNAL_SHARED_SECRET` | `long-random-secret` | Yes | Must exactly match Vercel. |
| `CORS_ORIGINS` | `https://app.tradereviewdesk.com` | Yes | Current config accepts a single origin string. |
| `LLM_API_KEY` | `sk-proj-...` | Yes | OpenAI API key for live report generation. |
| `LLM_MODEL_NAME` | `gpt-4.1-mini` | Yes | Recommended starting model. |
| `LLM_REQUEST_TIMEOUT_SECONDS` | `30` | Recommended | Can remain `30` to start. |
| `STRIPE_SECRET_KEY` | `sk_live_...` | Yes for live billing | Required for checkout, portal, and webhooks. |
| `STRIPE_WEBHOOK_SECRET` | `whsec_...` | Yes for live billing | Must match the live Stripe webhook endpoint. |
| `STRIPE_PRICE_ID_PRO` | `price_...` | Yes for live billing | Live Stripe price ID for Pro. |
| `STRIPE_PRICE_ID_ELITE` | `price_...` | Yes for live billing | Live Stripe price ID for Elite. |
| `STRIPE_CHECKOUT_SUCCESS_PATH` | `/app/settings?billing=success` | Recommended | App-relative success path. |
| `STRIPE_CHECKOUT_CANCEL_PATH` | `/pricing?billing=cancelled` | Recommended | App-relative cancel path. |
| `STRIPE_BILLING_PORTAL_RETURN_PATH` | `/app/settings?billing=manage` | Recommended | App-relative portal return path. |

## Clerk

Clerk dashboard checklist:

- Set production app domain to `app.tradereviewdesk.com`
- Add allowed redirect URLs for:
  - `https://app.tradereviewdesk.com/login`
  - `https://app.tradereviewdesk.com/signup`
  - `https://app.tradereviewdesk.com/app/dashboard`
- Add any required after-sign-in / after-sign-up redirects to:
  - `https://app.tradereviewdesk.com/app/dashboard`

Values to copy into Vercel/Railway:

| Variable | Goes where |
| --- | --- |
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | Vercel |
| `CLERK_SECRET_KEY` | Vercel and Railway if API-side Clerk verification is added later |

## Stripe

Stripe dashboard checklist:

- Create live products/prices for:
  - Pro
  - Elite
- Copy live price IDs into Railway:
  - `STRIPE_PRICE_ID_PRO`
  - `STRIPE_PRICE_ID_ELITE`
- Create a live webhook endpoint:
  - `https://api.tradereviewdesk.com/api/v1/billing/webhooks/stripe`

Subscribe these webhook events:

- `checkout.session.completed`
- `customer.subscription.created`
- `customer.subscription.updated`
- `customer.subscription.deleted`

Copy these values into Railway:

| Variable | Source |
| --- | --- |
| `STRIPE_SECRET_KEY` | Stripe Developers > API keys |
| `STRIPE_WEBHOOK_SECRET` | Stripe Developers > Webhooks |
| `STRIPE_PRICE_ID_PRO` | Stripe product/price config |
| `STRIPE_PRICE_ID_ELITE` | Stripe product/price config |

## OpenAI

Copy into Railway:

| Variable | Recommended value |
| --- | --- |
| `LLM_API_KEY` | your live OpenAI API key |
| `LLM_MODEL_NAME` | `gpt-4.1-mini` |
| `LLM_REQUEST_TIMEOUT_SECONDS` | `30` |

## DNS

Recommended records:

| Host | Target |
| --- | --- |
| `app.tradereviewdesk.com` | Vercel-assigned target |
| `api.tradereviewdesk.com` | Railway-assigned target |

Keep the root domain free for a later marketing/homepage choice unless you already want the main site there.

## Release Checklist

1. Push the latest repo state to GitHub.
2. Apply database migrations in the hosted API environment.
3. Configure Railway env vars from the matrix above.
4. Configure Vercel env vars from the matrix above.
5. Attach `app.tradereviewdesk.com` to Vercel.
6. Attach `api.tradereviewdesk.com` to Railway.
7. Configure Clerk production domain and redirects.
8. Configure Stripe live prices and live webhook endpoint.
9. Run one hosted dry run:
   - sign up
   - sign in
   - save profile
   - create checklist
   - create/import trade
   - generate premarket
   - generate debrief
   - generate weekly review
   - run billing checkout
   - confirm webhook subscription update
10. Only then open access to real users.
