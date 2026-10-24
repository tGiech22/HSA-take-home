# AI usage

I used ChatGPT, Claude, and Perplexity for initial research and design discussions,
and Codex for implementation, explanations, tests, review, and documentation.
AI contributed substantially to the code and test suite. I directed the work
through incremental prompts, asked for explanations before implementation, and
made the scope and design decisions described below.

This account summarizes my research notes and development chat logs. The initial
research log mostly records prompts and occasional notes, rather than complete
responses. The Codex log records prompts, outputs, and my follow-up decisions.
Technical descriptions here follow the implemented design in
[architecture.md](architecture.md).

## Tools and areas of assistance

| Tool | How I used it |
| --- | --- |
| ChatGPT and Claude | Assignment planning, HSA concepts, monetary modeling, ledger design, idempotency, concurrency, system invariants, and comparisons of implementation options. |
| Perplexity | Research into HSAs, qualified expenses, idempotency, invariants, and supporting references. |
| Codex | Project scaffolding; database models and migrations; API routes, services, and ledger helpers; React/TypeScript UI; automated tests; debugging; repository review; and documentation drafts. |

My research notes combined AI discussions with external articles and references.
I used that research to define a deliberately limited simulator: category-based
qualification, simulated deposits and cards, and no contribution-limit enforcement,
tax reporting, or banking integration. The research was background for those
choices, rather than a claim that the application implements complete HSA rules.

## Representative prompts and workflows

### 1. Research, challenge the design, then define the scope

Representative prompts included:

> What are idempotency keys and how do they apply here?

> Is it better to only keep balance in a separate ledger or have it in both ledger and in a column on the account?

I iterated on my own design notes and asked ChatGPT and Claude to identify missing
rules and tradeoffs. Follow-up questions covered request hashes, positive amounts
versus signed balance changes, concurrency control, and ledger immutability.

I chose one transaction table to serve as both history and ledger rather than
separate business-transaction and ledger tables, to keep the assignment manageable.
I also chose a stored account balance for quick reads, with balance changes and
ledger inserts committed atomically. Approved deposits have positive balance
changes, approved purchases have negative changes, and declines have zero impact.

Other deliberate choices included integer cents, readable integer IDs, selected
users instead of authentication, and application-level append-only ledger helpers
instead of a PostgreSQL immutability trigger. These choices have limits: selected
users do not authenticate callers, and the ledger is not protected from arbitrary
SQL updates. Compensating transactions were discussed but deferred, so refunds
are not implemented.

### 2. Ask for a plan, understand it, then implement incrementally

My initial Codex prompt began:

> Set up the project skeleton based on the pasted context. No business logic yet, show me the file tree and your plan first.

I supplied the stack, tables, invariants, assumptions, and collaboration rules.
For later features, I repeatedly requested a plan with no code changes, asked
follow-up questions, and then authorized implementation. I requested models one
at a time before moving to migrations, creation endpoints, ledger helpers,
deposits, cards, and purchases.

For example, I explicitly required the conditional balance update and ledger
insert to share one database transaction. I also clarified that business declines
should be saved as normal outcomes, while malformed requests should return errors
without creating ledger entries. This avoids losing a declined purchase from
history because an exception rolls back its insert.

Codex later implemented the frontend from my page requirements, including user
and account selection, the dashboard, card controls, purchases, and the deposit
page. I explicitly deferred deposit retries, deposit history, and automatic
dashboard refresh after deposits. Full history navigation also remains unfinished;
the API supports history and the dashboard displays recent transactions.

### 3. Use AI to explain and implement verification, then audit the result

One prompt was:

> How would you implement the concurrency and idempotency tests? Give me a plan and explain it to me well, no code changes yet.

I asked how `ThreadPoolExecutor` works and requested a concrete test proposal
before asking Codex to implement it. The resulting tests launch overlapping
requests against PostgreSQL and inspect committed outcomes. Threads create the
test concurrency; database locking and conditional updates provide correctness.

I also asked Codex to review the repository against the original assignment.
That review checked implementation gaps, setup, documentation, and verification,
and identified the fresh-database startup problem below.

## An incomplete AI output and how it was corrected

The earlier AI-assisted setup started the API without applying database migrations,
and the original setup guidance omitted that initialization step. I ran a Codex
audit to test setup and saw that it reported reproducing `/health` returning `200` while `/users` returned `500`
against an empty database.

I brought the issue back to Codex and asked for a proposed fix before approving
the changes. The final Compose configuration adds a migration service and starts
services in this order:

```text
Postgres healthy → alembic upgrade head succeeds → backend healthy → frontend
```

The README and architecture document were updated too. Codex reported verifying
fresh initialization, core API operations, and persistence after restart in an
isolated Compose stack. Local Uvicorn development still requires running migrations
manually.

I also challenged an earlier card proposal that assumed an expired card needed
explicit deactivation. I requested automatic deactivation instead. The implemented
behavior processes expiration during card issuance and purchase operations; it
does not run a scheduled expiration job.

## Verification and ownership

The recorded verification was performed through Codex; I am not presenting those
agent-run checks as a separate personal browser test. The latest repository review
recorded 197 passing backend tests and a successful TypeScript/production build.
The suite covers validation, ownership checks, card lifecycle, qualified and
declined purchases, deposits, history, idempotency, rollback, and balance/ledger
reconciliation.

The concurrency tests include two $80 purchases against a $100 balance, expecting
one approval, one decline, and a $20 balance. Duplicate concurrent deposits must
apply only once. These checks inspect persisted results rather than relying only
on HTTP success responses. The separate fresh-stack check matters because test
fixtures apply migrations themselves and therefore cannot establish that Compose
startup initializes the application database.

There is no committed frontend interaction test suite, and the supplied logs do
not establish a completed personal browser walkthrough. The manual flow in
[README.md](README.md#reviewer-walkthrough) remains the guide for that check.

My role was to set requirements, question proposed behavior, choose tradeoffs,
and direct corrections. AI-generated code and tests were useful evidence, but
did not remove the need to understand transaction boundaries, database constraints,
retry behavior, and the simulator's limitations. Codex also drafted
`architecture.md` from the implementation and my notes, and drafted this document
from those materials and my supplied AI-usage logs.
