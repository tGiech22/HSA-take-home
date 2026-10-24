from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import settings
from src.routes.accounts import router as accounts_router
from src.routes.cards import router as cards_router
from src.routes.purchases import router as purchases_router
from src.routes.deposits import router as deposits_router
from src.routes.users import router as users_router
from src.routes.transactions import router as transactions_router

app = FastAPI(title="HSA Simulator")
app.include_router(users_router)
app.include_router(accounts_router)
app.include_router(deposits_router)
app.include_router(cards_router)
app.include_router(purchases_router)
app.include_router(transactions_router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Idempotency-Key"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
