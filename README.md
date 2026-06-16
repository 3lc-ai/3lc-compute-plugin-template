# hub-plugin_template

Boilerplate for 3LC compute-service plugins hosted in their own repository — so a
plugin can ship and version independently of `3lc-insights`.

It contains **two example plugins**, one per isolation tier:

| | [`template_host`](plugins/template_host) | [`template_venv`](plugins/template_venv) |
|---|---|---|
| Runs | in-process, in the compute-service | out-of-process, in its own venv |
| Dependencies | must be a subset of the service's | its own (may conflict with the service) |
| Files | `plugin.toml` + `__init__.py` + `ui.html` | `plugin.toml` + `pyproject.toml` + `plugin.py` + `ui.html` |
| Pick it when | your plugin is lightweight | you need your own / heavy / conflicting deps |

**The only structural difference is `runtime.isolation` in the manifest** (and the
`venv` tier additionally declares its deps in a `pyproject.toml`). Everything else —
how metadata is declared, how the plugin is discovered, how it's served — is identical.

## How a plugin is described: the manifest

Every plugin has a `plugin.toml` (or a `[tool.tlc-compute]` table in a
`pyproject.toml`). It is the **single source of metadata**, and it is read **without
importing the plugin** — so discovery can list, gate and route a plugin even when its
code can't be imported (it shows greyed-out with a reason instead of vanishing).

```toml
id = "template-host"            # public id, used in URLs (hyphens ok)
name = "Template (host)"
version = "0.1.0"
min_service_version = "0.2.0"

[ui]
display_mode = "sidebar"        # sidebar | action | hidden
section = "Examples"
compatible_with = ["table"]

[runtime]
isolation = "host"              # host | venv  ← the tier switch
entrypoint = "template_host:TemplateHostPlugin"   # module:Class
```

The service imports the `entrypoint` and instantiates the class. There is **no
metadata on the Python class and no `register()` call** — the class carries only
behavior (`get_ui_fragment`, `compute`, and — for jobs — `run_job(ctx)`).

## Loading the plugin

Point the compute-service at the **`plugins/` root** (it loads every plugin under it):

```bash
# 1. CLI flag (repeatable)
3lc-compute --plugin-dir /path/to/hub-plugin_template/plugins

# 2. Environment variable (os.pathsep-joined)
export TLC_COMPUTE_EXTERNAL_PLUGIN_DIRS=/path/to/hub-plugin_template/plugins

# 3. Runtime API
curl -X POST http://localhost:5020/api/admin/plugins/dirs \
  -H 'Content-Type: application/json' \
  -d '{"directory": "/path/to/hub-plugin_template/plugins"}'
```

## Verifying it works

Both plugins expose the same generic endpoints:

```bash
curl http://localhost:5020/api/plugins/template-host/manifest
curl http://localhost:5020/api/plugins/template-host/compute?url=hello
curl http://localhost:5020/api/plugins/template-host/ui

curl http://localhost:5020/api/plugins/template-venv/compute?url=hello
# Run a streaming job (NDJSON: progress / metric / log, then a terminal done):
curl -N -X POST http://localhost:5020/api/plugins/template-venv/run \
  -H 'Content-Type: application/json' -d '{"steps": 5}'
```

## Running the venv example

By default the venv worker runs on the **host interpreter**, so the stdlib-only
example above works out of the box. To run it in a real, isolated venv with its own
dependencies (the actual point of this tier):

```bash
cd plugins/template_venv
uv venv .venv
uv pip install --python .venv/bin/python 3lc-compute   # + your own deps from pyproject.toml
```

The service resolves the worker interpreter in this order: the
`TLC_COMPUTE_PLUGIN_VENV_TEMPLATE_VENV` env var → `runtime.venv_python` in the
manifest → a `.venv/` next to the plugin → the host interpreter. So once the `.venv`
above exists it is used automatically. (Fully automatic provisioning from
`pyproject.toml` is in progress.)

## Iteration

```bash
# Reload one plugin by id (host plugins; picks up code edits)
curl -X POST http://localhost:5020/api/admin/plugins/template-host/reload

# Reload everything in this directory
curl -X POST http://localhost:5020/api/admin/plugins/dirs/reload \
  -H 'Content-Type: application/json' \
  -d '{"directory": "/path/to/hub-plugin_template/plugins"}'
```

## Notes

* Package/dir names must be valid Python identifiers and must not collide with other
  top-level modules. The public `id` (in the manifest) is independent and may use hyphens.
* This template targets the manifest-first plugin contract (compute-service ≥ 0.2). On
  older services the old class-attribute + `register()` form is still accepted as a
  fallback.
