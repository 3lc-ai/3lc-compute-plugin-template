# 3LC compute-plugin contract — condensed reference

Condensed from the canonical public docs; when in doubt, they win:

- Author guide: https://3lc-ai.github.io/3lc-compute-plugin-sdk/plugin-guide.html
- API reference: https://3lc-ai.github.io/3lc-compute-plugin-sdk/api.html
- SDK repo (incl. agent guidance in its CLAUDE.md): https://github.com/3lc-ai/3lc-compute-plugin-sdk
- Example plugin, "Mission Control" — a runnable tour of every surface below, with tests:
  https://github.com/3lc-ai/3lc-compute-plugin-example

This template pins the SDK's **0.6 line**, the contract the Hub and Compute Service **1.2**
implement.

## The model

Each plugin is a self-contained package: Python behavior + one HTML fragment + optional
REST routes + optional long-running jobs. The host (the 3LC compute service, port 5020)
reads the plugin's `plugin.toml` **without importing it**, provisions the plugin its own
uv-managed venv (`uv sync --extra <provision_extra>`), runs it out-of-process behind a
reverse proxy, and serves it at `/api/plugins/{id}/…`. The Hub frontend has zero knowledge
of any specific plugin — it renders sidebar entries and the generic job panel purely from
manifests and the generic job schema. A run may happen on the compute host's own workers
or, when the manifest allows it, on a remote node the Hub manages.

