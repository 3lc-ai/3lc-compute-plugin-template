# hub-plugin_template

Minimal boilerplate for a 3LC compute-service plugin hosted in its own
repository. Use this as a starting point when building a plugin that should
ship and version independently of the `3lc-insights` repo.

## Layout

```
hub-plugin_template/
├── README.md
├── LICENSE
└── plugins/                       <- "plugin root" you point compute-service at
    └── template_plugin/           <- the plugin package (one of possibly many)
        ├── __init__.py            <- defines & registers the ComputePlugin
        └── ui.html                <- self-contained UI fragment
```

The `plugins/` directory is the **plugin root**. Every immediate subdirectory
that contains an `__init__.py` is imported as a top-level Python package and
must call `register(MyPlugin())` at import time. You can host multiple plugins
in the same repo — just add more sibling directories under `plugins/`.

The package directory name (`template_plugin/`) becomes a top-level Python
module name when loaded, so it must:

* be a valid Python identifier (snake_case, no hyphens),
* not collide with any other top-level package name (stdlib, installed
  dependencies, or other external plugins).

The plugin's public `id` (e.g. `"template-plugin"`) is independent of the
directory name — it can use hyphens because it is only used in URLs and the
plugin manifest.

## Loading the plugin

The 3LC compute service can pick this directory up three ways:

### 1. CLI flag (preferred for development)

```bash
3lc-compute --plugin-dir /path/to/hub-plugin_template/plugins
```

The flag is repeatable; pass it multiple times to load several plugin roots.

### 2. Environment variable

```bash
export TLC_COMPUTE_EXTERNAL_PLUGIN_DIRS=/path/to/hub-plugin_template/plugins
3lc-compute
```

Multiple paths are joined with `os.pathsep` (`:` on macOS/Linux, `;` on
Windows).

### 3. Runtime API

```bash
curl -X POST http://localhost:5020/api/admin/plugins/dirs \
  -H 'Content-Type: application/json' \
  -d '{"directory": "/path/to/hub-plugin_template/plugins"}'
```

The compute service responds with the list of plugins it loaded:

```json
{
  "directory": "/path/to/hub-plugin_template/plugins",
  "already_registered": false,
  "loaded": ["template-plugin"],
  "skipped": []
}
```

## Verifying it works

Once loaded, the plugin is exposed on the same endpoints as built-in plugins:

```bash
curl http://localhost:5020/api/plugins/template-plugin/manifest
curl http://localhost:5020/api/plugins/template-plugin/compute?url=hello
curl http://localhost:5020/api/plugins/template-plugin/ui
```

## Iteration loop

Edit `plugins/template_plugin/__init__.py`, then reload without restarting the
service:

```bash
# Reload one plugin by id
curl -X POST http://localhost:5020/api/admin/plugins/template-plugin/reload

# Or reload every plugin in this directory at once
curl -X POST http://localhost:5020/api/admin/plugins/dirs/reload \
  -H 'Content-Type: application/json' \
  -d '{"directory": "/path/to/hub-plugin_template/plugins"}'
```

Reload tears down the plugin's runtime, purges its modules from
`sys.modules`, re-imports the package (picking up your edits), and calls
`initialise_runtime()` on the new instance. Generic routes
(`/api/plugins/<id>/compute`, `/ui`, `/manifest`) keep working across the
reload because they dispatch through the registry at request time.

## Detaching

To unload all plugins from this directory and remove it from `sys.path`:

```bash
curl -X DELETE \
  "http://localhost:5020/api/admin/plugins/dirs?directory=/path/to/hub-plugin_template/plugins"
```

Add `&force=true` to override the running-jobs guard.

## Limitations

* Custom Litestar route handlers (returned by `get_route_handlers()`) are
  mounted at compute-service startup. Plugins added at runtime can use the
  generic `/api/plugins/<id>/compute` and `/api/plugins/<id>/ui` endpoints
  out of the box, but custom controllers require a service restart.
* External plugin packages must not collide on top-level Python module names
  with each other or with installed dependencies. The loader skips
  collisions with a logged warning.
