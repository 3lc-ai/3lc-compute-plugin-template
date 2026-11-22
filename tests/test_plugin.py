# Copyright 2026 3LC Inc.
# SPDX-License-Identifier: Apache-2.0
"""The plugin imports through its entry point, and its project files agree.

Every name comes from pyproject.toml and plugin.toml, so a renamed plugin passes unchanged.
"""

import importlib
import importlib.metadata
import json
import tomllib
from pathlib import Path

from tlc_plugin_sdk import ComputePlugin

ROOT = Path(__file__).resolve().parents[1]
PROJECT = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
[(ENTRY_NAME, PACKAGE)] = PROJECT["entry-points"]["tlc_compute.plugins"].items()
MANIFEST = tomllib.loads((ROOT / "src" / PACKAGE / "plugin.toml").read_text(encoding="utf-8"))
CATALOG = json.loads((ROOT / "catalog.json").read_text(encoding="utf-8"))


def test_plugin_imports_through_its_entry_point() -> None:
    [entry_point] = [ep for ep in importlib.metadata.entry_points(group="tlc_compute.plugins") if ep.name == ENTRY_NAME]
    assert entry_point.load().__name__ == PACKAGE
    module, _, cls = MANIFEST["runtime"]["entrypoint"].partition(":")
    plugin = getattr(importlib.import_module(module), cls)()
    assert isinstance(plugin, ComputePlugin)
    assert plugin.get_ui_fragment().strip()


def test_project_files_agree() -> None:
    assert MANIFEST["version"] == PROJECT["version"]
    assert MANIFEST["runtime"]["entrypoint"].split(":")[0].split(".")[0] == PACKAGE
    extra = MANIFEST["runtime"]["provision_extra"]
    assert extra in PROJECT["optional-dependencies"]
    [listing] = CATALOG["plugins"]
    assert listing["id"] == MANIFEST["id"]
    # The catalog lists this version, its source installs this dist's extra, and its manifest
    # is plugin.toml exactly: the Hub decides compatibility from it without downloading.
    [entry] = [version for version in listing["versions"] if version["version"] == PROJECT["version"]]
    assert entry["source"].startswith(f"{PROJECT['name']}[{extra}]")
    assert entry["manifest"] == MANIFEST
