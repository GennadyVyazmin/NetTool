import httpx
from fastapi import HTTPException, status

from app.config import get_settings
from app.services.network_tools import resolve_host


async def lookup_ip_location(target: str) -> dict:
    ip_address_text = await resolve_host(target)
    settings = get_settings()
    url = f"{settings.geolookup_url.rstrip('/')}/{ip_address_text}"

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.get(url)
            response.raise_for_status()
    except httpx.HTTPError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Geo lookup provider is unavailable.",
        ) from error

    payload = response.json()
    success = payload.get("success", True)
    if success is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=payload.get("message", "Geo lookup failed."),
        )

    return {
        "target": target,
        "ip": ip_address_text,
        "country": payload.get("country"),
        "region": payload.get("region"),
        "city": payload.get("city"),
        "latitude": payload.get("latitude"),
        "longitude": payload.get("longitude"),
        "provider": settings.geolookup_url,
    }
