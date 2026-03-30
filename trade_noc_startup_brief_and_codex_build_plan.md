# TradeReviewDesk — Startup Brief, Branding, Pricing, MVP Spec, Landing Page Copy, and Codex Build Plan

## 1) Startup brief

### Working concept
TradeReviewDesk is an AI-powered operations layer for self-directed traders. It helps users run a disciplined trading workflow with structured premarket preparation, session checklists, position/risk reminders, post-close debriefs, and weekly performance reviews.

### Core promise
Your broker helps you place trades. TradeReviewDesk helps you run your process.

### Positioning
TradeReviewDesk is not a signal service, not a copy-trading tool, and not an auto-execution engine. It is a trader workflow platform focused on discipline, consistency, and decision support.

### Problem
Retail traders often fail from process breakdowns rather than lack of information:
- inconsistent premarket planning
- impulsive entries
- poor journaling habits
- weak post-trade review
- limited visibility into concentration and event risk
- no repeatable operating cadence

### Solution
TradeReviewDesk gives users a personal command center for:
- premarket brief generation
- watchlist triage
- checklist-based trade preparation
- risk and exposure reminders
- post-close debriefs
- weekly behavior and setup reviews

### Target users
#### Primary
Self-directed stock and options traders who trade at least weekly and want more structure.

#### Best launch niche
Part-time traders using broker mobile apps and/or desktop tools who want process discipline without building their own journaling and review stack.

### Why it wins
- process-centric rather than chart-centric
- AI handles repetitive review and summarization
- broker-agnostic at launch
- easier to explain and demo than a complex analytics platform
- sticky daily/weekly habit loop

### Initial business model
- Free tier for limited briefs and journals
- Pro subscription for daily workflow tooling
- Elite subscription for advanced analytics and weekly reviews

### Initial revenue thesis
The fastest path is not a massive app. It is a narrow product that creates recurring daily or weekly value through habit-forming outputs.

---

## 2) Brand name options

### Top recommendation: TradeReviewDesk
Why it works:
- immediately conveys the operations-center concept
- memorable, technical, differentiated
- aligns with your network engineering angle

### Other strong options
1. **EdgeBell**  
   Suggests signal, alerts, edge, and monitoring.

2. **PositionOps**  
   Very clear product meaning. Good B2B-style feel.

3. **OpenChecklist**  
   Strong for discipline and routine; less premium sounding.

4. **PremarketOS**  
   Great product feel, though slightly limiting if product expands beyond the morning workflow.

5. **TradeBridge**  
   Broad and accessible, but less differentiated.

6. **EntryGuard**  
   Good for the checklist/risk-control angle.

7. **SessionPilot**  
   Good for traders who want guidance without “advice” language.

8. **RiskRelay**  
   Strong for alerts and exposure monitoring.

9. **ChartOps**  
   Memorable, but may sound too chart-focused.

10. **DisciplineDesk**  
    Descriptive, but less sleek.

### Brand direction
Use **TradeReviewDesk** unless domain constraints are severe.

### Tagline options
- Run your trading like an operating system.
- Your personal ops center for the market.
- Plan better. Trade calmer. Review smarter.
- A control plane for self-directed traders.
- Discipline over noise.

---

## 3) Pricing page copy

# Pricing
## Pick the workflow that fits your trading style
From daily prep to weekly performance reviews, TradeReviewDesk gives you a repeatable system for planning, monitoring, and learning.

### Free
**$0/month**
For trying the workflow before committing.

Includes:
- 1 daily premarket brief per day
- basic watchlist summary
- limited journal entries
- end-of-day recap preview
- 7-day history

CTA: **Start free**

### Pro
**$24/month**
For active traders who want structure every day.

Includes everything in Free, plus:
- full daily premarket brief
- checklist-based trade prep
- full post-close debriefs
- weekly performance review
- setup tagging and behavior notes
- 90-day history
- priority report generation

CTA: **Start Pro**

### Elite
**$59/month**
For traders who want deeper review and tighter risk awareness.

Includes everything in Pro, plus:
- advanced weekly analytics
- concentration and event-risk summaries
- options-aware reminders
- custom rule sets and workflow templates
- exportable performance reports
- longer history and premium support

CTA: **Go Elite**

