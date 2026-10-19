# Provenance — Neo4j Ontology Graph Specification assets

- **Source repo**: `neo4j/graph-spec` (https://github.com/neo4j/graph-spec)
- **Branch**: `ontology-graph-spec` — PR #118, pre-merge draft status (not yet merged to the spec's mainline)
- **Pinned commit**: `2f8dcbdf2dab51ebf2d760e00904a8f2b0518f59`
- **Fetch date (UTC)**: 2026-10-19

The assets here are an immutable snapshot fetched from `raw.githubusercontent.com` at the pinned
commit SHA above (not the branch name), so they do not drift as the PR branch moves.

## Refresh

Set the SHA to pin (re-resolve the branch HEAD with
`git ls-remote https://github.com/neo4j/graph-spec.git refs/heads/ontology-graph-spec`),
then re-fetch every asset with this curl pattern:

```bash
SHA=<40-char-pinned-commit-sha>

curl -fsSL "https://raw.githubusercontent.com/neo4j/graph-spec/${SHA}/ontology-graph-spec.schema.json" \
  -o neo4j-ontology-skill/assets/ontology-graph-spec.schema.json

curl -fsSL "https://raw.githubusercontent.com/neo4j/graph-spec/${SHA}/src/jvmTest/resources/ontology/movies.ontology.json" \
  -o neo4j-ontology-skill/assets/examples/movies.ontology.json

curl -fsSL "https://raw.githubusercontent.com/neo4j/graph-spec/${SHA}/src/jvmTest/resources/ontology/foaf.ontology.json" \
  -o neo4j-ontology-skill/assets/examples/foaf.ontology.json

curl -fsSL "https://raw.githubusercontent.com/neo4j/graph-spec/${SHA}/src/jvmTest/resources/ontology/org.ontology.json" \
  -o neo4j-ontology-skill/assets/examples/org.ontology.json
```

After refreshing, update the pinned commit and fetch date in this file.
