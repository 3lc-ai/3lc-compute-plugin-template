# 3LC compute-plugin contract — condensed reference

Condensed from the canonical public docs; when in doubt, they win:

- Author guide: https://3lc-ai.github.io/3lc-compute-plugin-sdk/plugin-guide.html
- API reference: https://3lc-ai.github.io/3lc-compute-plugin-sdk/api.html
- SDK repo (incl. agent guidance in its CLAUDE.md): https://github.com/3lc-ai/3lc-compute-plugin-sdk
- Example plugin, "Mission Control" — a runnable tour of every surface below:
  https://github.com/3lc-ai/3lc-compute-plugin-example

## The model

Each plugin is a self-contained package: Python behavior + one HTML fragment + optional
REST routes + optional long-running jobs. The host (the 3LC compute service, port 5020)
reads the plugin's `plugin.toml` **without importing it**, provisions the plugin its own
uv-managed venv (`uv sync --extra <provision_extra>`), runs it out-of-process behind a
reverse proxy, and serves it at `/api/plugins/{id}/…`. The Hub frontend has zero knowledge
of any specific plugin — it renders sidebar entries and the generic job panel purely from
manifests and the generic job schema.

Plugins must **not** access the 3LC Object Service directly (it may be unreachable from the
plugin's environment) — all data access goes through the `tlc` SDK server-side.

## Manifest (`plugin.toml`)

The single source of the plugin's metadata; the class carries none.

```toml
id = "my-plugin"                    # URL-safe slug; also the SocketIO namespace "/<id>"
name = "My Plugin"
description = "One user-facing sentence."
version = "0.1.0"                   # SemVer; bump on every release
min_service_version = "0.1.0"
icon = "🔍"                         # fallback emoji
# Optional: icon_svg = '<svg …>'   # inline 16x16 SVG

[ui]
display_mode = "sidebar"            # sidebar | action | hidden
section = "Tools"                   # sidebar grouping label
compatible_with = ["table"]         # resource types this acts on: "table" | "run"
# input_types / output_types / priority / quick_action also available

[runtime]
isolation = "venv"                  # keep "venv" — out-of-process in the plugin's own venv
entrypoint = "tlc_plugin_my_plugin:MyPlugin"   # "package.module:ClassName"
provision_extra = "my-plugin"       # REQUIRED: the extra in pyproject.toml the host installs
# requires_gpu = true               # routes jobs through the shared GPU queue (one at a time)
# socketio_namespace = "/my-plugin" # defaults to "/<id>"; declare only to override
```

`display_mode`: `sidebar` = a nav item under `section`; `action` = a button on resource
pages (tables/runs), receiving the selected resources; `hidden` = API-only, no UI entry.

## The plugin class

Subclass `ComputePlugin` (from `tlc_plugin_sdk`). Two abstract methods are the whole
required contract; everything else is a no-op default you override only when needed. There
is **no** `register()`, and no `get_active_jobs`/`cancel_job` — the host owns job listing
and cancellation.

```python
from tlc_plugin_sdk import ComputePlugin

class MyPlugin(ComputePlugin):
    id: str  # stamped onto the instance by the host from the manifest

    def get_ui_fragment(self) -> str: ...          # required — GET /api/plugins/{id}/ui
    def compute(self, params) -> dict: ...          # required — GET /api/plugins/{id}/compute
    def run_job(self, ctx) -> None: ...             # optional — long-running work
    def get_route_handlers(self) -> list: ...       # optional — custom REST routes
    def initialise_runtime(self) -> None: ...       # optional — one-time setup (models, stores)
    def shutdown_runtime(self) -> None: ...         # optional — teardown; safe if never initialised
```

`compute(params)` receives the query params of `GET /api/plugins/{id}/compute` and returns
a JSON-able dict. Error convention: bad input → `{"error": "…"}`; execution outcome →
`{"success": true/false, "message": "…"}`; not found in routes → `HTTPException(404)`.

## Long-running jobs — `run_job(ctx)`

The UI starts a job with `POST /api/plugins/{id}/run` (JSON body = params) and the host
calls `run_job(ctx)` on a worker thread. The host owns the queue, the GPU/CPU slot,
progress fan-out, the generic Queue & Progress panel, and cancellation — the plugin only
runs the job and talks to `ctx` (`JobContext`):

| Member | Purpose |
|---|---|
| `ctx.job_id` | unique id for this job |
| `ctx.params` | parsed request body / query |
| `ctx.cancelled` | `True` once cancel requested — poll at checkpoints, return cleanly |
| `ctx.state_dir` | writable per-plugin scratch dir (never write inside the package) |
| `ctx.progress(*, percent, label="", timing=None)` | generic progress bar; `percent=-1` = indeterminate |
| `ctx.metric(label, value)` | scalar metric card on the generic panel |
| `ctx.log(message)` | a log line for the job |
| `ctx.result(*, run_url)` | the canonical "open result" link (last write wins) |
| `ctx.emit(name, payload)` | plugin-private event for this plugin's own UI only |

Rules: `run_job` is a plain `def` (never `async`); raise to fail the job; keep
plugin-specific fields (epoch, loss, model name, …) out of `progress`/`metric` — those feed
the plugin-agnostic panel; use `ctx.emit` for anything richer, consumed only by your own
`ui.html`. The event name `job_update` is reserved.

## Custom REST routes

A module-level `get_route_handlers()` (conventionally in `routes.py`) returning bare
`@get`/`@post` Litestar handlers with **relative** paths — no `Controller`, no
`/api/plugins` prefix. They resolve under `/api/plugins/{id}/…`.

```python
from typing import Any
from litestar import get, post

def get_route_handlers() -> list[Any]:
    @get("/status", sync_to_thread=False)
    async def get_status() -> dict[str, Any]:
        return {"ready": True}

    @post("/analyze", sync_to_thread=True)   # sync_to_thread=True for blocking work
    def analyze(data: dict[str, Any]) -> dict[str, Any]:
        return {"result": "done"}

    return [get_status, analyze]
```

Don't add job routes (`/queue`, `/cancel/{id}`, a start route) — the generic
`POST /api/plugins/{id}/run`, `GET /api/plugins/jobs`, and
`POST /api/plugins/jobs/{job_id}/cancel` cover the job lifecycle. Custom routes carry only
genuinely plugin-specific surface (config CRUD, metadata lookups, uploads, …).

## UI fragment (`ui.html`)

One self-contained `<style>` + markup + `<script>` block, mounted into the Hub page.
The same bytes serve host- and venv-isolated plugins.

**The bridge.** Reach the host only through `window.PLUGIN_API` — never bare `fetch`.
It is typed: the repo-root `jsconfig.json` points the editor at `plugin-api.d.ts` inside
the installed SDK wheel (run `uv sync` once and hover works). Key surface:

```javascript
var API = window.PLUGIN_API;
var base = API.getConfig('compute_service_url');   // also: dashboard_url, object_service_url
API.context.resourceType;    // "table" | "run" | null (for action plugins)
API.context.resourceUrls;    // selected resource URLs
API.context.projectName;
API.authFetch(url, opts);    // fetch with auth header; rejects non-ok with parsed detail
API.showToast(msg, 'success'|'error'|'info');
API.libs.io;                 // Socket.IO client — the ONLY libs member that is stable;
                             // Chart / html2canvas / PptxGenJS / cytoscape are best-effort
```

**Jobs from the UI.** Use `window.PluginJobs` — injected server-side in
`get_ui_fragment()`:

```python
from tlc_plugin_sdk.shared.job_tracker import job_tracker_script
from tlc_plugin_sdk.shared.ui_inject import inject_scripts
return inject_scripts(_UI.read_text(encoding="utf-8"), job_tracker_script())
```

```javascript
PluginJobs.run('my-plugin', { table_url: url }, {
  onUpdate: function (job) { /* job.status, job.progress.percent/label, job.metrics[] */ },
  onDone:   function (job) { /* job.run_url */ },
  onError:  function (job) { /* failure message rides job.subtitle */ },
});
// plugin-private ctx.emit events, on the same namespace:
var socket = PLUGIN_API.libs.io(base + '/my-plugin');
socket.on('telemetry', function (d) { /* … */ });
```

**Styling.** Inherit the house CSS; never hardcode colors — use
`var(--text)`, `var(--text-muted)`, `var(--bg)`, `var(--bg-card)`, `var(--border)`,
`var(--accent)`, `var(--error)`, `var(--code-bg)`. Shared classes:
`.plugin-page` (1200px) / `.plugin-page-narrow` (700px), `.card`, `.btn` / `.btn-sm` /
`.btn-primary`, `.plugin-hero` (+ 3 `.plugin-hero-badge`s), `.plugin-form-grid` /
`.plugin-form-grid-3`, `.plugin-param-group`, `.plugin-action-bar`,
`.plugin-progress-wrap` + `.plugin-progress-bar`, `.plugin-log-area`, `.spinner`.
Scope your own CSS under one plugin-specific class on the root `<div>`. No custom
button/modal styles, no `position: fixed`, must work in dark mode.

## Packaging (this template's shape)

One dist, one plugin. In `pyproject.toml`: base `dependencies` stay at the SDK floor only
(`3lc-compute-plugin-sdk>=0.1.0,<0.2.0`); the plugin's real deps go in its extra under
`[project.optional-dependencies]` (that's what lands in the provisioned venv); the entry
point under `[project.entry-points."tlc_compute.plugins"]` names the import package. If the
plugin uses `tlc_plugin_sdk.shared.*` data-plane helpers, depend on
`3lc-compute-plugin-sdk[shared]` **and** add `3lc[pandas]>=3.0.0,<4.0.0` with the
`3lc-releases` index source (already stubbed in the template's `pyproject.toml` comments).

`catalog.json` is the one-URL install listing: `source` is a PEP 508 git ref —
`<dist>[<extra>] @ git+https://github.com/<you>/<repo>.git@main` — and the embedded
`manifest` is a raw copy of `plugin.toml` so the Hub can render a card without downloading.

## Common mistakes

- Metadata on the class or a `register()` call — the manifest is the only metadata source.
- Bare `fetch()` in the UI instead of `PLUGIN_API.authFetch()`.
- Hardcoded colors / broken dark mode.
- Hand-rolled job queue, job store, cancel route, or `get_active_jobs` — all host-owned.
- `async def run_job` — it runs synchronously on a worker thread; poll `ctx.cancelled`.
- Plugin-specific fields in `ctx.progress`/`ctx.metric` — use `ctx.emit` for those.
- Opening a raw SocketIO connection server-side — emit through `ctx` only.
- Writing files inside the package at runtime — use `ctx.state_dir`.
- Plugin deps in base `dependencies` instead of the extra.
- A committed relative `path=` source in `[tool.uv.sources]` — breaks remote installs of
  the catalog `source`; local SDK overrides stay uncommitted.

## Dev loop

```bash
3lc-compute --plugin-dir /path/to/repo/src        # discover + provision + serve
curl http://localhost:5020/api/plugins/manifest/<id>
curl "http://localhost:5020/api/plugins/<id>/compute?x=1"
# hot reload after edits (re-provisions when deps changed):
curl -X POST http://localhost:5020/api/admin/plugins/dirs/reload \
  -H 'Content-Type: application/json' -d '{"directory": "/path/to/repo/src"}'
```
