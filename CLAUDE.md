# Founder Funnel — generic assessment engine (Phase A)

This started as a Phase 1 discovery prototype and is being rebuilt into a
generic, config-driven assessment engine (Phase A, checkpoints 0-6). Core
code must stay generic — no client names, branding, or framework names
hard-coded; see the Phase A brief's amended hard constraints. Do not treat
anything here as hardened/production-ready without re-reading this file.

## What's real vs. what's stubbed

**Real, as of Checkpoint 3:**
- Extraction and scoring are real two-stage Claude API calls (model from
  `AI_MODEL` env, default `claude-sonnet-5-5`) — `backend/services/claude_client.py`
  (structured output via forced tool-use) orchestrated by
  `backend/services/pipeline.py`. PDFs are sent natively as a document content
  block; PPTX/DOCX/XLSX/CSV are converted to text server-side first
  (`backend/services/document_text.py`) — see `backend/services/file_validation.py`
  for how each document's real kind is determined (by content, not extension).
- Scoring runs against a client's YAML framework, loaded at runtime from
  `clients/<CLIENT_ID>/scoring/*.yaml` (`backend/services/client_config.py`,
  schema in `backend/services/scoring_schema.py`). `CLIENT_ID` env var selects
  the client; unset defaults to `demo`, the neutral three-dimension framework.
  `clients/fg/scoring/4t.yaml` is a **scaffold only** — four placeholder
  dimensions, real content pending the real criteria (see that file's header
  comment; do not treat its wording as real).
- Every dimension score carries a short evidence quote/field reference from
  the extraction and 2-3 feedback points — see `Score.dimension_scores`.
- A rendered report (`clients/<id>/report/template.html`, Jinja2) is served as
  HTML at `GET /report/:id` and as a downloadable PDF at `GET /report/:id/pdf`
  (Playwright print-to-PDF — see "Why Playwright, not WeasyPrint" below).
  `clients/fg/report/template.html` doesn't exist yet — same reason as 4t.yaml.
- Every AI call's raw response, token counts, and latency are logged to
  `model_calls` (admin-only in principle — no endpoint exposes this table yet,
  that's Checkpoint 4's cost-logging/admin-page work on top of what's already
  captured here).
- UK Companies House *lookup* (status, incorporation date, SIC codes) when a
  number is given and `COMPANIES_HOUSE_API_KEY` is set — merged into the
  extraction under `companies_house`. Unset key = skipped gracefully, not an
  error. See `backend/services/companies_house.py`.
- Robustness: timeouts + retries with backoff on both the Claude calls and the
  Companies House lookup; a failed/missing document, a failed extraction, or a
  failed scoring call never 500s the submission request — see
  `SubmissionResponse.processing_error` and `services/pipeline.py`'s module
  docstring. A corrupt individual document (passes content-sniffing but fails
  to parse) is dropped with a warning, not fatal.
- Three typed document slots per submission — `deck` (required), `forecast`,
  `one_pager` (both optional) — PDF, PPTX, XLSX, CSV, or DOCX, up to 20MB each.
- A `StorageBackend` interface (`backend/services/storage.py`) with a local
  filesystem implementation. `STORAGE_BACKEND` env var selects it (only
  `local` works today; `box` raises `NotImplementedError` until Checkpoint 5).
- A declared-sector dropdown fed by `GET /api/config/sectors`
  (`backend/config/sectors.json`) — the founder's own self-reported category.
  This is **distinct** from `extraction.extracted_sector` in the API response,
  which is whatever the AI extraction reads off the deck — the two can and do
  disagree; see the field comment on `Submission.declared_sector`.
- Required consent checkbox; `consent_at` stored per submission.
- Normalised data model: `founders` → `submissions` (versioned per founder) →
  `documents` / `extractions` / `scores` / `model_calls`. Repeat submissions
  from the same email link to one founder record. Managed by Alembic.
- Results live at `/critique/:id`, refresh-safe, with a friendly not-found
  screen; roadmap/calculator carry the id and link back to that same page.
  No email-based lookup on any public endpoint (admin-only, Checkpoint 4).
- The dilution calculator does real arithmetic (unchanged since Phase 1).

**Stubbed / not built:**
- No cost-per-call calculation or admin page (Checkpoint 4 — the token counts
  and raw responses it needs are already captured in `model_calls`).
- No export, no external scoring API, no client theme layer (`GET /api/theme`
  doesn't exist yet — the frontend's dark-palette tokens are hardcoded, not
  read from `theme.json`). All Checkpoint 4.
- No Box backend (Checkpoint 5). No synthetic data pack / demo_runs (Checkpoint 6).
- `clients/fg/scoring/4t.yaml` and `clients/fg/report/template.html`: FG's
  real criteria and report layout, pending.

### Why Playwright, not WeasyPrint, for the PDF

Playwright prints through a real Chromium rather than a CSS-subset renderer,
so the report template can use real flexbox/grid/custom fonts without
surprises, and setup is one documented command
(`playwright install --with-deps chromium`) rather than chasing a
version-sensitive apt package list (Pango/cairo/GDK-pixbuf/etc.) for
WeasyPrint on a slim Debian image. Tradeoff: a materially larger Docker image.

## Running locally

```bash
cp .env.example .env
docker compose up --build
```

Set `ANTHROPIC_API_KEY` in `.env` for real extraction/scoring — without it,
submissions still work but `processing_error` explains why extraction/scoring
didn't run. `CLIENT_ID` (default `demo`) and `COMPANIES_HOUSE_API_KEY`
(optional) are also read from `.env` — see `.env.example` for the full list.

The backend container runs `alembic upgrade head` before starting uvicorn,
then `playwright install --with-deps chromium` at image build time for report
PDFs — schema comes from migrations only, there's no `create_all` fallback.
To seed synthetic demo data (5 founders, one with two versions, real-shaped
extraction/score data authored by hand — no API key needed):

```bash
docker compose exec backend python -m scripts.seed
```

- Frontend: http://localhost:5173
- Backend: http://localhost:8000 (docs at `/docs`)
- Postgres: localhost:5432 (`founder` / `founder_pass` / `founder_funnel` by default)

### Tests

Every test mocks `services.claude_client` (and, where relevant,
`services.companies_house`) directly — the suite never calls a real external
API, so it runs with no `ANTHROPIC_API_KEY`/`COMPANIES_HOUSE_API_KEY` set.
One PDF-generation test skips gracefully if no Chromium build matches the
pinned Playwright version (expected outside Docker; the Dockerfile's
`playwright install` guarantees a match in the real container).

Integration tests run against a real, migrated Postgres (the same
`DATABASE_URL` the app uses — point this at a disposable database if you
don't want test data touching your dev one):

```bash
cd backend && pip install -r requirements-dev.txt
pytest
```

## Stack

- Backend: FastAPI + async SQLAlchemy + Postgres + Alembic + Anthropic SDK +
  Playwright (report PDFs) + python-pptx/python-docx/openpyxl (document text).
- Frontend: React + TypeScript + Tailwind + Vite. Design tokens (`#0A0A0B`
  background, `#2C5282` steel-blue accent, Inter) are the neutral demo
  theme — Checkpoint 4 adds a real client theme layer on top.

## Out of scope for this phase (per the amended brief)

Client branding, client framework/dimension names, client question sets, and
client terms text in core code — all client-specific material lives under
`clients/<client_id>/`. Box credentials beyond the developer-account test
case, public deployment, and payment/auth beyond a basic admin guard.
