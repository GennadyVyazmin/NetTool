from typing import Literal

from pydantic import BaseModel, Field


class NetworkTargetRequest(BaseModel):
    target: str = Field(min_length=1, max_length=255)


class PortCheckRequest(NetworkTargetRequest):
    port: int = Field(ge=1, le=65535)
    timeout_seconds: float = Field(default=3.0, ge=0.2, le=10.0)


class FavoriteCreateRequest(BaseModel):
    label: str = Field(min_length=1, max_length=100)
    host: str = Field(min_length=1, max_length=255)
    init_data: str = Field(min_length=1)


class FavoriteDeleteRequest(BaseModel):
    host: str = Field(min_length=1, max_length=255)
    init_data: str = Field(min_length=1)


class AuthenticatedRequest(BaseModel):
    init_data: str = Field(min_length=1)


class FavoriteServer(BaseModel):
    id: int
    label: str
    host: str
    created_at: str


class PingHop(BaseModel):
    line: str


class PingResponse(BaseModel):
    target: str
    command: list[str]
    output: list[str]


class PortCheckResponse(BaseModel):
    target: str
    ip: str
    port: int
    reachable: bool
    latency_ms: float | None


class GeoLocationResponse(BaseModel):
    target: str
    ip: str
    country: str | None
    region: str | None
    city: str | None
    latitude: float | None
    longitude: float | None
    provider: str


class TraceResponse(BaseModel):
    target: str
    command: list[str]
    output: list[str]


class ApiError(BaseModel):
    detail: str
    code: Literal["invalid_target", "telegram_auth_failed", "network_error", "tool_missing"]
