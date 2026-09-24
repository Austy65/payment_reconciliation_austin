# from fastapi import FastAPI, Request
# from fastapi.responses import JSONResponse

# from app.db.database import Base, engine
# from app.routers import events, transactions, reconciliation

# # Create tables on startup (for local dev; in prod use Alembic migrations)
# Base.metadata.create_all(bind=engine)

# app = FastAPI(
#     title="Setu Payment Reconciliation Service",
#     description=(
#         "Backend service for ingesting payment lifecycle events, maintaining "
#         "transaction state, and identifying settlement discrepancies."
#     ),
#     version="1.0.0",
#     docs_url="/docs",
#     redoc_url="/redoc",
# )

# app.include_router(events.router)
# app.include_router(transactions.router)
# app.include_router(reconciliation.router)


# @app.get("/health", tags=["Health"])
# def health():
#     return {"status": "ok"}


# @app.exception_handler(Exception)
# async def unhandled_exception_handler(request: Request, exc: Exception):
#     return JSONResponse(
#         status_code=500,
#         content={"detail": "Internal server error", "error": str(exc)},
#     )


from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.config import settings

from app.db.database import Base, engine
from app.routers import events, transactions, reconciliation


# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     # Create tables on application startup (for local dev;
#     # in production use Alembic migrations).
#     Base.metadata.create_all(bind=engine)
#     yield

@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.APP_ENV != "test":
        Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Setu Payment Reconciliation Service",
    description=(
        "Backend service for ingesting payment lifecycle events, maintaining "
        "transaction state, and identifying settlement discrepancies."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.include_router(events.router)
app.include_router(transactions.router)
app.include_router(reconciliation.router)


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok"}


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)},
    )
