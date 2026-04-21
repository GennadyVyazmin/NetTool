import asyncio
import ipaddress
import shutil
import socket
from time import perf_counter

from fastapi import HTTPException, status


def normalize_target(target: str) -> str:
    cleaned = target.strip()
    if not cleaned:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Target is required.")

    try:
        ipaddress.ip_address(cleaned)
        return cleaned
    except ValueError:
        pass

    if len(cleaned) > 253:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Target is too long.")

    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-")
    if any(char not in allowed for char in cleaned):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only IPv4/IPv6 addresses and DNS hostnames are allowed.",
        )

    return cleaned.rstrip(".")


def require_command(command: str) -> str:
    found = shutil.which(command)
    if not found:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Required command '{command}' is not installed on the server.",
        )
    return found


async def run_command(command: list[str], timeout_seconds: float = 20.0) -> list[str]:
    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    try:
        stdout, _ = await asyncio.wait_for(process.communicate(), timeout=timeout_seconds)
    except TimeoutError as error:
        process.kill()
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Network tool timed out.",
        ) from error

    output = stdout.decode("utf-8", errors="replace").splitlines()
    return output or ["No output produced."]


async def ping_target(target: str) -> tuple[list[str], list[str]]:
    normalized = normalize_target(target)
    ping_path = require_command("ping")
    command = [ping_path, "-c", "4", "-W", "2", normalized]
    return command, await run_command(command, timeout_seconds=15.0)


async def traceroute_target(target: str) -> tuple[list[str], list[str]]:
    normalized = normalize_target(target)
    traceroute_path = require_command("traceroute")
    command = [traceroute_path, "-m", "12", "-w", "2", normalized]
    return command, await run_command(command, timeout_seconds=35.0)


async def resolve_host(target: str) -> str:
    normalized = normalize_target(target)

    def _resolve() -> str:
        info = socket.getaddrinfo(normalized, None, proto=socket.IPPROTO_TCP)
        return info[0][4][0]

    try:
        return await asyncio.to_thread(_resolve)
    except socket.gaierror as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not resolve target host.",
        ) from error


async def check_port(target: str, port: int, timeout_seconds: float) -> tuple[str, bool, float | None]:
    normalized = normalize_target(target)
    ip_address_text = await resolve_host(normalized)

    def _connect() -> tuple[bool, float | None]:
        started = perf_counter()
        try:
            with socket.create_connection((normalized, port), timeout=timeout_seconds):
                latency_ms = (perf_counter() - started) * 1000
                return True, round(latency_ms, 2)
        except OSError:
            return False, None

    reachable, latency_ms = await asyncio.to_thread(_connect)
    return ip_address_text, reachable, latency_ms
