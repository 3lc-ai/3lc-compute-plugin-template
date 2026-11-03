# Working here with an agent

This repository is the starting point for a 3LC compute service plugin. Before changing it, read:

- The [plugin author guide](https://3lc-ai.github.io/3lc-compute-plugin-sdk/plugin-guide.html): the contract a
  plugin implements (manifest, `ComputePlugin`, jobs, routes, the UI bridge). This is the reference.
- <https://docs.3lc.ai/llms-full.txt>: 3LC's primers for agents, with the Hub primer (deployments, jobs, GPU nodes,
  Connections) that says where a plugin runs, and the Python primer for when the plugin reads or writes 3LC tables
  and runs with `tlc`. <https://docs.3lc.ai/llms.txt> is the index.

The example plugin, [Mission Control](https://github.com/3lc-ai/3lc-compute-plugin-example), is a runnable tour of
the contract; crib from it rather than from memory. The primers name concepts, not signatures: confirm symbols
against the installed SDK (`help(tlc_plugin_sdk.X)`).
