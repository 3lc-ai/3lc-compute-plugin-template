# 3lc-compute-plugin-template

The starting point for writing a [3LC compute service](https://github.com/3lc-ai) plugin —
and a runnable tour of what one can do. Two plugins ship in this repo:

| | [`template`](src/tlc_plugin_template) | [`example` — Mission Control](src/tlc_plugin_example) |
|---|---|---|
| What it is | The bare-bones skeleton you **copy** to start | A working tour of the **whole** contract, staged as a rocket launch |
| Files | `plugin.toml` + `__init__.py` + `ui.html` | + `routes.py` (custom REST) + `patch.py` (binary asset) |
| Shows | manifest, `compute()`, a UI fragment | + `run_job(ctx)` jobs with live progress/metrics/telemetry and abort, custom routes (JSON, 404, binary PNG, raw upload), `PLUGIN_API`/`TlcData`/`PluginJobs`, lifecycle hooks, quick actions |

Both are `venv`-isolated: the host reads each plugin's `plugin.toml` **without importing it**,
provisions the plugin its own virtual environment, and runs it out-of-process behind a
reverse proxy. Your dependencies live in your plugin's extra in [`pyproject.toml`](pyproject.toml)
and never touch the host venv — pin anything you like.

The full contract reference lives in the
[**plugin author guide**](https://github.com/3lc-ai/3lc-compute-plugin-sdk/blob/main/docs/plugin-guide.md)
(`3lc-compute-plugin-sdk`). This README gets you running.

## Try it in two minutes

```bash
git clone https://github.com/3lc-ai/3lc-compute-plugin-template
# Point a compute service at the src/ folder (repeatable flag, or use the
# TLC_COMPUTE_EXTERNAL_PLUGIN_DIRS env var):
3lc-compute --plugin-dir /path/to/3lc-compute-plugin-template/src
```

The service discovers both plugins, provisions each a venv (`uv sync --extra <plugin>` against
this repo — first run takes a few seconds), and they appear in the Hub sidebar under
**Examples**. Open **Mission Control**, poll go/no-go, recruit some crew, and launch a mission —
then watch the same job stream into the generic Queue & Progress panel.

No Hub handy? The whole surface also speaks curl:

```bash
curl http://localhost:5020/api/plugins/manifest/example
curl 'http://localhost:5020/api/plugins/example/compute?station=all'      # go/no-go
curl http://localhost:5020/api/plugins/example/crew                       # custom route
curl http://localhost:5020/api/plugins/example/crew/elvis                 # → 404
curl -o patch.png http://localhost:5020/api/plugins/example/patch.png     # binary route
curl -N -X POST http://localhost:5020/api/plugins/example/run \
  -H 'Content-Type: application/json' -d '{"destination": "Mars"}'        # streaming job
```

## Start your own plugin

1. **Copy the skeleton.** Duplicate `src/tlc_plugin_template` → `src/tlc_plugin_<yours>`
   (package names must be valid Python identifiers; the public `id` in the manifest is
   independent and may use hyphens).
2. **Edit `plugin.toml`.** Set `id`, `name`, `entrypoint`, and `provision_extra`. The
   example's [`plugin.toml`](src/tlc_plugin_example/plugin.toml) documents every field.
3. **Register it in [`pyproject.toml`](pyproject.toml).** Add an extra named after your
   plugin (your dependencies go there), an entry in `[project.entry-points."tlc_compute.plugins"]`,
   and your package under `[tool.hatch.build.targets.wheel]`.
4. **Fill in the class.** `compute()` and `get_ui_fragment()` are the whole required
   contract; grow into `run_job(ctx)` and `get_route_handlers()` by cribbing from the example.

Or lift the whole repo shape into a repository of your own — that *is* the intended use.

### The dev loop

Code edits go live with a reload — no service restart:

```bash
# Reload everything under the plugin dir (re-provisions venvs when deps changed):
curl -X POST http://localhost:5020/api/admin/plugins/dirs/reload \
  -H 'Content-Type: application/json' \
  -d '{"directory": "/path/to/3lc-compute-plugin-template/src"}'
```

Lint like CI does (standalone — no deps to resolve):

```bash
uvx --from 'ruff>=0.15,<0.16' ruff check .
uvx --from 'ruff>=0.15,<0.16' ruff format .
```

To develop against a sibling SDK checkout, override its source **uncommitted**:

```toml
# pyproject.toml [tool.uv.sources]  (local dev only — do not commit)
3lc-compute-plugin-sdk = { path = "../3lc-compute-plugin-sdk", editable = true }
```

### Editor autocomplete for `ui.html`

A fragment talks to the host through `window.PLUGIN_API` / `window.PluginJobs`, and both are
**typed**: the declaration ships inside the pip-installed SDK wheel, and the repo-root
[`jsconfig.json`](jsconfig.json) points TypeScript at it. Run `uv sync` once (creates `.venv/`)
and VS Code autocompletes the whole bridge inside every `ui.html` — no node, no build step.

## The catalog: one-click install from GitHub

This repo bakes its own shop listing: [`catalog.json`](catalog.json). A catalog is a static
JSON file listing plugins, each with versions, a raw manifest (so the Hub can render cards and
check compatibility **without downloading anything**), and an install source. Ours points
straight back at this repo:

```
3lc-compute-plugin-template[example] @ git+https://github.com/3lc-ai/3lc-compute-plugin-template.git@main
```

The `[extra]` is what selects one plugin out of a multi-plugin repo — no wheel publishing
required. To use it, add the catalog to a running service (persisted across restarts):

```bash
curl -X POST http://localhost:5020/api/admin/plugins/catalogs \
  -H 'Content-Type: application/json' \
  -d '{"url": "https://raw.githubusercontent.com/3lc-ai/3lc-compute-plugin-template/main/catalog.json", "persist": true}'
```

…or paste that URL into the Hub's Plugins page. **Mission Control** and **Template** show up
as installable cards; installing materializes a managed venv from the git source and registers
the plugin live. Ship your own plugin the same way: commit a `catalog.json` next to it, point
the source at your repo, and hand out one URL.

## Repo layout

```
├── pyproject.toml            # one umbrella dist; per-plugin extras + entry points
├── catalog.json              # the shop listing — install either plugin from GitHub
├── jsconfig.json             # types for window.PLUGIN_API in every ui.html
└── src/
    ├── tlc_plugin_template/  # ← copy me
    │   ├── plugin.toml       #    manifest (metadata; read without import)
    │   ├── __init__.py       #    the ComputePlugin subclass (behavior only)
    │   └── ui.html           #    the UI fragment
    └── tlc_plugin_example/   # ← crib from me
        ├── plugin.toml       #    every manifest field, annotated
        ├── __init__.py       #    compute + run_job + lifecycle hooks
        ├── routes.py         #    custom REST routes, one of every response shape
        ├── patch.py          #    a generated binary asset (stdlib-only PNG)
        └── ui.html           #    the full PLUGIN_API / PluginJobs tour
```

## License

Apache-2.0 — see [LICENSE](LICENSE).
