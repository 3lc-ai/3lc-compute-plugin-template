# Copyright 2026 3LC Inc.
# SPDX-License-Identifier: Apache-2.0
"""The template plugin — the smallest viable 3LC compute-service plugin.

Copy this package, rename it, and replace the two method bodies. All metadata lives
in ``plugin.toml`` (read without importing this module); this class carries only
behavior. The two methods below are the whole required contract:

- ``get_ui_fragment()`` — the plugin's UI, one self-contained HTML fragment;
- ``compute(params)``   — a synchronous call, served at ``GET /api/plugins/template/compute``.

Everything else is optional. When you outgrow this skeleton, ``tlc_plugin_example``
(next door) shows the full surface: ``run_job(ctx)`` for long jobs with progress and
cancellation, ``get_route_handlers()`` for custom REST routes, and the runtime
lifecycle hooks.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from tlc_plugin_sdk import ComputePlugin

_UI = Path(__file__).resolve().parent / "ui.html"


class TemplatePlugin(ComputePlugin):
    """Behavior only — metadata comes from ``plugin.toml``."""

    # Display identity stamped onto the instance by the host from the manifest.
    id: str

    def get_ui_fragment(self) -> str:
        """Return the fragment served at ``GET /api/plugins/template/ui``."""
        return _UI.read_text(encoding="utf-8")

    def compute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Answer ``GET /api/plugins/template/compute`` — replace with your logic."""
        return {"message": "Hello from the template plugin.", "received": params}
