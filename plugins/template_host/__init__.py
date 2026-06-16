"""Template HOST plugin — runs in-process inside the compute-service.

Metadata lives in ``plugin.toml`` and is read **without importing this module**, so
even a plugin with a broken dependency still lists (greyed-out) instead of vanishing.
The compute-service imports the ``entrypoint`` declared in the manifest and
instantiates this class — there is **no metadata on the class and no
``register()``-at-import**.

Use the ``host`` tier when your dependencies are a subset of the compute-service's
(no extra installs needed). If you need your own/conflicting deps, use the ``venv``
tier — see ``../template_venv``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from tlc_compute.plugins.base import ComputePlugin

_UI = Path(__file__).resolve().parent / "ui.html"


class TemplateHostPlugin(ComputePlugin):
    """Minimal in-process plugin. Behavior only — metadata comes from plugin.toml."""

    def get_ui_fragment(self) -> str:
        """Return the self-contained UI fragment served at /api/plugins/<id>/ui."""
        return _UI.read_text(encoding="utf-8")

    def compute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Return a deterministic payload proving the plugin is alive."""
        return {"message": "Hello from the HOST template plugin.", "received": params}
