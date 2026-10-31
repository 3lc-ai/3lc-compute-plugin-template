# 3lc-compute-plugin-template

The starting point for writing a [3LC compute service](https://github.com/3lc-ai) plugin.
This is a **GitHub template repository**: click **Use this template** (top right) and you get
a fresh repo — your name, your history — containing the smallest viable plugin, ready to
rename and grow. Nothing in it is scaffolding you delete; everything is something you edit.

Want to see what a plugin can *do* first? The example plugin,
[**Mission Control**](https://github.com/3lc-ai/3lc-compute-plugin-example), is a runnable
tour of the whole contract — jobs with live progress, a clean failure and abort, custom REST
routes, the typed UI bridge, the shared data-source picker, lifecycle hooks, and a test suite
that runs it all without a compute service. Crib from it as you grow. The full contract
reference lives in the
[**plugin author guide**](https://3lc-ai.github.io/3lc-compute-plugin-sdk/plugin-guide.html)
(`3lc-compute-plugin-sdk`).

The template pins the SDK's **0.6 line**, the contract the Hub and Compute Service **1.2**
implement (`min_service_version = "1.2.0"` in the manifest).

## What's in the box

```
├── pyproject.toml            # one dist; your plugin's extra + entry point
├── catalog.json              # your shop listing — point it at your repo (see below)
├── jsconfig.json             # types for window.PLUGIN_API in ui.html
├── tests/test_plugin.py      # the plugin in-process (SDK harness) + the UI lint
├── .github/workflows/ci.yml  # ruff lint + format, pytest
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

Using [Claude Code](https://claude.com/claude-code)? Run **`/create-plugin <what it should
do>`** in your generated repo — a bundled skill ([`.claude/skills/create-plugin`](.claude/skills/create-plugin/SKILL.md))
that interviews you about the pieces your one-liner left open (inputs, outputs, jobs, GPU),
then does the renames below and implements a first working version, using only the public
[plugin guide](https://3lc-ai.github.io/3lc-compute-plugin-sdk/plugin-guide.html).

Doing it by hand: after **Use this template**, five renames:

1. **The package.** `src/tlc_plugin_template` → `src/tlc_plugin_<yours>` (package names must
   be valid Python identifiers; the public `id` in the manifest is independent and may use
   hyphens).
2. **The manifest.** In `plugin.toml`, set `id`, `name`, `description`, and the
   `runtime.entrypoint` / `provision_extra` to match. The example's
   [`plugin.toml`](https://github.com/3lc-ai/3lc-compute-plugin-example/blob/main/src/tlc_plugin_example/plugin.toml)
   documents every optional field: GPU and remote-node runs, the run-body keys that carry
   data, tokens, auth-exempt assets.
3. **The dist.** In [`pyproject.toml`](pyproject.toml): project `name`, your extra under
   `[project.optional-dependencies]` (your dependencies go there), the entry point, and the
   package path under `[tool.hatch.build.targets.wheel]`.
4. **The catalog.** In [`catalog.json`](catalog.json): `id`, `latest`, the manifest copy, and
   the `source` — point it at *your* repo (see below).
5. **The tests.** In [`tests/test_plugin.py`](tests/test_plugin.py), the package folder and
   the root class name your fragment uses.

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
Hub (on a keyless dev service; one under an API key wants an `Authorization: Bearer …` header):

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
# Or retire just this plugin's worker; the next request cold-starts on the code on disk:
curl -X POST http://localhost:5020/api/admin/plugins/template/worker/stop
```

Test and lint like CI does — the tests need no compute service, they run the plugin
in-process through the SDK's harness:

```bash
uv sync --extra template                # the venv the host would provision, plus pytest
uv run pytest -q                        # harness + the UI lint
uv run python -m tlc_plugin_sdk.lint src/   # the fragment against the Hub's styling rules
uvx --from 'ruff>=0.15,<0.16' ruff check .
uvx --from 'ruff>=0.15,<0.16' ruff format .
```

To develop against a sibling SDK checkout, override its source **uncommitted**:

```toml
# pyproject.toml [tool.uv.sources]  (local dev only — do not commit)
3lc-compute-plugin-sdk = { path = "../3lc-compute-plugin-sdk", editable = true }
```

### Editor autocomplete for `ui.html`

Your fragment talks to the host through `window.PLUGIN_API` / `window.PluginJobs`, and both
are **typed**: the declaration ships inside the pip-installed SDK wheel, and the repo-root
[`jsconfig.json`](jsconfig.json) points TypeScript at it. Run `uv sync` once (creates
`.venv/`) and VS Code autocompletes the whole bridge inside `ui.html` — no node, no build
step.

## The catalog: one-click install from GitHub

[`catalog.json`](catalog.json) is your plugin's shop listing — a static JSON file with
versions, a `latest` tag naming the release to offer, a raw copy of the manifest (so the Hub
can render a card and check compatibility **without downloading anything**), and an install
source. The committed one points at this template repo; after **Use this template**, edit the
`source` to point at your repo:

```
your-dist-name[your-extra] @ git+https://github.com/you/your-repo.git@main
```

No wheel publishing required — the `[extra]` selects your plugin and the venv materializes
straight from the git source. Hand out one URL and anyone can install it.

Which catalogs a compute service reads is **configuration**, because a catalog's entries are
trusted install sources (the default install policy, `catalog-only`, installs nothing a
catalog did not list). The person running the service names yours in its environment:

```bash
TLC_COMPUTE_PLUGIN_CATALOG_URLS=https://raw.githubusercontent.com/you/your-repo/main/catalog.json
```

…or as `compute-service.plugins.catalog-urls` in the service's configuration file (or a
Config Service scope, for a deployment). The Hub's Plugins page lists the catalogs in force
under **Plugin sources**; your plugin shows up as a card there, **Add** registers it, and the
first visit materializes its venv.

## License

Apache-2.0 — see [LICENSE](LICENSE). Repos generated from this template are yours to
license as you wish.
