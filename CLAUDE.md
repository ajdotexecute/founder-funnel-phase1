# Founder Funnel — generic assessment engine (Phase A)

This started as a Phase 1 discovery prototype and is being rebuilt into a
generic, config-driven assessment engine (Phase A, checkpoints 0-6). Core
code must stay generic — no client names, branding, or framework names
hard-coded; see the Phase A brief's amended hard constraints. Do not treat
anything here as hardened/production-ready without re-reading this file.

## What's real vs. what's stubbed

**Stubbed — do not mistake this for finished extraction logic:**
- `backend/services/stub_extractor.py` returns the same hardcoded sample
  payload for **every** deck, regardless of its actual content. Checkpoint 3
  replaces this with a real two-stage Claude API extract-then-score pipeline.
- The response's `extracted_sector`, `extracted_industry`, `raise_amount`,
  `gap_flags`, and `raising_raw` all come from that stub, not from the
  uploaded documents.
- No AI scoring, no report generation, no Companies House *lookup* (only
  format *validation* exists so far — see below). No cost logging, no
  export, no client theming. All later checkpoints.
- `raising_raw` stores the "(E) raising" marker from the original Phase 1
  notes as a raw string only — meaning still unresolved, no logic built
  against it.

**Real, as of Checkpoint 2:**
- Three typed document slots per submission — `deck` (required), `forecast`,
  `one_pager` (both optional) — accepting PDF, PPTX, XLSX, CSV, or DOCX, up
  to 20MB each. File type is validated by sniffing actual content
  (`backend/services/file_validation.py`), not by trusting the filename
  extension or browser-supplied Content-Type.
- A `StorageBackend` interface (`backend/services/storage.py`) with a local
  filesystem implementation. `STORAGE_BACKEND` env var selects it (only
  `local` works today; `box` raises `NotImplementedError` until Checkpoint 5).
- UK Companies House number format validation (not a live lookup yet).
- A declared-sector dropdown fed by `GET /api/config/sectors`
  (`backend/config/sectors.json`) — the founder's own self-reported
  category. This is **distinct** from `extracted_sector` in the API
  response, which is whatever the (currently stubbed) extraction reads off
  the deck — the two fields can and do disagree; see the field comment on
  `Submission.declared_sector` in `models/db_models.py`.
- Required consent checkbox; `consent_at` is stored per submission.
- Normalised data model: `founders` → `submissions` (versioned per founder)
  → `documents` / `extractions` / `scores`. Repeat submissions from the same
  email link to one founder record. Managed by Alembic — see
  `backend/alembic/`.
- Results live at `/critique/:id` (React Router, fetched by UUID via
  `GET /api/submissions/:id`), refresh-safe, with a friendly not-found
  screen. Roadmap and calculator carry the id and link back to that same
  results page — not to the upload screen.
- No email-based lookup exists on any public endpoint, and none should be
  added — submission history is admin-only once an admin surface exists
  (Checkpoint 4).
- The dilution calculator does real arithmetic (unchanged since Phase 1);
  see `frontend/src/components/DilutionCalculator.tsx`.

## Running locally

```bash
cp .env.example .env
docker compose up --build
```

The backend container runs `alembic upgrade head` before starting uvicorn —
schema comes from migrations only, there's no `create_all` fallback. To seed
synthetic demo data (5 founders, one with two versions):

```bash
docker compose exec backend python -m scripts.seed
```

- Frontend: http://localhost:5173
- Backend: http://localhost:8000 (docs at `/docs`)
- Postgres: localhost:5432 (`founder` / `founder_pass` / `founder_funnel` by default)

### Tests

Backend tests are integration tests against a real, migrated Postgres (the
same `DATABASE_URL` the app uses — point this at a disposable database if
you don't want test data touching your dev one):

```bash
cd backend && pip install -r requirements-dev.txt
pytest
```

## Stack

- Backend: FastAPI + async SQLAlchemy + Postgres + Alembic.
- Frontend: React + TypeScript + Tailwind + Vite. Design tokens (`#0A0A0B`
  background, `#2C5282` steel-blue accent, Inter) are the neutral demo
  theme — Checkpoint 4 adds a real client theme layer on top.

## Out of scope for this phase (per the amended brief)

Client branding, client framework/dimension names, client question sets,
and client terms text in core code (all client-specific material lives
under `clients/<client_id>/`, not introduced yet — first needed in
Checkpoint 3). Box credentials beyond the developer-account test case,
public deployment, and payment/auth beyond a basic admin guard.