### Pricing reassurance copy
No trade signals. No copy trading. No hype.
TradeReviewDesk is built to improve process discipline, review quality, and decision support.

### FAQ snippets
**Does TradeReviewDesk tell me what to buy?**  
No. TradeReviewDesk helps you organize your process, review your decisions, and identify behavior patterns.

**Does it connect to my broker?**  
At launch, TradeReviewDesk supports uploads and manual workflows first. Broker integrations can be added later.

**Is this for day traders only?**  
No. It is useful for day traders, swing traders, and options traders who want more structure.

---

## 4) MVP feature spec

## Product goal
Deliver a narrow, useful product that traders will actually use at least 3 times per week.

## MVP success criteria
- users return at least 3 times weekly
- users generate at least 1 post-close debrief weekly
- users report that the product saves time or improves discipline
- at least 10 paid beta users convert from free/manual onboarding

## Core MVP modules

### A. User onboarding
#### Inputs
- name / handle
- trading style: day, swing, options, mixed
- watchlist symbols
- preferred setup types
- biggest challenges (discipline, overtrading, risk sizing, missing entries, etc.)
- optional broker/platform info

#### Outputs
- personalized dashboard state
- initial checklist template
- personalized first-day workflow

### B. Daily Premarket Brief
#### Inputs
- user watchlist
- saved notes from prior sessions
- market calendar/events input
- optional user-entered priorities

#### Outputs
- watchlist triage
- overnight change summary
- what needs attention today
- user reminders and focus notes
- premarket checklist

#### UI sections
- market snapshot
- watchlist changes
- events to watch
- focus checklist

### C. Trade Checklist Engine
#### Inputs
- user-defined or default setup checklist
- manual trade candidate entry

#### Outputs
- completed checklist state
- reason-for-entry note
- warnings for skipped conditions

#### Features
- configurable checklist items
- mandatory note before marking trade as ready
- simple confidence score

### D. Post-Close Debrief
#### Inputs
- uploaded trades CSV or manual trades
- user notes
- checklist completion data

#### Outputs
- summary of day
- deviations from plan
- what went well
- what to improve
- suggested notes for tomorrow

### E. Weekly Review
#### Inputs
- daily debriefs
- trade records
- setup tags
- user notes

#### Outputs
- setup-level performance summary
- repeated mistakes or strengths
- emotional/behavioral pattern notes
- next-week action items

### F. Basic account and history
#### Features
- saved reports
- saved watchlist
- saved checklist templates
- report history
- billing state

## Out of scope for MVP
- live brokerage execution
- automated buy/sell recommendations
- real-time options chain analytics
- community/social features
- complex charting engine
- mobile app native build

## MVP user stories
1. As a trader, I can set my watchlist and style so the dashboard reflects my workflow.
2. As a trader, I can generate a premarket brief that narrows what matters today.
3. As a trader, I can complete a checklist before taking a trade.
4. As a trader, I can upload or enter trades and get a post-close review.
5. As a trader, I can see a weekly summary of recurring mistakes and useful patterns.

## Suggested MVP stack
- Frontend: Next.js + TypeScript + Tailwind
- Backend API: Python FastAPI
- Database: Postgres
- Auth: Clerk or Supabase Auth
- Billing: Stripe
- Background jobs: Celery or Dramatiq / Redis
- AI orchestration: structured prompt pipelines with JSON outputs
- File ingestion: CSV uploads first
- Hosting: Vercel (frontend), Render/Fly/Railway (backend), managed Postgres

## MVP data model (high-level)
- users
- profiles
- watchlists
- checklist_templates
- checklist_runs
- trade_entries
- debrief_reports
- weekly_reports
- subscriptions
- ai_jobs
- audit_logs

---

## 5) Landing page copy

## Hero
### Headline
**Run your trading like an operating system.**

### Subheadline
TradeReviewDesk gives self-directed traders a personal ops center for premarket planning, trade checklists, post-close reviews, and weekly performance insights.

### CTA buttons
- **Start free**
- **See how it works**

### Supporting line
No trade signals. No hype. Just a better process.

---

## Section: The problem
### Heading
Most traders do not need more charts. They need more structure.

### Body
Broker apps help you place trades. They do not help you run a disciplined workflow. TradeReviewDesk turns scattered notes, watchlists, and trade history into a repeatable system for planning, monitoring, and review.

