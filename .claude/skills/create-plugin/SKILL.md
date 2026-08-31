---
name: create-plugin
description: Create a 3LC compute-service plugin from this template repo. Turns the template skeleton into a working plugin from a one-line description — package rename, manifest, behavior, UI, catalog. Use when the user asks to create or scaffold a plugin, e.g. "/create-plugin a plugin that shows class balance for a table".
argument-hint: <what the plugin should do>
---

# Create a 3LC compute-service plugin

Transform this template repo **in place** into the plugin described by the user's prompt.
Nothing in the template is scaffolding to delete — every file is something you rename or
edit. Read `reference.md` (next to this file) before writing any plugin code: it is the
condensed plugin contract (manifest, `ComputePlugin`, `JobContext`, `PLUGIN_API`, UI rules,
common mistakes).

Canonical public docs, when the condensed reference isn't enough:

- Author guide: https://3lc-ai.github.io/3lc-compute-plugin-sdk/plugin-guide.html
- API reference: https://3lc-ai.github.io/3lc-compute-plugin-sdk/api.html
- Runnable example (full contract tour): https://github.com/3lc-ai/3lc-compute-plugin-example

## Step 0 — Check state and derive identity

First check that `src/tlc_plugin_template/` still exists. If it doesn't (the repo was
already transformed), stop and ask the user whether they want to modify the existing plugin
instead — this template hosts exactly one plugin per repo.

From the user's prompt, derive:

| Thing | Rule | Example |
|---|---|---|
| plugin `id` | short kebab-case slug (used in URLs and the SocketIO namespace) | `class-balance` |
| package | `tlc_plugin_<id with underscores>` (valid Python identifier) | `tlc_plugin_class_balance` |
| class | `<PascalCase>Plugin` | `ClassBalancePlugin` |
| dist name | `3lc-compute-plugin-<id>` | `3lc-compute-plugin-class-balance` |
| extra | same as `id` | `class-balance` |
| `name` | short display name | `Class Balance` |
| `description` | one sentence, user-facing | |
| `icon` | one fitting emoji | `⚖️` |

Also decide, from the prompt, which contract surfaces the plugin needs:

- **`compute(params)` only** — quick synchronous request/response (analysis, lookups). Default.
- **`run_job(ctx)`** — anything long-running (training, inference, imports, multi-step work
  with progress). Set `requires_gpu = true` in the manifest only if it genuinely needs a GPU.
- **`get_route_handlers()`** — POST bodies, multiple endpoints, config CRUD, file uploads.
- **deps** — whatever the plugin imports beyond the SDK goes in the plugin's extra in
  `pyproject.toml`, never in base `dependencies`.

Treat all of the above as **proposals, not decisions** — one prompt rarely nails
everything.

## Step 0.5 — Interview the author

Before touching any file, run **one** focused round of questions (use the AskUserQuestion
tool if available, otherwise ask in plain text). Ask at most 4 questions, each offering
your recommended answer first, marked as such. Skip anything the prompt already answers —
only ask what is genuinely open. Pick from these, in priority order:

1. **Input** — what does the plugin act on: one table, several tables, a run, or nothing
   (a standalone tool)? This drives `compatible_with` and whether it's a `sidebar` item or
   an `action` button on resource pages.
2. **Output** — display-only analysis, or does it produce something (a new table, a run,
   a downloadable file)? Producing something usually means `run_job` + `ctx.result(...)`.
3. **Execution shape** — instant response, or long-running work that needs a progress bar
   and cancel (and does it need a GPU)?
4. **Parameters** — which knobs should the UI expose, and should settings be persistent
   across sessions (config CRUD routes)?
5. **Dependencies** — does the author have specific libraries in mind (torch, pandas,
   OpenCV, …)?

Naming (id / display name / icon) is yours to decide — state your choice rather than
asking, unless the author's prompt suggests they care.

After the answers, restate the final plan in one short paragraph (identity, surfaces,
UI placement, deps) and proceed. Don't run a second round unless an answer contradicts
the original prompt — in that case resolve just that contradiction.

## Step 1 — The renames

