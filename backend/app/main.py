from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.paths import FRONTEND
from app.wiring import build_store


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.store = build_store()
    yield


app = FastAPI(title="BookNest", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)


@app.exception_handler(RequestValidationError)
async def invalid_request(_request, exc: RequestValidationError):
    parts = []
    for error in exc.errors():
        location = [str(item) for item in error.get("loc", []) if item not in ("body", "query", "path")]
        message = error.get("msg", "Invalid value")
        if location:
            parts.append(f"{'.'.join(location)}: {message}")
        else:
            parts.append(message)
    detail = "; ".join(parts) if parts else "Invalid request"
    return JSONResponse(status_code=422, content={"detail": detail})


if FRONTEND.is_dir():
    app.mount("/", StaticFiles(directory=str(FRONTEND), html=True), name="frontend")