---

## Section: How it works
### Heading
A control plane for your trading day

### Step 1
**Start with a premarket brief**  
See what changed overnight, what matters on your watchlist, and what deserves your attention.

### Step 2
**Use a checklist before entries**  
Define your setup rules and slow down impulsive trades before they happen.

### Step 3
**Review the day with context**  
Turn your trades and notes into a useful post-close debrief.

### Step 4
**Learn from the week**  
See which setups, habits, and mistakes keep repeating.

---

## Section: Features
### Heading
Built for traders who want discipline over noise

- AI-generated daily premarket brief
- checklist-based trade prep
- post-close debriefs in plain English
- weekly performance and behavior reviews
- broker-agnostic workflows at launch
- options-aware reminders in higher tiers

---

## Section: Who it’s for
### Heading
Made for self-directed traders

### Body
TradeReviewDesk is built for traders who already have a broker, already have information, and want a better process for using it.

- part-time traders
- stock and options traders
- mobile-first broker users
- traders building consistency

---

## Section: Trust / boundary language
### Heading
Decision support, not investment advice

### Body
TradeReviewDesk does not tell you what to buy or sell. It helps you organize your workflow, review your behavior, and improve consistency over time.

---

## Section: Pricing teaser
### Heading
Start free. Upgrade when the workflow clicks.

### Body
Use the free plan to test your routine, then unlock full premarket briefs, debriefs, and weekly reviews with Pro.

CTA: **View pricing**

---

## Footer CTA
### Heading
Build a trading routine that actually compounds

### CTA
**Start free**

---

## 6) Build plan to hand off to Codex

# Project brief for Codex
Build an MVP web app called **TradeReviewDesk**. The product is an AI-powered workflow platform for self-directed traders. It is not a signal engine, not a copy-trading system, and not an execution platform. The app helps users create a structured daily trading process with premarket briefs, trade checklists, post-close debriefs, and weekly performance reviews.

## Product requirements
### User goals
- generate a daily premarket brief from their watchlist and notes
- use a checklist before entering trades
- upload or manually enter trades for post-close review
- receive a weekly review of patterns, strengths, and mistakes

### Core pages
1. Landing page
2. Auth pages (sign up / sign in)
3. Dashboard
4. Premarket Brief page
5. Checklists page
6. Post-Close Debrief page
7. Weekly Review page
8. History / Reports page
9. Billing / Settings page

### Design direction
- dark mode by default
- blue/green accent highlights
- polished, technical, dashboard feel
- glassmorphism influences where appropriate
- clean card layouts, clear visual hierarchy
- responsive desktop-first design, decent mobile support

### Preferred stack
- Next.js + TypeScript frontend
- Tailwind CSS
- shadcn/ui components
- FastAPI backend
- Postgres database
- Redis-backed background jobs if needed
- Stripe billing
- Clerk or Supabase auth

### Non-functional requirements
- modular architecture
- strongly typed frontend API contracts
- clear env var management
- audit logging for AI-generated reports
- graceful handling of failed AI jobs
- no fake market data in production code

## Functional requirements in detail

### 1. Authentication and onboarding
Implement account creation and login. After signup, show an onboarding flow that collects:
- trading style
- watchlist symbols
- preferred setup types
- biggest pain points
- optional broker/platform

Store this in the database and use it to personalize report prompts.

### 2. Dashboard
Dashboard should show:
- today’s premarket brief status
- checklist completion summary
- latest post-close debrief
- latest weekly review
- watchlist snapshot
- upgrade banner for free users

### 3. Premarket Brief generation
User can click a button to generate a daily premarket brief. For MVP, the system should use:
- saved watchlist
- saved notes
- a placeholder/manual events input field
- AI prompt pipeline that returns structured JSON

Render results in cards:
- summary
- watchlist priorities
- key reminders
- checklist for the session

### 4. Checklist engine
Allow users to create and edit checklist templates. A checklist run should be generated for a trading session or a prospective trade. Each checklist item can be checked off. Require a notes field for “reason for entry.” Save completed checklist runs.

### 5. Post-Close Debrief
Allow user to either:
- upload CSV trade history, or
- manually enter trades

Generate an AI-powered post-close review with sections:
- session summary
- what went well
- deviations from plan
- risks taken
- next-day improvements