Do these mechanically, keeping every existing comment intact (edit values, not the
surrounding documentation — the comments are part of the template's teaching surface).

1. `git mv src/tlc_plugin_template src/<package>`
2. **`src/<package>/plugin.toml`** — set `id`, `name`, `description`, `icon`,
   `runtime.entrypoint = "<package>:<Class>"`, `runtime.provision_extra = "<extra>"`.
   Choose `[ui]` `display_mode` / `section` / `compatible_with` to fit the plugin
   (see reference.md → Manifest). Add `requires_gpu = true` under `[runtime]` if needed.
3. **`pyproject.toml`** — project `name` = dist name; description; rename the extra under
   `[project.optional-dependencies]` (and put the plugin's deps in it); the entry point under
   `[project.entry-points."tlc_compute.plugins"]` (`<extra> = "<package>"`); the package path
   under `[tool.hatch.build.targets.wheel]`.
4. **`catalog.json`** — `id`, `source` (`<dist>[<extra>] @ git+<repo-url>@main` — get the
   repo URL from `git remote get-url origin`; if there is no remote, leave the template URL
   and flag it in your final report), and the `manifest` object mirrors `plugin.toml`.
5. **`README.md`** — retitle for the new plugin; keep the run/dev-loop/catalog sections,
   updated with the new names.

## Step 2 — Implement the behavior

Rewrite `src/<package>/__init__.py`: rename the class, rewrite the module docstring for
this plugin, and implement the surfaces chosen in step 0. Follow the patterns in
reference.md exactly — in particular:

- Metadata lives only in `plugin.toml`; the class carries behavior only (no `register()`,
  no metadata attributes).
- `run_job(ctx)` is synchronous, talks only to `ctx`, and polls `ctx.cancelled` at
  checkpoints. Never hand-roll a queue, job store, or cancel route — the host owns those.
- Custom routes are bare relative `@get`/`@post` Litestar handlers in a `routes.py`
  (`sync_to_thread=True` for blocking work), returned from `get_route_handlers()`.
- Data access goes through the `tlc` SDK server-side; the plugin SDK brings `tlc` with it, so
  `tlc_plugin_sdk.shared.*` and `import tlc` work with the base pin alone.

## Step 3 — The UI fragment

Rewrite `src/<package>/ui.html` as one self-contained fragment (scoped `<style>` + markup +
one IIFE `<script>`), following reference.md → UI:

- Reach the host **only** through `window.PLUGIN_API` (`authFetch`, never bare `fetch`).
- Style with the house CSS variables and shared classes (`.plugin-page-narrow`, `.card`,
  `.btn btn-primary`, `.plugin-hero`, …) — no hardcoded colors, works in dark mode.
- If the plugin has jobs: start/track them with `window.PluginJobs` (inject
  `job_tracker_script()` via `inject_scripts()` in `get_ui_fragment()` — see reference.md).
- Update the endpoint URLs and CSS class prefix from `template-` to the new id.

## Step 4 — Verify

```bash
uvx --from 'ruff>=0.15,<0.16' ruff format .
uvx --from 'ruff>=0.15,<0.16' ruff check .
uv sync --extra <extra>          # resolves the venv; proves deps + extra wiring
uv run python -c "from <package> import <Class>; p = <Class>(); print(type(p.get_ui_fragment()))"
```

Also confirm `plugin.toml` parses and agrees with the code:

```bash
uv run python -c "
import tomllib, pathlib
m = tomllib.loads(pathlib.Path('src/<package>/plugin.toml').read_text())
assert m['runtime']['entrypoint'] == '<package>:<Class>', m['runtime']['entrypoint']
assert m['runtime']['provision_extra'] == '<extra>'
print(m['id'], m['version'])
"
```

Fix everything these surface. Do not commit unless asked.

## Step 5 — Report

Tell the user: the identity you chose (id / package / dist / extra), which contract
surfaces you implemented and why, and how to run it against a local compute service:

```bash
3lc-compute --plugin-dir "$(pwd)/src"
# then iterate with hot reload:
curl -X POST http://localhost:5020/api/admin/plugins/dirs/reload \
  -H 'Content-Type: application/json' -d "{\"directory\": \"$(pwd)/src\"}"
```

Flag anything left for them (e.g. catalog `source` URL if no git remote, GPU testing).
