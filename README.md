# HSA Simulator

A local Health Savings Account simulator for the Human Interest SWE take-home
assignment. Create users and accounts, deposit simulated USD funds, issue virtual
debit cards, and simulate qualified or declined purchases through a web UI.

Built with React, TypeScript, Vite, Tailwind CSS, FastAPI, SQLAlchemy, Alembic,
and PostgreSQL. Docker Compose runs the frontend, API, and database locally.

## Run with Docker

Prerequisite: Docker with Docker Compose installed and running. Run these commands
from the repository root. Copy `.env.example` only on first setup; preserve any
existing `.env` configuration.

```sh
cp .env.example .env
docker compose up -d --wait db
docker compose build
docker compose run --rm backend alembic upgrade head
docker compose up --build
```

**The migration command is required.** Startup does not apply migrations or create
tables automatically. It is safe to run `alembic upgrade head` again to apply any
pending revisions; reviewers do not need to generate migrations.

| Service | URL |
| --- | --- |
| Frontend | http://localhost:5173 |
| Interactive API documentation | http://localhost:8000/docs |
| API process health | http://localhost:8000/health |

Compose waits for dependency health checks. `/health` checks the API process only;
it does not verify database connectivity or that migrations have been applied.

Stop with `docker compose down`. Database data persists in a named Docker volume.
Rebuild with `docker compose up --build` after code or dependency changes. The
example credentials are for local development. Ports 5432, 8000, and 5173 must be
available; services are exposed on the local machine only.

## Reviewer walkthrough

The database starts without seeded users or accounts.

1. Open the frontend and expand **Create your first user**. Enter a name and email.
2. Under **Create a new account**, click **Create new account**. The new account is
   selected automatically and starts with a $0 balance. The existing-account
   dropdown is for reopening accounts; creating one requires only a selected user.
3. Click **Deposit funds**, enter `100.00`, and submit. A successful response shows
   the saved amount and transaction ID.
4. Return to the dashboard and click **Refresh data** to load the new balance and
   recent transactions. Deposits currently do not refresh the dashboard automatically.
5. Click **Issue card**. In the purchase form, select the card, enter `80.00`, choose
   **Pharmacy**, and submit. The purchase is approved and the balance becomes $20.
6. Submit a `1.00` **Restaurant** purchase. It is declined as an invalid expense,
   with no balance change. **Electronics** is also invalid; **Hospital** is qualified.
7. Submit a `50.00` **Hospital** purchase. It is declined for insufficient funds.
8. Optionally deactivate the card and try another purchase to see an inactive-card
   decline. Purchase outcomes and their reasons appear in recent transactions.

Selection stays in memory, so a browser refresh requires selecting the user and
account again. Saved accounts, cards, balances, and transactions remain in Postgres.
The dashboard shows five recent transactions; the API exposes paginated full history.

## Local development

Prerequisites: Python 3.12+, Node.js 22.12+ (or 20.19+), and Docker Compose for
Postgres. From the repository root:

```sh
cp .env.example .env
docker compose up -d --wait db
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e './backend[dev]'
cd backend
alembic upgrade head
uvicorn src.main:app --reload
```

In a second terminal, starting from the repository root:

```sh
cd frontend
npm ci
npm run dev
```

The backend reads the root `.env`; environment variables take precedence. Local
Python connects to `localhost`, while Compose sets the database hostname to `db`.
If database credentials change, update `DATABASE_URL` for local Python too.
Postgres initialization variables apply only when the data volume is first created.

The frontend defaults to `http://localhost:8000`. To change it, set
`VITE_API_BASE_URL` in `frontend/.env.local` and restart Vite. If the frontend origin
changes, update the backend's `CORS_ORIGINS` JSON list as well.

## Verification

With Postgres running and backend development dependencies installed, run from the
repository root:

```sh
.venv/bin/python -m pytest -c backend/pyproject.toml
```

Or use the backend container after building the images:

```sh
docker compose run --rm backend python -m pytest -c pyproject.toml
```

