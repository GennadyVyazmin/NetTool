from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.database import init_db
from app.repository import delete_favorite, list_favorites, save_favorite
from app.schemas import (
    AuthenticatedRequest,
    FavoriteCreateRequest,
    FavoriteDeleteRequest,
    GeoLocationResponse,
    NetworkTargetRequest,
    PingResponse,
    PortCheckRequest,
    PortCheckResponse,
    TraceResponse,
)
from app.security import validate_telegram_init_data
from app.services.geolocation import lookup_ip_location
from app.services.network_tools import check_port, normalize_target, ping_target, traceroute_target


BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="NetTool Telegram WebApp",
    version="1.0.0",
    lifespan=lifespan,
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.post("/api/ping", response_model=PingResponse)
async def ping_api(payload: NetworkTargetRequest) -> PingResponse:
    command, output = await ping_target(payload.target)
    return PingResponse(target=payload.target, command=command, output=output)


@app.post("/api/traceroute", response_model=TraceResponse)
async def traceroute_api(payload: NetworkTargetRequest) -> TraceResponse:
    command, output = await traceroute_target(payload.target)
    return TraceResponse(target=payload.target, command=command, output=output)


@app.post("/api/geo", response_model=GeoLocationResponse)
async def geo_api(payload: NetworkTargetRequest) -> GeoLocationResponse:
    return GeoLocationResponse(**(await lookup_ip_location(payload.target)))


@app.post("/api/port-check", response_model=PortCheckResponse)
async def port_check_api(payload: PortCheckRequest) -> PortCheckResponse:
    ip_address_text, reachable, latency_ms = await check_port(
        payload.target,
        payload.port,
        payload.timeout_seconds,
    )
    return PortCheckResponse(
        target=payload.target,
        ip=ip_address_text,
        port=payload.port,
        reachable=reachable,
        latency_ms=latency_ms,
    )


@app.post("/api/favorites")
async def favorites_list_api(payload: AuthenticatedRequest) -> dict:
    user = validate_telegram_init_data(payload.init_data)
    favorites = list_favorites(int(user["id"]))
    return {"items": [item.model_dump() for item in favorites]}


@app.put("/api/favorites")
async def favorites_save_api(payload: FavoriteCreateRequest) -> dict:
    user = validate_telegram_init_data(payload.init_data)
    save_favorite(
        int(user["id"]),
        payload.label.strip(),
        normalize_target(payload.host),
    )
    return {"ok": True}


@app.delete("/api/favorites")
async def favorites_delete_api(payload: FavoriteDeleteRequest) -> dict:
    user = validate_telegram_init_data(payload.init_data)
    deleted = delete_favorite(int(user["id"]), normalize_target(payload.host))
    return {"ok": deleted}
