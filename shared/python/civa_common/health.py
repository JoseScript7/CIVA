"""Standard health check for CIVA services."""

import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DependencyCheck:
    name: str
    status: str = "unknown"  # ok, degraded, unavailable
    latency_ms: float = 0.0
    error: Optional[str] = None


@dataclass
class HealthStatus:
    status: str = "healthy"  # healthy, degraded, unhealthy
    service: str = ""
    version: str = ""
    uptime_seconds: float = 0.0
    dependencies: list[DependencyCheck] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "service": self.service,
            "version": self.version,
            "uptime_seconds": round(self.uptime_seconds, 2),
            "dependencies": [
                {
                    "name": d.name,
                    "status": d.status,
                    "latency_ms": round(d.latency_ms, 2),
                    "error": d.error,
                }
                for d in self.dependencies
            ],
        }


class HealthCheck:
    """Standard health check for CIVA services."""

    def __init__(self, service: str, version: str):
        self.service = service
        self.version = version
        self._start_time = time.time()
        self._checks: list[tuple[str, callable]] = []

    def register_check(self, name: str, check_fn: callable) -> None:
        """Register a dependency health check function."""
        self._checks.append((name, check_fn))

    async def check(self) -> HealthStatus:
        """Run all health checks and return aggregated status."""
        health = HealthStatus(
            service=self.service,
            version=self.version,
            uptime_seconds=time.time() - self._start_time,
        )

        all_ok = True
        for name, check_fn in self._checks:
            dep = DependencyCheck(name=name)
            start = time.perf_counter()
            try:
                result = await check_fn() if callable(check_fn) else check_fn
                dep.status = "ok" if result else "degraded"
                if dep.status == "degraded":
                    all_ok = False
            except Exception as e:
                dep.status = "unavailable"
                dep.error = str(e)
                all_ok = False
            finally:
                dep.latency_ms = (time.perf_counter() - start) * 1000
            health.dependencies.append(dep)

        health.status = "healthy" if all_ok else "degraded"
        return health
