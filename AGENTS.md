# Building a plugin from this template

This repo is a template for a 3LC compute service plugin. Turn it into a working plugin with
the steps in [`.claude/skills/create-plugin/SKILL.md`](.claude/skills/create-plugin/SKILL.md);
the condensed contract is in [`reference.md`](.claude/skills/create-plugin/reference.md) beside
it, and the full one in the
[plugin author guide](https://3lc-ai.github.io/3lc-compute-plugin-sdk/plugin-guide.html).

## Rules for the plugin page (`ui.html`)

The Hub shows the page in a sandboxed frame served by the compute service, not inside the Hub's
own page. Code that reaches past the frame fails at run time, so:

- Talk to the Hub only through `window.PLUGIN_API`. Use `PLUGIN_API.compute.request` for the
  plugin's own routes; a bare `fetch` to the compute service carries no sign-in and is refused.
- Move the Hub with `PLUGIN_API.nav.go('/path')`, never `window.location.href`.
- Never use `TlcApi`, `TlcAuth`, `TlcData`, `window.top` or `window.parent`: they do not exist
  in the frame or belong to another origin.
- Plain `fetch` to other sites' public APIs, CDN `<script>` tags, `localStorage`, downloads and
  `window.open` work. Keep secrets out of `localStorage`: other plugins on the same compute
  service share it.
- To call another plugin's routes, keep the page's own query in the Hub's address, or show the
  person's name, declare `calls:<id>`, `history` or `identity:name` under `[ui] capabilities`
  in `plugin.toml`.
- Style with the house CSS variables and classes; the frame loads the Hub's stylesheets and
  follows its light and dark theme.

A refused call rejects with an error naming the route or member; check the browser console.

## SDK 0.6.2 frame runtime

Use the SDK [browser runtime guide](https://3lc-ai.github.io/3lc-compute-plugin-sdk/browser-runtime.html)
and [agent guide](https://3lc-ai.github.io/3lc-compute-plugin-sdk/agent-guide.html).
These pages publish with the SDK release; before release read the matching SDK branch sources.
The host must serve the new runtime; upgrading only the plugin venv is insufficient.
`PLUGIN_API.jobs` is installed by the runtime: new plugins do not inject a job tracker.
Use namespaced helpers and register local cleanup with `lifecycle.onDispose`.
Never cancel a running job on navigation, renewal failure, disconnect or disposal.
Test explicit cancellation separately from viewer cleanup and recovery.
