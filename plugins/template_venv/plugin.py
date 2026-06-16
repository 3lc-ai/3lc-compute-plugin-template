"""Template VENV plugin — runs OUT-OF-PROCESS in its own virtual environment.

The compute-service reads this plugin's metadata + dependencies from its manifest
WITHOUT importing it, then launches it in a worker subprocess (its own
interpreter/venv) and talks to it over a Unix socket. This is the tier to use when
your plugin needs its own — possibly conflicting — dependencies: declare them in
``pyproject.toml`` and they live in this plugin's venv, isolated from the service.

It depends only on the **import-light** ``tlc_compute.plugin_sdk`` (not the full
server stack). This example is stdlib-only so it runs immediately on the host
interpreter; see the README to point it at a real venv with its own deps.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from tlc_compute.plugin_sdk import ComputePlugin, JobContext

_UI = Path(__file__).resolve().parent / "ui.html"


class TemplateVenvPlugin(ComputePlugin):
    """Out-of-process plugin demonstrating the v2 run_job(ctx) contract."""

    def get_ui_fragment(self) -> str:
        """Served (reverse-proxied from the worker) at /api/plugins/<id>/ui."""
        return _UI.read_text(encoding="utf-8")

    def compute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Synchronous call, proxied to the worker, at /api/plugins/<id>/compute."""
        return {"message": "Hello from the VENV template plugin.", "received": params}

    def run_job(self, ctx: JobContext) -> None:
        """A long-running job (POST /api/plugins/<id>/run).

        Reports progress/metrics and polls cancellation through ``ctx`` — it never
        touches the host GPU queue or a shared cancel flag. The same code runs in
        host or venv mode.
        """
        steps = int(ctx.params.get("steps", 5))
        ctx.log(f"starting job with {steps} steps")
        for i in range(1, steps + 1):
            if ctx.cancelled:  # cooperative checkpoint
                ctx.log(f"cancelled at step {i}")
                return
            time.sleep(0.5)  # stand-in for real work (training, etc.)
            ctx.progress(percent=100 * i / steps, label=f"step {i}/{steps}")
            ctx.metric("step", i)

    def handle(self, method: str, path: str, query: str, body: dict[str, Any]) -> tuple[int, dict[str, Any]] | None:
        """Optional custom routes, served by the worker. Return (status, json) or None."""
        if method == "GET" and path.endswith("/ping"):
            return 200, {"pong": True}
        return None
