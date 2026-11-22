# Building a plugin from this template

This repo is a template for a 3LC compute service plugin. Turn it into a working plugin with
the steps in [`.claude/skills/create-plugin/SKILL.md`](.claude/skills/create-plugin/SKILL.md);
the condensed contract is in [`reference.md`](.claude/skills/create-plugin/reference.md) beside
it, and the full one in the
[plugin author guide](https://3lc-ai.github.io/3lc-compute-plugin-sdk/plugin-guide.html).

## Rules for the plugin page (`ui.html`)

The Hub mounts the page into its own page and hands it `window.PLUGIN_API`:

- Talk to the host only through `window.PLUGIN_API`. Use `PLUGIN_API.authFetch` with
  `PLUGIN_API.getConfig('compute_service_url')` for the plugin's own routes; a bare `fetch`
  carries no sign-in.
- Move the Hub with `PLUGIN_API.navigate('/path')`.
- Track jobs with `window.PluginJobs`, which the plugin's worker injects into the page.
- Scope queries and CSS under the page's root class; the Hub's page is shared.
- Style with the house CSS variables and classes; never hardcode colors, so light and dark
  themes both work.