### 6. Weekly Review
Aggregate trade entries, checklist runs, and debriefs from the last 7 days. Generate a weekly AI report that identifies recurring patterns, strengths, weaknesses, and next actions.

### 7. Billing
Implement Stripe-based subscription gating:
- Free tier: limited reports/history
- Pro tier: full daily briefs, debriefs, weekly reviews
- Elite tier: premium placeholders and higher limits

### 8. History
Provide a history page showing saved reports with filtering by type and date.

### 9. Settings
Allow editing:
- watchlist
- trading style
- checklist templates
- account preferences
- subscription status

## AI implementation requirements
- use provider abstraction so model vendor can be swapped later
- prompts must enforce structured output JSON
- validate model outputs with schema validation
- store raw AI output and parsed result separately
- maintain audit logs for generated reports
- include fallback messaging when generation fails

## Compliance / boundary requirements
Hard-code guardrails into prompts and UI copy:
- do not generate direct buy/sell instructions
- do not claim profitability or guaranteed results
- frame outputs as workflow and review assistance
- include disclaimers where relevant

## Suggested repo structure
- /apps/web
- /apps/api
- /packages/ui
- /packages/types
- /packages/config
- /infra

## Suggested milestones
### Milestone 1
- repo setup
- auth
- db schema
- landing page
- onboarding

### Milestone 2
- dashboard
- checklist CRUD
- premarket brief generation flow

### Milestone 3
- trade entry / CSV upload
- post-close debrief generation
- history page

### Milestone 4
- weekly review generation
- billing integration
- polish and QA

### Milestone 5
- deployable production candidate
- analytics hooks
- basic email notifications

## Engineering expectations
- write production-quality code
- use clean components and reusable patterns
- document setup instructions in README
- include seed data for local dev
- include migration scripts
- include example env file
- include basic test coverage for critical flows

## Output requested from Codex
1. Full MVP codebase
2. README with setup steps
3. Env var template
4. DB schema and migrations
5. Placeholder mock data where live data is not yet connected
6. Clear TODO list for broker integrations and real market/news data

---

## 7) Immediate launch plan

### Phase 0: validation before full app
Before building everything, validate demand with a concierge beta:
- landing page + waitlist
- manual intake form
- manually reviewed AI-generated premarket briefs and debriefs
- collect testimonials and objections
- test pricing sensitivity

### Phase 1: MVP launch
- free tier + pro tier
- narrow onboarding
- premarket brief + debrief + weekly review
- no broker sync required

### Phase 2: retention improvements
- better reminders
- workflow streaks
- improved templates
- options-aware review tools

---

## 8) Recommended next deliverables
1. clickable wireframe / page map
2. database schema in SQL
3. prompt specs for each AI workflow
4. technical architecture diagram
5. launch checklist and beta onboarding plan

---

## 9) Implementation pack

# 9.1 Product page map and wireframe spec

## Global UX principles
- dark-mode first UI
- blue/green accent palette
- glassmorphism used lightly on hero cards, modals, and status panels
- dashboard-first layout
- strong visual hierarchy
- minimal clutter
- primary navigation on left rail for desktop, bottom nav or menu on mobile
- every AI-generated report should show: status, generated timestamp, source inputs, and a clear disclaimer

## App sitemap
### Marketing/public pages
- /
- /pricing
- /how-it-works
- /login
- /signup
- /legal/terms
- /legal/privacy
- /legal/disclaimer

### Authenticated app pages
- /app/dashboard
- /app/premarket
- /app/checklists
- /app/debrief
- /app/weekly-review
- /app/history
- /app/settings/profile
- /app/settings/watchlist
- /app/settings/checklists
- /app/settings/billing

## Navigation structure
### Left sidebar
- Dashboard
- Premarket Brief
- Checklists
- Post-Close Debrief
- Weekly Review
- History
- Settings

### Top bar
- workspace / app logo
- current plan badge
- generate button when relevant
- account menu

## Page-by-page wireframe spec

### A. Landing page
#### Sections
1. Hero
   - headline
   - subheadline
   - primary CTA
   - secondary CTA
   - product screenshot mock panel
2. Problem section
3. How it works section
4. Features grid
5. Trust / compliance section
6. Pricing teaser
7. Footer CTA

