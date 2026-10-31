# Copyright 2026 3LC Inc.
# SPDX-License-Identifier: Apache-2.0
"""The template plugin — the smallest viable 3LC compute-service plugin.

Copy this package, rename it, and replace the two method bodies. All metadata lives
in ``plugin.toml`` (read without importing this module); this class carries only
behavior. The two methods below are the whole required contract:

- ``get_ui_fragment()`` — the plugin's UI, one self-contained HTML fragment;
- ``compute(params)``   — a synchronous call, served at ``GET /api/plugins/template/compute``.

Everything else is optional. When you outgrow this skeleton, the example plugin
(https://github.com/3lc-ai/3lc-compute-plugin-example) shows the full surface:
``run_job(ctx)`` for long jobs with progress, a clean failure and cancellation,
``get_route_handlers()`` for custom REST routes, the shared data-source picker, and the
runtime lifecycle hooks. ``ComputePlugin`` is the base for a plugin that runs jobs; its
parent ``HubPlugin`` (fragment, ``compute``, routes) is enough for one that never will.

``tests/test_plugin.py`` runs this plugin in-process through ``tlc_plugin_sdk.harness``
and checks the fragment with ``tlc_plugin_sdk.lint`` — no compute service needed.
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
        """Return the fragment served at ``GET /api/plugins/template/ui``.

        The worker adds the ``window.PluginJobs`` client to every fragment; inject other SDK
        scripts (the data-source picker, the preset bar) with ``inject_scripts`` here.
        """
        return _UI.read_text(encoding="utf-8")

    def compute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Answer ``GET /api/plugins/template/compute`` — replace with your logic."""
        return {"message": "Hello from the template plugin.", "received": params}