Tests create and migrate a uniquely named disposable database and remove it after
completion. The database role must have permission to create databases. Tests use
`DATABASE_URL` by default; set `TEST_DATABASE_ADMIN_URL` in the test process to use
another Postgres server or role. For a Compose test run, pass an override with
`docker compose run --rm -e TEST_DATABASE_ADMIN_URL backend ...` after exporting it.
The test database must be reachable from the environment running the tests.
Application data is not cleared or modified.

Coverage includes request validation, account ownership checks, qualification,
card lifecycle, deposits, purchase approvals/declines, history, rollback, and
idempotency. Concurrent tests use independent request connections and verify that
competing purchases cannot overspend and that the balance matches the ledger.

Frontend type check and production build:

```sh
cd frontend
npm run build
```

There is currently no committed frontend automated interaction test suite. Use the
reviewer walkthrough for browser verification. A successful test run does not
replace checking setup against a fresh application database: test fixtures apply
migrations independently of application startup.

## Data and transaction behavior

- **Users** hold a name and unique normalized email; **accounts** belong to users
  and start with zero balance.
- **Cards** belong to an account and store only simulated details, including last
  four digits, holder name, expiration, and status. An account has at most one
  active card, enforced by a partial unique index. Deactivation has no reactivation
  operation; expired active cards are deactivated during issuance or purchase processing.
- **Transactions** form an application-level append-only ledger. Approved deposits
  increase the balance; approved purchases decrease it; declined purchases record
  a zero balance change. The API offers no ledger editing or deletion operations.
- Money is stored as integer USD cents. UI dollar input is parsed into cents without
  floating-point arithmetic. Each deposit or purchase must be positive and no more
  than $1 trillion. The frontend cannot display accumulated balances above
  JavaScript's safe integer range exactly and shows a precision warning instead.
- Purchases lock the account before checking the card and qualified category and
  conditionally debiting sufficient funds. Balance changes and ledger insertion
  commit atomically. Database constraints also prohibit negative balances.
- Both financial endpoints require an `Idempotency-Key` header. Identical replays
  return the original transaction; reusing a key for a different operation payload
  on the same account returns a conflict. Purchase retries retain the original key.
  Deposit submissions include a new key but have no retry workflow; an unknown
  deposit outcome is reported without automatically resubmitting.

## Scope and assumptions

This is a simulator with selected users, not authentication. User/account checks
validate the supplied IDs but do not prevent a caller from selecting another
user. The user and account listing endpoints expose simulator data for local use.

Qualification is determined by a server-side category allowlist, not individual
items or medical records. Deposits are immediately available simulated funds, and
cards do not connect to a payment network. Contribution limits, tax reporting,
refunds, investments, fees, interest, and external banking integrations are outside
scope. Full history UI, deposit history, and automatic refresh after deposits are
not implemented.

## Repository layout

- `backend/src/routes/`: HTTP endpoints and error mapping.
- `backend/src/schemas/`: request validation and response definitions.
- `backend/src/services/`: account, card, deposit, and purchase business logic.
- `backend/src/database/`: models, sessions, and ledger repository functions.
- `backend/migrations/`: versioned Alembic schema migrations.
- `frontend/src/pages/`: account dashboard and deposit page.
- `frontend/src/components/`: selection, card controls, purchases, and recent transactions.
- `frontend/src/services/`, `types/`, `utils/`: Fetch calls, API types, and money utilities.
- `tests/`: backend integration and concurrent-request tests.
- `docs/project-context.md`: original project assumptions and collaboration conventions.

## Submission materials

The following required materials are still pending in this checkout:

- `architecture.md`: architecture, request flow, data model, concurrency handling,
  and design tradeoffs.
- `ai-usage.md`: tools used, assistance provided, representative prompts/workflows,
  one corrected AI output, and final verification.
- Demo video link: up to five minutes covering the application, architecture,
  data model, transaction processing, improvements, and AI usage/validation.
