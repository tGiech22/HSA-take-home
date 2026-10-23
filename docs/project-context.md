# Project context

## What this is
An HSA (Health Savings Account) simulator built for a SWE take-home assignment.
Users can create accounts, deposit funds, issue a virtual debit card, and
simulate card transactions. The system decides whether each purchase is a
qualified medical expense and must stay correct under concurrent transactions.
Reviewers will run it locally, so setup must be simple and reliable.

## Stack (decided, don't substitute)
- Using Python FastAPI, React, Postgres SQL
- SQL Alchemy - ORM that talks to Postgres
- Alembic handles schema migrations
- Uvicorn - server that actually runs FastAPI
- Pydantic - comes with FastAPI and validates request and response models
- Vite - scaffold and run react
- Fetch - for API calls from frontend
- Tailwind CSS - styling
- CORSMiddleware - from FastAPI to connect backend and frontend
- Docker and Docker Compose - run postgres in a container so reviewer doesn’t have to install it
  - Docker compose up starts db, backend, and frontend
- Pytest or FastAPI’s TestClient for testing


## Data model
Data Representations
- Integer cents for money (never floats)
  - Floats cannot precisely represent base 10 fractions leading to rounding errors that accumulate - floats = approximations of decimals
  - Use BigINT for integer cents
  - Reject monetary amounts that are negative or zero when creating deposits or purchases
  - Use DB constraints to prevent negative balances
  - Use USD
- Have a ledger model - append only - to keep track of all transactions alongside the account balance for easy auditing
- Enums of allowed purchases for the HSA based on list outlined in general notes and research:
  - Doctor’s Visit
  - Pharmacy
  - Hospital
  - Prescription
  - Dental
  - Vision
  - Over the counter medicine
  - Preventative care
- Have a list of expense categories as well for testing that includes things like: restaurant, movies, electronics etc


Tables:
- Account
  - Account ID
  - User ID (many : 1)
  - Balance
  - Created date
- User
  - User ID
  - Name
  - Email
  - Created date
- Debit Card
  - Debit Card ID
  - Account ID (Many : 1)
  - Last 4 card numbers
  - Expiration date
  - Created date
  - Status (Active/Inactive) → 1 active card per account and NOT null
  - Card Holder name
CREATE UNIQUE INDEX one_active_card_per_account
ON debit_cards(account_id)
WHERE status = 'ACTIVE';


- Transactions
  - Transaction ID
  - Account ID (many : 1)
  - Card ID (nullable for deposits)
  - Transaction Amount
  - Balance Change Amount
  - Transaction Category
  - Transaction Created Date
  - Transaction Type
  - Transaction Status (approved/declined)
  - Transaction decline reason (nullable)
  - Idempotency Key
  - Request hash


Transaction Decline Reasons:
- Insufficient funds
- Invalid expense
- Inactive card
- Expired card


## Non-negotiable conventions
- Account balance cannot be negative
- 1 Idempotency key can’t create multiple financial operations
- Inactive/expired cards cannot make purchases
- Users cannot access other users’ accounts
- Account balance = sum of all transactions from balance change amount
- If having balance change amount and transaction amount both:
  - An approved deposit has balance_change_cents = amount_cents.
  - An approved purchase has balance_change_cents = -amount_cents.
  - A declined transaction has balance_change_cents = 0.
  - amount_cents > 0 for every row.
- Balance updates and transaction creation should be one atomic operation
- Every purchase must use a valid debit card belonging to the account
- Every completed purchase must be a qualified or valid expense
- Every declined transaction cannot affect balance (zero impact)
- Finalized and committed transactions cannot be changed to preserve audit history
- Every account starts off with zero balance
- Only one card can be active per account at any given time
- Every completed transaction has a unique idempotency key
- All money is integer cents everywhere: database, API, and server logic.
  - Convert dollars to cents only at the UI boundary. Never use floats for money.
  - Keep code simple and readable. Prefer plain functions over classes and abstractions.


## General repo structure:
- Monorepo layout
- Backend and frontend separate
- Backend/
  - Src/
    - Routes/
    - Services/
    - database/
- Frontend/
  - Src/
    - Pages/
    - Services/
    - types/
- Tests/ 
- Root/
  - Documentation
  - Packages and dependencies
Note if you have suggestions for this general repo structure section please bring them up and explain them in depth instead of just following my instructions 

## Assumptions:
- Going to assume no Auth and implement selected user model instead
- Going to assume no refunds or reversals
- Going to assume purchase qualification determined by category instead of verifying by each item
- Going to assume employer contributions are out of scope and focus only on usability for individual people
- Going to assume that users have HDHP already
- Going to assume everything is in USD and there is no currency exchange
- Going to assume all accounts are active
- Going to assume enforcing contribution limits are out of scope due to them changing every year
- Going to assume simulated deposits → no banking integration
- Going to assume no overdrafts allowed - just decline/not approve and record it
- Going to assume no HSA investments → simplify scope
- Going to assume no tax reporting 
- Going to assume 1 active debit card per account for simplicity
- Going to assume no real medical records to avoid unnecessary data
- Going to assume no account fees/interest to simplify financial calculations
- Going to assume no holds or waiting period for funds to hit account for simplicity
- Going to assume simulated Debit cards - no card network


## How to work with me
- For any task touching more than one file, first propose the files and
  approach, then wait for my approval before writing code.
- Do one task at a time. Don't modify files outside the task's scope.
- After each task, list any assumptions you made and anything you're unsure of.
- If a request conflicts with these conventions, say so instead of
  silently deviating.

