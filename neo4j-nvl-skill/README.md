# neo4j-nvl-skill

Skill for the Neo4j Visualization Library (NVL) — covering:

- `@neo4j-nvl/base` — `NVL` class, nodes/relationships, options, callbacks, hit testing, image export
- `@neo4j-nvl/interaction-handlers` — `ZoomInteraction`, `PanInteraction`, `DragNodeInteraction`, `ClickInteraction`, `HoverInteraction`, `BoxSelectInteraction`, `LassoInteraction`, `KeyboardInteraction`
- `@neo4j-nvl/react` — `InteractiveNvlWrapper`, `BasicNvlWrapper`, `StaticPictureWrapper`
- `nvlResultTransformer` for piping `driver.executeQuery` results straight into NVL
- Canvas vs WebGL renderer selection (~1k vs 100k+ nodes)
- Layout selection (`forceDirected`, `hierarchical`, `circular`, `grid`, `free`, `d3Force`)
- Container setup, Web Worker fallback, telemetry opt-out

**Not covered** (see sibling tools / skills):
- Out-of-the-box embedded graph view with default styling → `GraphVisualization` component in `@neo4j-ndl/react` (Neo4j Needle design system) — wraps NVL with defaults
- Python / Jupyter graph visualization → `neo4j/python-graph-visualization` (Python port of NVL)
- Cypher query authoring → `neo4j-cypher-skill`
- Driver lifecycle, sessions, `executeQuery` setup → `neo4j-driver-javascript-skill`
- GDS algorithms → `neo4j-gds-skill` / `neo4j-aura-graph-analytics-skill`

**Compatibility:** `@neo4j-nvl/base` 1.1+; React 19 for `@neo4j-nvl/react`; modern browsers with Canvas2D + WebGL2.

**Install:**

```bash
npm install @neo4j-nvl/base
npm install @neo4j-nvl/interaction-handlers   # optional, for vanilla JS interactions
npm install @neo4j-nvl/react                  # optional, for React apps
```

Starter templates: https://github.com/neo4j-devtools/nvl-boilerplates

**Install skill:**

```bash
npx skills add https://github.com/neo4j-contrib/neo4j-skills
```