#### Notes
- Hero visual should resemble a premium command center
- Include mock cards for premarket brief, checklist completion, and weekly review summary

### B. Pricing page
#### Sections
- plan comparison cards
- feature matrix
- FAQ
- legal boundary copy
- CTA footer

### C. Dashboard
#### Layout
- top summary row: plan badge, today status, watchlist count, last report timestamp
- main content split 2/3 + 1/3

#### Left column
- today’s premarket brief status card
- latest post-close debrief card
- latest weekly review card

#### Right column
- watchlist panel
- checklist completion panel
- upgrade card for free users

#### Empty state
- onboarding nudge + CTA to create first watchlist and first brief

### D. Premarket Brief page
#### Layout
- header with date, generate button, inputs drawer button
- inputs drawer containing watchlist, notes, events, priorities
- output cards beneath

#### Output cards
- market summary
- watchlist priorities
- what changed since yesterday
- focus reminders
- session checklist

#### Actions
- regenerate
- save note
- export as PDF later

### E. Checklists page
#### Layout
- list of checklist templates on left
- template editor or checklist run panel on right

#### Template editor
- title
- description
- checklist items
- required or optional toggles
- reorder support

#### Checklist run panel
- choose template
- complete items
- required reason-for-entry note
- confidence slider/select
- save run

### F. Post-Close Debrief page
#### Layout
- inputs panel at top
- trade import area
- notes area
- generate button
- output report cards below

#### Report cards
- session summary
- what went well
- deviations from plan
- risk behavior notes
- next-day improvements

### G. Weekly Review page
#### Layout
- date range selector
- generate button
- trend cards
- main report sections

#### Report sections
- top strengths
- repeated mistakes
- setup notes
- discipline observations
- next-week action items

### H. History page
#### Features
- filter by type: premarket, debrief, weekly
- filter by date
- search
- click to open saved report

### I. Settings pages
#### Profile
- name
- trading style
- pain points
- optional platform

#### Watchlist
- symbols CRUD
- grouping later

#### Checklist settings
- default templates
- create/edit/delete templates

#### Billing
- plan info
- manage subscription
- usage/limits

---

# 9.2 Database schema

## Entity relationship overview
Core entities:
- users
- profiles
- watchlists
- watchlist_symbols
- checklist_templates
- checklist_template_items
- checklist_runs
- checklist_run_items
- trade_entries
- report_jobs
- reports
- subscriptions
- audit_logs

