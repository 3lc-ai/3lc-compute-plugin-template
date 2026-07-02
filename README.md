# 3lc-compute-plugin-template

The starting point for writing a [3LC compute service](https://github.com/3lc-ai) plugin.
This is a **GitHub template repository**: click **Use this template** (top right) and you get
a fresh repo — your name, your history — containing the smallest viable plugin, ready to
rename and grow. Nothing in it is scaffolding you delete; everything is something you edit.

Want to see what a plugin can *do* first? The example plugin,
[**Mission Control**](https://github.com/3lc-ai/3lc-compute-plugin-example), is a runnable
tour of the whole contract — jobs with live progress and abort, custom REST routes, the
typed UI bridge, lifecycle hooks. Crib from it as you grow. The full contract reference
lives in the
[**plugin author guide**](https://github.com/3lc-ai/3lc-compute-plugin-sdk/blob/main/docs/plugin-guide.md)
(`3lc-compute-plugin-sdk`).

## What's in the box

```
├── pyproject.toml            # one dist; your plugin's extra + entry point
├── catalog.json              # your shop listing — point it at your repo (see below)
├── jsconfig.json             # types for window.PLUGIN_API in ui.html
├── .github/workflows/ci.yml  # ruff lint + format, standalone
└── src/
    └── tlc_plugin_template/  # ← rename me
        ├── plugin.toml       #    manifest (metadata; read without import)
        ├── __init__.py       #    the ComputePlugin subclass (behavior only)
        └── ui.html           #    the UI fragment
```

The plugin is `venv`-isolated: the host reads `plugin.toml` **without importing it**,
provisions the plugin its own virtual environment, and runs it out-of-process behind a
reverse proxy. Your dependencies live in your plugin's extra in
[`pyproject.toml`](pyproject.toml) and never touch the host venv — pin anything you like.

## Make it yours

After **Use this template**, four renames:

1. **The package.** `src/tlc_plugin_template` → `src/tlc_plugin_<yours>` (package names must
   be valid Python identifiers; the public `id` in the manifest is independent and may use
   hyphens).
2. **The manifest.** In `plugin.toml`, set `id`, `name`, `description`, and the
   `runtime.entrypoint` / `provision_extra` to match. The example's
   [`plugin.toml`](https://github.com/3lc-ai/3lc-compute-plugin-example/blob/main/src/tlc_plugin_example/plugin.toml)
   documents every optional field.
3. **The dist.** In [`pyproject.toml`](pyproject.toml): project `name`, your extra under
   `[project.optional-dependencies]` (your dependencies go there), the entry point, and the
   package path under `[tool.hatch.build.targets.wheel]`.
4. **The catalog.** In [`catalog.json`](catalog.json): `id`, the manifest copy, and the
   `source` — point it at *your* repo (see below).

Then fill in the class: `compute()` and `get_ui_fragment()` are the whole required contract;
grow into `run_job(ctx)` and `get_route_handlers()` by cribbing from
[the example](https://github.com/3lc-ai/3lc-compute-plugin-example).

## Run it

```bash
# Point a compute service at the src/ folder (repeatable flag, or use the
# TLC_COMPUTE_EXTERNAL_PLUGIN_DIRS env var):
3lc-compute --plugin-dir /path/to/your-repo/src
```

The service discovers the plugin, provisions it a venv (`uv sync --extra <yours>` against
your repo — first run takes a few seconds), and it appears in the Hub sidebar. Or skip the
Hub:

```bash
curl http://localhost:5020/api/plugins/manifest/template
curl http://localhost:5020/api/plugins/template/compute
```

### The dev loop

Code edits go live with a reload — no service restart:

```bash
# Reload everything under the plugin dir (re-provisions venvs when deps changed):
curl -X POST http://localhost:5020/api/admin/plugins/dirs/reload \
  -H 'Content-Type: application/json' \
  -d '{"directory": "/path/to/your-repo/src"}'
```

Lint like CI does (standalone — no deps to resolve):

```bash
uvx --from 'ruff>=0.15,<0.16' ruff check .
uvx --from 'ruff>=0.15,<0.16' ruff format .
```

To develop against a sibling SDK checkout, override its source **uncommitted**:

```toml
# pyproject.toml [tool.uv.sources]  (local dev only — do not commit)
3lc-compute-plugin-sdk = { path = "../3lc-plugin-sdk", editable = true }
```

### Editor autocomplete for `ui.html`

Your fragment talks to the host through `window.PLUGIN_API` / `window.PluginJobs`, and both
are **typed**: the declaration ships inside the pip-installed SDK wheel, and the repo-root
[`jsconfig.json`](jsconfig.json) points TypeScript at it. Run `uv sync` once (creates
`.venv/`) and VS Code autocompletes the whole bridge inside `ui.html` — no node, no build
step.

## The catalog: one-click install from GitHub

[`catalog.json`](catalog.json) is your plugin's shop listing — a static JSON file with
versions, a raw copy of the manifest (so the Hub can render a card and check compatibility
**without downloading anything**), and an install source. The committed one points at this
template repo; after **Use this template**, edit the `source` to point at your repo:

```
your-dist-name[your-extra] @ git+https://github.com/you/your-repo.git@main
```

No wheel publishing required — the `[extra]` selects your plugin and the venv materializes
straight from the git source. Hand out one URL and anyone can install it, via the Hub's
Plugins page or:

```bash
curl -X POST http://localhost:5020/api/admin/plugins/catalogs \
  -H 'Content-Type: application/json' \
  -d '{"url": "https://raw.githubusercontent.com/you/your-repo/main/catalog.json", "persist": true}'
```

## License

Apache-2.0 — see [LICENSE](LICENSE). Repos generated from this template are yours to
license as you wish.