Plugins must **not** access the 3LC Object Service directly (it may be unreachable from the
plugin's environment) — all data access goes through the `tlc` SDK server-side.

## Manifest (`plugin.toml`)

The single source of the plugin's metadata; the class carries none.

```toml
id = "my-plugin"                    # URL-safe slug; also the SocketIO namespace "/<id>"
name = "My Plugin"
description = "One user-facing sentence."
version = "0.1.0"                   # SemVer; bump on every release
min_service_version = "1.2.0"       # Compute 1.2 implements the SDK 0.6 line the plugin pins
# min_frontend_version = "1.2.0"    # only when ui.html needs a Hub 1.2 feature (<tlc-table-field>, TlcPicker, showResult)
icon = "🔍"                         # fallback emoji
# icon_svg = '<svg …>'              # inline 16x16 SVG
# kind = "compute"                  # default; "infrastructure" = a node provider (InfrastructurePlugin)

[ui]
display_mode = "sidebar"            # sidebar | action | hidden
section = "Tools"                   # sidebar grouping label
compatible_with = ["table"]         # resource types this acts on: "table" | "run"
# input_types / output_types / min_input_count / priority / quick_action also available

[runtime]
entrypoint = "tlc_plugin_my_plugin:MyPlugin"   # "package.module:ClassName"
provision_extra = "my-plugin"       # REQUIRED: the extra in pyproject.toml the host installs
# requires_gpu = true               # routes jobs through the shared GPU queue (one at a time)
# remote_capable = true             # a run may target a remote node although requires_gpu is false
# data_inputs = ["folder", "source.table_url"]   # dotted run-body keys naming data the run READS
# data_outputs = ["output_path"]                 # … and places it WRITES (never the project root)
# node_routes = ["/preview"]        # custom routes that run on the node for a node run
# credentials = [{ service = "huggingface", required = false, value_hint = "…" }]  # tokens a job may be lent
# credential_routes = ["/hf/search"]             # custom routes that receive the token
# auth_exempt_paths = ["/api/plugins/my-plugin/logo.png"]   # full paths under the plugin's own prefix
```

`display_mode`: `sidebar` = a nav item under `section`; `action` = a button on resource
pages (tables/runs), receiving the selected resources; `hidden` = API-only, no UI entry.
There is no `isolation` to set: every plugin runs out-of-process in its own venv (older
manifests still say `isolation = "venv"`; nothing reads it).

**Data the run touches.** The host plans the values under `data_inputs` / `data_outputs` for
the run target before the run (a folder on the host is not on a node; a node may not read a
bucket), asks the person once in the Hub, and may rewrite an input to a staged copy. Leave the
project root out: the host stamps it as `ctx.project_root_url`.

## The plugin class

Three bases in `tlc_plugin_sdk`: `HubPlugin` (fragment, optional `compute`, routes, shutdown)
for a plugin with no jobs; `ComputePlugin(HubPlugin)` adds `run_job` / `initialise_runtime`;
`InfrastructurePlugin(HubPlugin)` is the typed node-provider contract (not covered here). One
abstract method, `get_ui_fragment()`; everything else is a safe default you override only when
needed. There is **no** `register()`, and no `get_active_jobs`/`cancel_job` — the host owns
job listing and cancellation.

```python
from tlc_plugin_sdk import ComputePlugin

class MyPlugin(ComputePlugin):
    id: str  # stamped onto the instance by the host from the manifest

    def get_ui_fragment(self) -> str: ...          # required — GET /api/plugins/{id}/ui
    def compute(self, params) -> dict: ...          # optional — GET /api/plugins/{id}/compute (default: an error dict)
    def run_job(self, ctx) -> None: ...             # optional — long-running work
    def get_route_handlers(self) -> list: ...       # optional — custom REST routes
    def initialise_runtime(self) -> None: ...       # optional — one-time setup (models, stores)
    def shutdown_runtime(self) -> None: ...         # optional — teardown; safe if never initialised
```

`compute(params)` receives the query params of `GET /api/plugins/{id}/compute` and returns
a JSON-able dict. Error convention: bad input → `{"error": "…"}`; an outcome →
`{"success": true/false, "message": "…", "details": {…}}` (the shape `PLUGIN_API.showResult`
draws); not found in routes → a 404 `Response` or `HTTPException(404)`.

## Long-running jobs — `run_job(ctx)`

The UI starts a job with `POST /api/plugins/{id}/run` (JSON body = params; answer
`{job_id, status, namespace}`) and the host calls `run_job(ctx)` on a worker thread. The host
owns the queue, the GPU/CPU slot, progress fan-out, the generic Queue & Progress panel, and
cancellation — the plugin only runs the job and talks to `ctx` (`JobContext`):

| Member | Purpose |
|---|---|
| `ctx.job_id` | unique id for this job |
| `ctx.params` | parsed request body / query, without host-owned keys and secrets |
| `ctx.cancelled` | `True` once cancel requested — poll at checkpoints, return cleanly |
| `ctx.state_dir` | writable per-plugin scratch dir (never write inside the package) |
| `ctx.project_root_url` | the project root the job writes to, stamped by the host: pass it as `root_url` when creating tables or runs |
| `ctx.identity` | who the job runs for (`user_id`, `org_id`, `project_id`; `None` on a keyless host) — attribution only |
| `ctx.get_credential(service)` | a `SecretToken` for a declared service, or `None`; pass `.secret` to your library, never into `os.environ` |
| `ctx.progress(*, percent, label="", timing=None)` | generic progress bar; `percent=-1` = indeterminate |
| `ctx.metric(label, value)` | scalar metric card on the generic panel |
| `ctx.log(message)` | a log line for the job |
| `ctx.result(url)` | the canonical "open result" link — a run or a table URL (last write wins) |
| `ctx.fail(message)` | fail with a clean, user-facing sentence (raises `JobFailed`; no `TypeError:` prefix) |
| `ctx.emit(name, payload)` | plugin-private event for this plugin's own UI only |

Rules: `run_job` is a plain `def` (never `async`); raise, or `ctx.fail()`, to fail the job;
keep plugin-specific fields (epoch, loss, model name, …) out of `progress`/`metric` — those
feed the plugin-agnostic panel; use `ctx.emit` for anything richer, consumed only by your own
`ui.html`. The event name `job_update` is reserved. A cancel the loop ignores for 60 s costs
the worker process, so check `ctx.cancelled` inside long loops.

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

    @post("/analyze", status_code=200, sync_to_thread=True)   # sync_to_thread=True for blocking work
    def analyze(data: dict[str, Any]) -> dict[str, Any]:
        return {"success": True, "message": "done", "details": {}}

    return [get_status, analyze]
```

Return a **fresh** list each call. Don't add job routes (`/queue`, `/cancel/{id}`, a start
route) — the generic `POST /api/plugins/{id}/run`, `GET /api/plugins/jobs`, and
`POST /api/plugins/jobs/{job_id}/cancel` cover the job lifecycle. Custom routes carry only
genuinely plugin-specific surface (config CRUD, metadata lookups, uploads, …). For files and
folders the person picks, mount the SDK's `data_source_route_handlers()` beside yours.

## UI fragment (`ui.html`)

One self-contained `<style>` + markup + `<script>` block, mounted into the Hub page with no
iframe: it inherits the Hub's stylesheets and shares its namespace.

**The bridge.** Reach the host only through `window.PLUGIN_API` — never bare `fetch`.
It is typed: the repo-root `jsconfig.json` points the editor at `plugin-api.d.ts` inside
the installed SDK wheel (run `uv sync` once and hover works). Key surface:

```javascript
var API = window.PLUGIN_API;
var base = API.getConfig('compute_service_url');   // also: dashboard_url, object_service_url, deployment_name
API.context.resourceType;    // "table" | "run" | null (for action plugins)
API.context.resourceUrls;    // selected resource URLs
API.context.projectName;
API.authFetch(url, opts);    // fetch with auth header; rejects non-ok with parsed detail
API.showToast(msg, 'success'|'error'|'info');
if (API.showResult) API.showResult(el, {success, message, details});  // the Hub's result box (Hub 1.2+)
API.libs.io;                 // Socket.IO client — the ONLY libs member that is stable
```

**Jobs from the UI.** `window.PluginJobs` is added to every fragment by the worker's `/ui`
handler — nothing to inject:

```javascript
var jobId = null, cancelPressed = false;
PluginJobs.run('my-plugin', { table_url: url }, {
  onUpdate: function (job) { /* job.status, job.progress.percent/label, job.metrics[] */ },
  onDone:   function (job) { /* job.run_url */ },
  onError:  function (job) { /* job.error: the failure message (job.subtitle is the last label) */ },
}).then(function (resp) {              // keep the id from the START answer — the first job_update
  if (!resp || !resp.job_id) return;   // can be minutes away, and a Cancel needs the id now
  jobId = resp.job_id;
  if (cancelPressed) PluginJobs.cancel(jobId);
});
// plugin-private ctx.emit events, subscribed BEFORE run() so none is missed:
var off = PluginJobs.on('/my-plugin', 'telemetry', function (d) { /* … */ });
```

**Fields.** A table URL: `<tlc-table-field id="t" required>` (Hub 1.2; set
`min_frontend_version = "1.2.0"`) — read `.value`, listen to `input`/`change`. A file or
folder: the SDK's data-source picker — inject `data_source_ui_script()` with `inject_scripts()`
in `get_ui_fragment()`, render `_tlcDataSourceHtml(id, {placeholder, accept})`, bind
`_tlcBindDataSource(id, base, pluginId, {mode: 'file'|'folder', purpose: 'input'|'output'})`,
read `_tlcGetDataSourceValue(id)`. Saved setups: the preset bar, `preset_ui_script()` +
`_tlcPluginPresets({...})` over `PluginConfigStore` config routes (guide → "Presets").

**Styling.** Use the Hub's classes — `.btn btn-primary` / `.btn-sm` / `.btn-danger`,
`.form-group` / `.form-label` / `.form-control` / `.form-select` / `.form-help`, `.card`,
`.plugin-page` / `.plugin-page-narrow`, `.plugin-hero` (+ 3 `.plugin-hero-badge`s),
`.plugin-form-grid` / `-3`, `.plugin-param-group`, `.plugin-action-bar`,
`.plugin-progress-wrap` + `.plugin-progress-bar`, `.plugin-log-area`, `.spinner` — and the
theme tokens for colour: `var(--text)`, `var(--text-muted)`, `var(--bg)`, `var(--bg-card)`,
`var(--border)`, `var(--accent)`, `var(--error)`, `var(--code-bg)`. Scope every rule of your
own under one class named after the plugin id (`.<id>-…`) on the root `<div>`. No custom
button/modal styles, no inline `background`/`color`/`box-shadow`, no `!important`, no
`position: fixed`, must work in dark mode. `python -m tlc_plugin_sdk.lint src/` checks all of
this; the template's tests run it.

## Packaging (this template's shape)

One dist, one plugin. In `pyproject.toml`: base `dependencies` stay at the SDK floor only
(`3lc-compute-plugin-sdk>=0.6.1,<0.7.0`); the plugin's real deps go in its extra under
`[project.optional-dependencies]` (that's what lands in the provisioned venv); the entry
point under `[project.entry-points."tlc_compute.plugins"]` names the import package; pytest
sits in the `dev` dependency group. The SDK brings the `tlc` data plane (`3lc[pandas]`) and
the `tlc_plugin_sdk.shared.*` helpers — no separate `3lc` dep is needed. Everything resolves
from public PyPI, no custom indexes needed.

`catalog.json` is the one-URL install listing: `source` is a PEP 508 git ref —
`<dist>[<extra>] @ git+https://github.com/<you>/<repo>.git@main` — `latest` names the
release to offer, and the embedded `manifest` is a raw copy of `plugin.toml` so the Hub can
render a card without downloading. Which catalogs a host reads is configuration
(`TLC_COMPUTE_PLUGIN_CATALOG_URLS`, or `compute-service.plugins.catalog-urls` in its config
file); the default install policy installs only what a catalog lists.

## Testing (no compute service)

`tests/test_plugin.py`: `PluginHarness.from_manifest(<plugin dir>)` builds the same Litestar
app the worker serves and calls it in-process — `h.get("/compute", params=…)`,
`h.post("/analyze", json_body=…)`, `h.get("/ui")`; a `run_job` is driven with
`JobContext("job-1", params, tmp_path, sink=events.append, cancel_event=threading.Event())`
and assertions on the recorded `progress` / `metric` / `result` / `custom` events;
`lint_plugin(<plugin dir>)` must return no findings. `uv sync --extra <extra>` then
`uv run pytest -q`.

## Common mistakes

- Metadata on the class or a `register()` call — the manifest is the only metadata source.
- Bare `fetch()` in the UI instead of `PLUGIN_API.authFetch()`.
- Hardcoded colors, inline surface styles, custom button styles, unscoped CSS rules / broken dark mode.
- Hand-rolled job queue, job store, cancel route, or `get_active_jobs` — all host-owned.
- `async def run_job` — it runs synchronously on a worker thread; poll `ctx.cancelled`.
- Plugin-specific fields in `ctx.progress`/`ctx.metric` — use `ctx.emit` for those.
- Opening a raw SocketIO connection, server- or browser-side — `ctx.emit` and `PluginJobs.on`.
- Learning the job id from the first `job_update` instead of `run()`'s answer — Cancel then has nothing to cancel.
- Reading the failure from `job.subtitle` — it is `job.error`.
- Writing files inside the package at runtime — use `ctx.state_dir`.
- Inventing an output root — use `ctx.project_root_url`.
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
# or retire just this plugin's worker; the next request cold-starts on the code on disk:
curl -X POST http://localhost:5020/api/admin/plugins/<id>/worker/stop
```