## SQL schema draft (Postgres)
```sql
create extension if not exists "pgcrypto";

create table users (
    id uuid primary key default gen_random_uuid(),
    auth_provider_id text unique not null,
    email text unique not null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table profiles (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null unique references users(id) on delete cascade,
    display_name text,
    trading_style text not null check (trading_style in ('day','swing','options','mixed')),
    pain_points text[] not null default '{}',
    broker_platform text,
    onboarding_completed boolean not null default false,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table watchlists (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references users(id) on delete cascade,
    name text not null default 'Default Watchlist',
    is_default boolean not null default true,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table watchlist_symbols (
    id uuid primary key default gen_random_uuid(),
    watchlist_id uuid not null references watchlists(id) on delete cascade,
    symbol text not null,
    notes text,
    display_order integer not null default 0,
    created_at timestamptz not null default now(),
    unique (watchlist_id, symbol)
);

create table checklist_templates (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references users(id) on delete cascade,
    name text not null,
    description text,
    is_default boolean not null default false,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table checklist_template_items (
    id uuid primary key default gen_random_uuid(),
    template_id uuid not null references checklist_templates(id) on delete cascade,
    label text not null,
    description text,
    is_required boolean not null default true,
    display_order integer not null default 0,
    created_at timestamptz not null default now()
);

create table checklist_runs (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references users(id) on delete cascade,
    template_id uuid references checklist_templates(id) on delete set null,
    session_date date not null,
    symbol text,
    setup_tag text,
    reason_for_entry text not null,
    confidence_score integer check (confidence_score between 1 and 5),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table checklist_run_items (
    id uuid primary key default gen_random_uuid(),
    checklist_run_id uuid not null references checklist_runs(id) on delete cascade,
    template_item_id uuid references checklist_template_items(id) on delete set null,
    label_snapshot text not null,
    completed boolean not null default false,
    created_at timestamptz not null default now()
);

create table trade_entries (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references users(id) on delete cascade,
    trade_date date not null,
    symbol text not null,
    asset_type text not null check (asset_type in ('stock','option','other')),
    side text not null check (side in ('long','short','call','put','other')),
    quantity numeric(18,4),
    entry_price numeric(18,6),
    exit_price numeric(18,6),
    pnl numeric(18,2),
    fees numeric(18,2),
    tags text[] not null default '{}',
    notes text,
    source_type text not null default 'manual' check (source_type in ('manual','csv_upload')),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table report_jobs (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references users(id) on delete cascade,
    report_type text not null check (report_type in ('premarket','debrief','weekly_review')),
    status text not null check (status in ('queued','running','succeeded','failed')),
    input_payload jsonb not null,
    error_message text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table reports (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references users(id) on delete cascade,
    report_job_id uuid references report_jobs(id) on delete set null,
    report_type text not null check (report_type in ('premarket','debrief','weekly_review')),
    title text not null,
    report_date date not null,
    input_summary jsonb not null,
    raw_model_output text,
    parsed_output jsonb not null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table subscriptions (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null unique references users(id) on delete cascade,
    stripe_customer_id text unique,
    stripe_subscription_id text unique,
    plan text not null check (plan in ('free','pro','elite')) default 'free',
    status text not null default 'active',
    current_period_end timestamptz,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table audit_logs (
    id uuid primary key default gen_random_uuid(),
    user_id uuid references users(id) on delete set null,
    entity_type text not null,
    entity_id uuid,
    action text not null,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create index idx_watchlists_user_id on watchlists(user_id);
create index idx_checklist_templates_user_id on checklist_templates(user_id);
create index idx_checklist_runs_user_id_date on checklist_runs(user_id, session_date desc);
create index idx_trade_entries_user_id_date on trade_entries(user_id, trade_date desc);
create index idx_report_jobs_user_id_type on report_jobs(user_id, report_type, created_at desc);
create index idx_reports_user_id_type_date on reports(user_id, report_type, report_date desc);
create index idx_audit_logs_user_id_date on audit_logs(user_id, created_at desc);
```

## Notes for Codex
- add updated_at triggers or application-layer updates
- use migrations from day one
- create seed templates for onboarding
- keep report JSON schemas versioned

---

# 9.3 API contract draft

## Authenticated routes
### Profile
- `GET /api/v1/profile`
- `PUT /api/v1/profile`

### Watchlist
- `GET /api/v1/watchlists`
- `POST /api/v1/watchlists`
- `PUT /api/v1/watchlists/:id`
- `DELETE /api/v1/watchlists/:id`
- `POST /api/v1/watchlists/:id/symbols`
- `DELETE /api/v1/watchlists/:id/symbols/:symbolId`

### Checklist templates
- `GET /api/v1/checklist-templates`
- `POST /api/v1/checklist-templates`
- `PUT /api/v1/checklist-templates/:id`
- `DELETE /api/v1/checklist-templates/:id`

### Checklist runs
- `GET /api/v1/checklist-runs`
- `POST /api/v1/checklist-runs`
- `GET /api/v1/checklist-runs/:id`

### Trade entries
- `GET /api/v1/trades`
- `POST /api/v1/trades`
- `POST /api/v1/trades/upload-csv`
- `PUT /api/v1/trades/:id`
- `DELETE /api/v1/trades/:id`

### Reports
- `POST /api/v1/reports/premarket/generate`
- `POST /api/v1/reports/debrief/generate`
- `POST /api/v1/reports/weekly-review/generate`
- `GET /api/v1/reports`
- `GET /api/v1/reports/:id`

### Billing
- `GET /api/v1/billing/subscription`
- `POST /api/v1/billing/create-checkout-session`
- `POST /api/v1/billing/create-portal-session`
- `POST /api/v1/billing/webhooks/stripe`

### Health
- `GET /api/v1/health`

---

# 9.4 Prompt specifications and output contracts

## Prompt design principles
- all outputs must be structured JSON
- prompts must explicitly prohibit buy/sell instructions
- prompts should summarize and prioritize, not recommend securities
- every prompt should include user profile and report purpose
- prompts should return concise sections suitable for direct UI rendering

