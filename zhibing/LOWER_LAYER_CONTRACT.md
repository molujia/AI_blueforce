# Zhibing Lower-Layer Contract

This file is now the short index for the lower-layer boundary. The handoff document for lower simulation engineers is:

- `zhibing/docs/lower_simulation_interface.md`

Machine-readable ownership metadata is in:

- `zhibing/interfaces/interface_ownership.py`
- `zhibing/interfaces/simulation_contract.schema.json`

Summary:

- Zhibing owns the LLM decision layer, Scene Query Tool facades, GraphRAG knowledge tools, task planning, deterministic SQF compilation, and 2D battlefield projection.
- The shared protocol covers `TaskSubmitRequest`, `StatusQueryRequest`, `TaskStatusResponse`, and socket envelopes.
- The lower simulation system owns VBS runtime integration, BT runtime, HTTP/socket return wrappers, task execution, scene data endpoints, and local emergency handling such as sudden contact avoidance.
- Protocol coordinates must always carry an explicit `frame`. Bare coordinate arrays are only allowed inside SQF emitted by the deterministic compiler.
