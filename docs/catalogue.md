# Catalogue and roadmap

`catalogue/taxonomy.json` has 20 areas, 200 workflow seeds, 10 capability types and
a planning allocation of 1,000 environments per area. The goal is 20,000; the repo
does not yet contain 20,000 reviewed specifications or implementations.

`catalogue/tasks.json` contains actionable starter specs. Published GitHub issues
are the unit of claiming. New specs must differ in reasoning, tools, constraints
or verifier; changing names, dates or paraphrases normally creates data variants.

## Infrastructure backlog

1. Tested OpenEnv adapter and multi-turn state.
2. Independent adversarial reviewer agent with bounded retries.
3. Trusted evidence ingestion and reproducible badge promotion.
4. Disposable compute-worker protocol and job selection.
5. Separate trusted merger that never executes contributor code.
6. Workflow discovery/deduplication toward 2,000 workflows and 20,000 environments.

Claims and CI work before these exist. Do not advertise automatic merging,
distributed scheduling or training-validated badges until verified end to end.
