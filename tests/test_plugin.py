# Copyright 2026 3LC Inc.
# SPDX-License-Identifier: Apache-2.0
"""The template plugin's tests — the plugin in-process, no compute service.

``PluginHarness`` builds the same Litestar app the worker serves and calls it directly, so
``/compute``, ``/ui`` and any custom route are one call away; ``lint_plugin`` checks the fragment
against the Hub's styling rules. Grow these with your plugin; drive a ``run_job`` with a
``JobContext`` whose ``sink`` is a list (see the example plugin's tests).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from tlc_plugin_sdk.harness import PluginHarness
from tlc_plugin_sdk.lint import lint_plugin

PLUGIN_DIR = Path(__file__).resolve().parents[1] / "src" / "tlc_plugin_template"


@pytest.fixture(scope="module")
def harness():
    """The plugin's app, loaded from its manifest the way a host would."""
    with PluginHarness.from_manifest(PLUGIN_DIR) as h:
        yield h


def test_compute_answers(harness: PluginHarness) -> None:
    answer = harness.get("/compute", params={"greeting": "hi"}).json()
    assert answer["received"] == {"greeting": "hi"}


def test_the_fragment_is_served(harness: PluginHarness) -> None:
    ui = harness.get("/ui").text
    assert 'class="template-plugin"' in ui
    assert "window.PluginJobs" in ui  # added by the worker's /ui handler


def test_the_ui_follows_the_hub_styling_conventions() -> None:
    findings = lint_plugin(PLUGIN_DIR)
    assert not findings, "\n".join(map(str, findings))
