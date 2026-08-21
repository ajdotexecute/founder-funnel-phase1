# Founder Funnel — Phase 1 (discovery prototype)

This is a **discovery prototype**, not production software. Its only job is to
let someone click through the upload → critique → (roadmap | dilution
calculator) flow and judge whether it holds up. Do not treat anything here as
a foundation to harden without re-reading this file first.

## What's real vs. what's stubbed

**Stubbed — do not mistake this for finished extraction logic:**
- `backend/services/stub_extractor.py` returns the same hardcoded sample
  company/sector/industry/raise-amount/gap-flags payload for **every**
  upload, regardless of what PDF was sent.
- `POST /api/submissions` (in `backend/main.py`) saves the uploaded file to
  disk but **never opens or parses it**. Any file extension would technically
  work; the endpoint doesn't validate PDF structure.
- There is no "AI scan" / market-comparison logic anywhere — it's explicitly
  out of scope for Phase 1 (flagged build-later in the spec).
- The quiz (Screen 5, "Raising roadmap") is not built — the spec itself
  never drafted its questions.
- The founder roadmap page is static placeholder content, not personalised.
- `raising_raw` stores the "(E) raising" marker from the deck notes as a raw
  string only. Its meaning is unresolved in the spec; no logic is built
  against it.
- "Replies" (mentioned once in the source notes, unconnected to any flow) is
  not implemented anywhere, deliberately.
- No auth. No Companies House / identity check. No RAG scoring. Those belong
  to Phase 1→2 and Phase 2 per the spec, not here.

**Real:**
- The upload endpoint persists a `Submission` row to Postgres (email,
  optional company name, the stub-extracted fields) and returns it.
- The dilution calculator (`frontend/src/components/DilutionCalculator.tsx`)
  does real arithmetic: dilution % = raise / (pre-money valuation + raise),
  founder ownership % = 100% − dilution%, and stage band is derived from the
  raise amount (Seed <£1m, Series A £1–20m, Series B £20–50m, Series C
  £50m+). The three-attempts-then-"talk to us" gate is client-side UI state
  only — it resets on page reload, by design (no real gating logic was
  asked for).

## Running locally

```bash
cp .env.example .env
docker compose up --build
```

- Frontend: http://localhost:5173
- Backend: http://localhost:8000 (docs at `/docs`)
- Postgres: localhost:5432 (`founder` / `founder_pass` / `founder_funnel` by default)

The backend creates its own tables on startup (`Base.metadata.create_all`) —
there's no separate migration step for this prototype.

## Stack

- Backend: FastAPI + async SQLAlchemy + Postgres (patterns borrowed from the
  `sentient-dfip` / Prism repo's backend structure: `core/config.py`,
  `core/database.py`, typed `Mapped[...]` models).
- Frontend: React + TypeScript + Tailwind, plain Vite (no Prism frontend
  reuse — Prism's frontend is Streamlit, not React; the design tokens here
  — `#0A0A0B` background, `#2C5282` steel-blue accent, Inter — come from the
  brief directly, not from Prism's actual styling).

## Explicitly out of scope for this phase

File parsing/extraction, the AI market-scan ambition, quiz content, anything
about "Replies," and logic built against "(E) raising." If a future session
is asked to "finish" extraction, start by replacing
`backend/services/stub_extractor.py` — that's the seam.
