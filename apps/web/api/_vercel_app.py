from __future__ import annotations

from collections.abc import Awaitable, Callable
from pathlib import Path
import sys
from typing import Any


CURRENT_DIR = Path(__file__).resolve().parent
API_PACKAGE_MARKER = Path("rfq_api/__init__.py")


def _find_api_src_dir() -> Path:
    candidate_roots = [CURRENT_DIR, *CURRENT_DIR.parents[:4]]
    candidate_dirs: list[Path] = []

    for root in candidate_roots:
        candidate_dirs.extend(
            [
                root / "apps" / "api" / "src",
                root / "api" / "src",
                root / "src",
            ]
        )

    seen: set[Path] = set()
    for candidate in candidate_dirs:
        resolved = candidate.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        if (resolved / API_PACKAGE_MARKER).exists():
            return resolved

    searched = "\n".join(f"- {path}" for path in seen)
    raise RuntimeError(
        "Could not locate the bundled FastAPI source directory for the Vercel Python function. "
        f"Searched:\n{searched}"
    )


def _load_fastapi_app():
    api_src_dir = _find_api_src_dir()
    if str(api_src_dir) not in sys.path:
        sys.path.insert(0, str(api_src_dir))

    from rfq_api.main import app as fastapi_app

    return fastapi_app


class PrefixAwareASGIApp:
    def __init__(self, inner_app: Callable[[dict[str, Any], Callable[[], Awaitable[Any]], Callable[[Any], Awaitable[None]]], Awaitable[None]], prefix: str) -> None:
        self.inner_app = inner_app
        self.prefix = prefix.rstrip("/") or "/"
        self.prefix_bytes = self.prefix.encode("utf-8")

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] in {"http", "websocket"}:
            scope = self._strip_prefix(scope)
        await self.inner_app(scope, receive, send)

    def _strip_prefix(self, scope: dict[str, Any]) -> dict[str, Any]:
        path = scope.get("path", "")
        if path == self.prefix:
            return self._replace_scope(scope, "/")
        if path.startswith(f"{self.prefix}/"):
            stripped_path = path[len(self.prefix) :]
            return self._replace_scope(scope, stripped_path or "/")
        return scope

    def _replace_scope(self, scope: dict[str, Any], path: str) -> dict[str, Any]:
        updated_scope = dict(scope)
        updated_scope["path"] = path
        raw_path = scope.get("raw_path")
        if isinstance(raw_path, (bytes, bytearray)):
            if raw_path == self.prefix_bytes:
                updated_scope["raw_path"] = b"/"
            elif raw_path.startswith(self.prefix_bytes + b"/"):
                updated_scope["raw_path"] = raw_path[len(self.prefix_bytes) :] or b"/"
        return updated_scope


app = PrefixAwareASGIApp(_load_fastapi_app(), prefix="/api")
