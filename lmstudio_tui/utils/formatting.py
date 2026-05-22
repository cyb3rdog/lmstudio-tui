from __future__ import annotations


def format_bytes(n: int | float | None) -> str:
    if n is None:
        return "—"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


def format_ms(ms: float | None, decimals: int = 0) -> str:
    if ms is None:
        return "—"
    if ms >= 1000:
        return f"{ms / 1000:.2f}s"
    fmt = f"{{:.{decimals}f}}ms"
    return fmt.format(ms)


def format_tps(tps: float | None) -> str:
    if tps is None:
        return "—"
    return f"{tps:.1f} t/s"


def format_ctx(ctx: int | None) -> str:
    if ctx is None:
        return "—"
    if ctx >= 1000:
        return f"{ctx // 1000}k"
    return str(ctx)


def pct(used: float, total: float) -> float:
    if total <= 0:
        return 0.0
    return min(100.0, (used / total) * 100)