## A. Premarket Brief prompt spec
### Purpose
Generate a daily planning brief from the user’s watchlist, notes, and manual context inputs.

### Inputs
- report_date
- user_profile
- watchlist_symbols
- prior_notes
- manual_events
- user_priorities

### Required output schema
```json
{
  "summary": "string",
  "watchlist_priorities": [
    {
      "symbol": "string",
      "priority": "high|medium|low",
      "reason": "string"
    }
  ],
  "changes_to_watch": ["string"],
  "focus_reminders": ["string"],
  "session_checklist": ["string"],
  "disclaimer": "string"
}
```

### System prompt draft
```text
You are generating a premarket workflow brief for a self-directed trader.
You are not providing investment advice, trade signals, or buy/sell recommendations.
Your job is to organize the user’s focus, summarize what deserves attention, and provide process-oriented reminders.
Do not tell the user to buy, sell, enter, or exit any security.
Return only valid JSON matching the required schema.
```

## B. Post-Close Debrief prompt spec
### Purpose
Generate a structured end-of-day review from trades, checklist runs, and user notes.

### Inputs
- report_date
- user_profile
- trade_entries
- checklist_runs
- user_notes

### Required output schema
```json
{
  "session_summary": "string",
  "what_went_well": ["string"],
  "deviations_from_plan": ["string"],
  "risk_behavior_notes": ["string"],
  "next_day_improvements": ["string"],
  "disclaimer": "string"
}
```

### System prompt draft
```text
You are generating a post-close workflow review for a self-directed trader.
You are not evaluating whether they should buy or sell a security next.
Focus on discipline, execution quality, checklist adherence, and behavioral patterns.
Do not provide direct trade recommendations.
Return only valid JSON matching the required schema.
```

## C. Weekly Review prompt spec
### Purpose
Generate a weekly performance and discipline review.

### Inputs
- week_start
- week_end
- user_profile
- debrief_summaries
- trade_entries
- checklist_run_summaries

### Required output schema
```json
{
  "top_strengths": ["string"],
  "repeated_mistakes": ["string"],
  "setup_observations": ["string"],
  "discipline_observations": ["string"],
  "next_week_action_items": ["string"],
  "disclaimer": "string"
}
```

### System prompt draft
```text
You are generating a weekly review for a self-directed trader.
The goal is to identify recurring patterns, strengths, mistakes, and process improvements.
Do not provide trade ideas, security recommendations, target prices, or market calls.
Frame all output as workflow support and self-review.
Return only valid JSON matching the required schema.
```

## Validation requirements
- use pydantic or zod schema validation
- reject malformed JSON and retry once with repair instructions
- store both raw and parsed outputs
- surface user-friendly error state when retries fail

---

# 9.5 Technical architecture

## High-level architecture
```text
[ Next.js Web App ]
        |
        | HTTPS / JSON API
        v
[ FastAPI Backend ] ----> [ Postgres ]
        |
        +----> [ Redis / Job Queue ] ----> [ AI Report Worker ] ----> [ LLM Provider ]
        |
        +----> [ Stripe ]
        |
        +----> [ Auth Provider ]
```

## Responsibilities
### Frontend
- auth/session handling
- page rendering
- forms and client validation
- report views
- billing screens
- usage gating banners

### Backend API
- auth verification
- CRUD for user data
- CSV parsing and validation
- report job creation
- subscription enforcement
- audit logging

### Worker
- receive report jobs
- assemble prompt inputs
- call model provider
- validate output
- persist results
- mark job status

## Suggested package structure
```text
/apps
  /web
  /api
/packages
  /ui
  /types
  /config
  /schemas
  /utils
/infra
  docker-compose.yml
  render.yaml or fly.toml
```

## Environment variables
### Web
- NEXT_PUBLIC_APP_URL
- NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY or auth equivalent
- API_BASE_URL

### API
- DATABASE_URL
- REDIS_URL
- LLM_API_KEY
- LLM_MODEL_NAME
- STRIPE_SECRET_KEY
- STRIPE_WEBHOOK_SECRET
- AUTH_PROVIDER_SECRET
- APP_ENV
- CORS_ORIGINS

