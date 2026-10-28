# Catalogue and roadmap

`catalogue/taxonomy.json` has 20 areas, 200 workflow seeds, 10 capability types and
a planning allocation of 1,000 environments per area. The goal is 20,000; the repo
does not yet contain 20,000 reviewed specifications or implementations.

`catalogue/tasks.json` contains 100 actionable starter specs: five per work area.
The 80 expanded specifications define inputs, objective, verifier, boundary cases,
data variation, evaluation and resource requirements. They target the environment contract
(`interaction: typed_answer` by default); a spec whose workflow changes system state
may be built as a `tool_episode` instead. Specs already built carry
`status: implemented` and the environment id. Published GitHub issues
are the unit of claiming. New specs must differ in reasoning, tools, constraints
or verifier; changing names, dates or paraphrases normally creates data variants.

## Infrastructure backlog

1. Tested OpenEnv adapter (multi-turn state exists: tool episodes).
2. Independent adversarial reviewer agent with bounded retries.
3. Trusted evidence ingestion and reproducible badge promotion.
4. Disposable compute-worker protocol and job selection.
5. Separate trusted merger that never executes contributor code.
6. Workflow discovery/deduplication toward 2,000 workflows and 20,000 environments.

Claims and CI work before these exist. Do not advertise automatic merging,
distributed scheduling or training-validated badges until verified end to end.
