"""Template plugin — minimal example for an externally hosted 3LC compute plugin.

This plugin is loaded by pointing the 3lc-compute service at this directory's
parent (``.../hub-plugin_template/plugins``) via:

* the ``--plugin-dir`` CLI flag, or
* the ``TLC_COMPUTE_EXTERNAL_PLUGIN_DIRS`` env var, or
* a ``POST /api/admin/plugins/dirs`` request at runtime.

The compute service treats the parent ``plugins/`` directory as a "plugin
root": every immediate subdirectory containing an ``__init__.py`` is imported
as a top-level Python package and is expected to ``register()`` a
``ComputePlugin`` subclass at import time. That is exactly what this file does.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from tlc_compute.plugins.base import ComputePlugin
from tlc_compute.plugins.registry import register

_UI_PATH = Path(__file__).resolve().parent / "ui.html"


class TemplatePlugin(ComputePlugin):
    """Minimal external plugin that surfaces as a sidebar page under AI Tools."""

    id = "template-plugin"
    name = "Template Plugin"
    description = "Minimal externally hosted plugin used as a boilerplate."
    version = "0.1.0"
    min_service_version = "0.2.0"
    icon = "✦"
    display_mode = "sidebar"
    section = "AI Tools"
    priority = 10

    _ui_cache: str | None = None

    def get_ui_fragment(self) -> str:
        """Return the self-contained HTML fragment served at /api/plugins/<id>/ui."""
        if self._ui_cache is None:
            self._ui_cache = _UI_PATH.read_text(encoding="utf-8")
        return self._ui_cache

    def compute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Return a deterministic payload that proves the plugin is alive."""
        return {
            "plugin": self.id,
            "version": self.version,
            "received": params,
            "message": "Hello from the external template plugin.",
        }


register(TemplatePlugin())
