# HSA Simulator

A take-home project using FastAPI, React with TypeScript, PostgreSQL, SQLAlchemy,
Alembic, Vite, and Tailwind CSS. This initial skeleton contains a placeholder UI
and a process health endpoint. No financial features or database tables exist yet.

## Run with Docker

Install Docker with Docker Compose, then run from the repository root:

```sh
cp .env.example .env
docker compose up --build
```

Open the frontend at http://localhost:5173, API docs at http://localhost:8000/docs,
and process health at http://localhost:8000/health. Compose waits for Postgres
and the backend to become healthy before starting dependent services. The health
endpoint checks the API process; it does not query the database.

Stop with `docker compose down`. Database data persists in a named Docker volume.
The example database credentials are intended for local development.
If ports 5432, 8000, or 5173 are occupied, stop the conflicting service first.
Rebuild with `docker compose up --build` after code or dependency changes.

## Local development

Use Python 3.12+ and Node.js 22.12+ (or 20.19+). Start only Postgres in Docker:

```sh
cp .env.example .env
docker compose up -d db
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e './backend[dev]'
cd backend
uvicorn src.main:app --reload
```

In a second terminal:

```sh
cd frontend
npm ci
npm run dev
```

The backend reads the root `.env`; environment variables take precedence. Compose
sets the database hostname to `db`, while local Python uses `localhost`.
When changing database credentials, update the local `DATABASE_URL` as well.
Postgres initialization variables only apply when the data volume is first created.
The frontend has no API calls yet; add Fetch-based calls in `frontend/src/services/`
when implementing features. CORS permits the local frontend origin.

## Checks

```sh
# From the root, after installing backend dependencies:
.venv/bin/python -m pytest -c backend/pyproject.toml

# Frontend type check and production build:
cd frontend
npm run build
```

Alternatively, run backend tests using Docker:

```sh
docker compose run --rm backend python -m pytest -c pyproject.toml
```

## Migrations

Alembic is configured, but there are no application models or revisions yet.
After defining models, import them in `backend/src/database/models/__init__.py`
so Alembic can discover their metadata. From `backend/`, with the virtual
environment activated and Postgres running:

```sh
alembic revision --autogenerate -m "describe schema change"
# Review the generated migration before applying it.
alembic upgrade head
```

Tables are not created automatically at API startup.

## Layout and conventions

- `backend/src/routes/`: future HTTP endpoints.
- `backend/src/services/`: future business functions.
- `backend/src/schemas/`: future Pydantic request and response definitions.
- `backend/src/database/`: SQLAlchemy base, sessions, and future models.
- `backend/migrations/`: Alembic configuration and future revisions.
- `frontend/src/pages/`, `services/`, `types/`: future React pages, Fetch calls, and types.
- `tests/`: backend tests; currently only a health smoke test.
- `docs/project-context.md`: original requirements and collaboration conventions.

All future money values use integer USD cents. Authentication, user selection,
accounts, deposits, cards, purchases, ledger constraints, and concurrency handling
are deferred. Python dependency ranges live in `backend/pyproject.toml`; frontend
resolved versions are committed in `frontend/package-lock.json`.