## Deployment recommendation
### MVP easiest path
- Vercel for web
- Render/Fly/Railway for API and worker
- Neon/Supabase/RDS for Postgres
- Upstash/Redis Cloud for Redis

---

# 9.6 Repo scaffold request for Codex

Use the following prompt with Codex to scaffold the repo:

```text
Create a production-minded MVP monorepo for a SaaS web app called TradeReviewDesk.

TradeReviewDesk is an AI-powered workflow platform for self-directed traders. It is NOT a trade signal engine, NOT a brokerage, NOT a copy-trading app, and NOT an auto-execution system. It helps users build discipline through premarket briefs, checklist-based trade prep, post-close debriefs, and weekly reviews.

Requirements:
- monorepo structure with /apps/web and /apps/api and /packages/ui, /packages/types, /packages/schemas, /packages/config
- web app: Next.js + TypeScript + Tailwind + shadcn/ui
- backend: FastAPI + SQLAlchemy or SQLModel + Alembic
- database: Postgres
- background jobs: Redis + a worker framework
- billing: Stripe stubs wired with env vars and placeholder endpoints
- auth: Clerk or Supabase auth integration scaffold
- dark-mode dashboard UI with blue/green accents and polished cards
- pages: landing, pricing, login, signup, dashboard, premarket, checklists, debrief, weekly review, history, settings
- report generation endpoints and job model scaffolded, with placeholder AI provider abstraction
- schema validation for all AI outputs
- CSV upload parsing scaffold for trade imports
- example seed data and checklist templates
- README with setup instructions
- example .env files
- Docker compose for local Postgres + Redis
- no fake claims about profits or trade recommendations in UI copy
- include compliance/disclaimer placeholders in the UI

Implement the core database schema, API routes, frontend pages, and a clean component system. Use strong typing and clear separation of concerns.

Do not build live broker execution or direct buy/sell recommendation features.
```

---

# 9.7 Build milestones and acceptance criteria

## Milestone 1: foundation
### Includes
- monorepo setup
- auth scaffold
- db migrations
- landing page
- pricing page
- onboarding flow

### Acceptance criteria
- app runs locally with one command set
- user can sign up and complete onboarding
- data persists to Postgres

## Milestone 2: dashboard + checklists
### Includes
- dashboard shell
- checklist template CRUD
- checklist run creation

### Acceptance criteria
- user can create and save a checklist template
- user can run a checklist and save it
- dashboard displays recent checklist state

## Milestone 3: premarket brief
### Includes
- report job creation
- worker processing
- placeholder AI provider integration
- premarket brief UI

### Acceptance criteria
- user can generate a premarket brief
- report is validated and saved
- report appears in history

## Milestone 4: debrief + trade import
### Includes
- manual trade entry
- CSV upload parsing
- post-close report generation

### Acceptance criteria
- user can upload trade CSV or enter trades manually
- user can generate and save a debrief

## Milestone 5: weekly review + billing
### Includes
- weekly report generation
- Stripe plan gating
- usage limits by plan

### Acceptance criteria
- free user limits are enforced
- paid tiers unlock premium actions
- weekly review is generated from last 7 days of data

## Milestone 6: polish + deploy
### Includes
- error states
- loading states
- analytics hooks
- legal pages
- deployment configs

### Acceptance criteria
- app can be deployed to staging
- core flows are usable end-to-end
- README is sufficient for another developer to run locally

---

# 9.8 Beta launch checklist

## Product
- finalize name and domain
- prepare logo and simple visual identity
- seed onboarding checklist templates
- write disclaimer copy

## Growth
- launch landing page with waitlist
- create 3 demo screenshots
- create 2 short demo videos
- write 10 launch posts for X / Reddit / Discord use

## Operations
- support email
- analytics
- crash/error monitoring
- privacy policy and terms
- Stripe products configured

## Beta success metrics
- 100 waitlist signups
- 20 beta users onboarded
- 10 active weekly users
- 5 paying conversions
- user-reported value: saves time, increases discipline, reduces impulsive entries

---

# 9.9 Suggested next artifact set
After this implementation pack, the next useful assets are:
1. full SQL migration files
2. TypeScript and Pydantic schema definitions
3. sample JSON payloads for each report type
4. landing page mockup copy blocks by section
5. a one-shot Codex prompt for each milestone
6. a seed dataset for local development
