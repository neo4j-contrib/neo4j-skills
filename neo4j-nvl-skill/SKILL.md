---
name: neo4j-nvl-skill
description: Neo4j Visualization Library (NVL) — framework-agnostic graph rendering for the browser.
  Covers @neo4j-nvl/base (NVL class, nodes/relationships, Canvas vs WebGL renderer),
  @neo4j-nvl/interaction-handlers (ZoomInteraction, PanInteraction, DragNodeInteraction, ClickInteraction,
  HoverInteraction, BoxSelectInteraction, LassoInteraction, KeyboardInteraction), and @neo4j-nvl/react
  (InteractiveNvlWrapper, BasicNvlWrapper, StaticPictureWrapper). Use when rendering a Neo4j graph in
  a browser, feeding driver results through nvlResultTransformer, choosing Canvas vs WebGL,
  wiring node/relationship click/hover/drag handlers, or embedding NVL in React, Vite,
  or vanilla JS apps.
  Does NOT handle Cypher query authoring — use neo4j-cypher-skill.
  Does NOT handle driver lifecycle, sessions, or executeQuery setup — use neo4j-driver-javascript-skill.
  Does NOT handle GraphVisualization/Needle default embed — use @neo4j-ndl/react.
compatibility: "@neo4j-nvl/base 1.1+; React 19 for @neo4j-nvl/react; modern browsers with Canvas2D + WebGL2"
version: 1.0.0
allowed-tools: Bash WebFetch
---

## When to Use
- Rendering a Neo4j graph in a browser (vanilla JS, React, Vite) with custom interactions, rendering, or data shapes
- Visualizing `driver.executeQuery` results as an interactive graph
- Wiring zoom, pan, drag, click, hover, lasso, or box-select interactions
- Embedding NVL inside an existing app and synchronizing graph state

## When NOT to Use
- **Pre-styled embedded graph view with default behavior, no custom interactions** → `GraphVisualization` from `@neo4j-ndl/react` (Neo4j Needle / NDL design system) — wraps NVL with default Neo4j styling. See [Use NVL or the Needle Component?](#use-nvl-or-the-needle-component) below.
- **Python / Jupyter notebook graph visualization** → `neo4j/python-graph-visualization` (the Python port of NVL)
- **Writing/optimizing Cypher** → `neo4j-cypher-skill`
- **Driver setup / executeQuery / sessions** → `neo4j-driver-javascript-skill`
- **Server-side data fetching with no rendering** → `neo4j-driver-javascript-skill`
- **GDS algorithm execution** → `neo4j-gds-skill` or `neo4j-aura-graph-analytics-skill`
- **GraphQL API** → `neo4j-graphql-skill`

---

## Use NVL or the Needle Component?

| Need | Use |
|---|---|
| Embed a graph view with default Neo4j styling, no custom interactions or rendering | `GraphVisualization` from `@neo4j-ndl/react` (Neo4j Needle / NDL design system) — wraps NVL and accepts records shaped `{ id, labels, properties: { key: { stringified, type } } }` (`NeoNode`) |
| Custom interactions, custom rendering, non-standard data shapes, or framework-agnostic embedding | This skill — use NVL directly |

If the answer is the first row, install and use the Needle component instead of NVL — do not duplicate styling work.

---

## Install

```bash
npm install @neo4j-nvl/base                  # core (required)
npm install @neo4j-nvl/interaction-handlers  # standard interactions (optional, vanilla JS)
npm install @neo4j-nvl/react                 # React wrappers (optional)
```

Peer requirements: **React 19** for `@neo4j-nvl/react`. The published peerDependency range still permits React 18, but mixing major versions is not recommended — target 19. `@neo4j-nvl/layout-workers` is a transitive dependency — never install directly. `neo4j-driver` is a peer of `@neo4j-nvl/base` only when using `nvlResultTransformer`.

Starter templates: https://github.com/neo4j-devtools/nvl-boilerplates — official per-framework scaffolds; prefer these over hand-rolled setups.

License: NVL ships under the **Neo4j Visualization Library License** — for use with Neo4j products only. Cannot be used against other graph backends.

---

## Pick the Right Paradigm

| Need | Use |
|---|---|
| React app, default interactions | `<InteractiveNvlWrapper>` from `@neo4j-nvl/react` |
| React app, custom interaction wiring | `<BasicNvlWrapper>` + own handlers via `ref` |
| Vanilla JS, standard interactions | `NVL` + `@neo4j-nvl/interaction-handlers` |
| Vanilla JS, fully custom event logic | `NVL` + `container.addEventListener` + `nvl.getHits()` |
| Static PNG/SVG image export | `<StaticPictureWrapper>` or `nvl.saveToFile()` / `nvl.saveToSvg()` |

---

## Pick the Right Renderer

| Renderer | Max nodes | Detail | Use case |
|---|---|---|---|
| `'canvas'` (default) | ~1,000 | Full captions, icons, arrows, pixel-perfect hit-testing | Detail investigation, small graphs |
| `'webgl'` | 100,000+ | Reduced label fidelity (bound by GPU max texture size) | Large-scale pattern exploration |

```javascript
const nvl = new NVL(container, nodes, rels, { renderer: 'webgl' })
nvl.setRenderer('canvas')   // swap at runtime
```

---

## Container Setup

The container must have an explicit `width` AND `height`. Missing height → container collapses to `0` → graph invisible. Most-reported NVL bug.

```html
<!-- ❌ height defaults to 0; graph invisible -->
<div id="viz"></div>

<!-- ✅ explicit dimensions -->
<div id="viz" style="width: 100%; height: 600px;"></div>
```

---

## Vanilla — Base Library

```javascript
import { NVL } from '@neo4j-nvl/base'

const container = document.getElementById('viz')
const nodes = [{ id: '1' }, { id: '2' }]
const relationships = [{ id: '12', from: '1', to: '2', type: 'KNOWS' }]

const nvl = new NVL(container, nodes, relationships)
```

With options + callbacks:

```javascript
import { NVL } from '@neo4j-nvl/base'

const options = {
  initialZoom: 1.0,
  minZoom: 0.1,
  maxZoom: 8,
  layout: 'forceDirected',
  renderer: 'canvas',
  styling: { defaultNodeColor: '#0e86d4', defaultRelationshipColor: '#888' }
}
const callbacks = {
  onInitialization: () => console.log('NVL ready'),
  onLayoutDone: () => nvl.fit([]),
  onError: (err) => console.error('NVL error', err)
}

const nvl = new NVL(container, nodes, relationships, options, callbacks)

// On teardown — always:
nvl.destroy()
```

`NVL` constructor signature: `new NVL(frame, nvlNodes?, nvlRels?, options?, callbacks?)`. All but `frame` are optional and default to empty.

---

## Vanilla — Interaction Handlers

Compose handlers onto an existing `NVL` instance. Each handler registers callbacks via `.updateCallback(name, fn)` and must be torn down with `.destroy()`.

```javascript
import { NVL } from '@neo4j-nvl/base'
import {
  ZoomInteraction, PanInteraction, DragNodeInteraction,
  ClickInteraction, HoverInteraction, BoxSelectInteraction,
  LassoInteraction, KeyboardInteraction
} from '@neo4j-nvl/interaction-handlers'

const nvl = new NVL(container, nodes, relationships)

const zoom  = new ZoomInteraction(nvl)
const pan   = new PanInteraction(nvl)
const drag  = new DragNodeInteraction(nvl)
const click = new ClickInteraction(nvl, { selectOnClick: true })
const hover = new HoverInteraction(nvl, { drawShadowOnHover: true })

click.updateCallback('onNodeClick',         (node, hits, evt) => console.log('node',  node.id))
click.updateCallback('onRelationshipClick', (rel,  hits, evt) => console.log('rel',   rel.id))
click.updateCallback('onCanvasClick',       (evt)             => console.log('canvas'))
hover.updateCallback('onHover',             (el, hits, evt)   => el && console.log('over', el.id))
drag.updateCallback('onDragEnd',            (nodes, evt)      => savePositions(nodes))
zoom.updateCallback('onZoom',               (level)           => console.log('zoom', level))

// Teardown — destroy all handlers, then the NVL instance
function teardown() {
  for (const h of [zoom, pan, drag, click, hover]) h.destroy()
  nvl.destroy()
}
```

Disable an event without removing the handler: `click.removeCallback('onCanvasClick')`. Passing `true` instead of a function enables the event with a no-op (useful for default selection behavior).

---

## React — InteractiveNvlWrapper

Pre-wires every interaction handler. Toggle events with `mouseEventCallbacks` (function = on + callback; `true` = on, no-op; `false`/omit = off).

```tsx
import { InteractiveNvlWrapper } from '@neo4j-nvl/react'
import type { MouseEventCallbacks, NvlOptions } from '@neo4j-nvl/react'
import { useRef } from 'react'
import type { NVL } from '@neo4j-nvl/base'

export function GraphView({ nodes, rels }) {
  const nvlRef = useRef<NVL>(null)

  const nvlOptions: NvlOptions = { initialZoom: 1, renderer: 'canvas' }

  const mouseEventCallbacks: MouseEventCallbacks = {
    onNodeClick:         (node, hits, evt) => console.log('node',  node.id),
    onRelationshipClick: (rel,  hits, evt) => console.log('rel',   rel.id),
    onCanvasClick:       (evt)             => console.log('canvas'),
    onHover:             (el, hits, evt)   => el && console.log('hover', el.id),
    onDragEnd:           (nodes, evt)      => persist(nodes),
    onZoom: true,                                       // enable, no callback
    onPan:  true
  }

  return (
    <div style={{ width: '100%', height: 600 }}>
      <InteractiveNvlWrapper
        ref={nvlRef}
        nodes={nodes}
        rels={rels}
        nvlOptions={nvlOptions}
        interactionOptions={{ selectOnClick: true, drawShadowOnHover: true }}
        mouseEventCallbacks={mouseEventCallbacks}
        onInitializationError={(err) => console.error('NVL init', err)}
      />
    </div>
  )
}
```

`ref` resolves to the underlying `NVL` instance — call any method on it: `nvlRef.current?.fit([])`, `nvlRef.current?.setRenderer('webgl')`, `nvlRef.current?.saveToFile()`.

---

## React — BasicNvlWrapper + Ref

No interactions wired. The ref exposes every NVL method via `IncludeMethods<NVL>` — use when building custom interaction logic in React.

```tsx
import { BasicNvlWrapper } from '@neo4j-nvl/react'
import type { NVL } from '@neo4j-nvl/base'
import { useRef } from 'react'

export function MiniGraph({ nodes, rels }) {
  const nvlRef = useRef<NVL>(null)

  return (
    <div style={{ width: '100%', height: 400 }}>
      <BasicNvlWrapper
        ref={nvlRef}
        nodes={nodes}
        rels={rels}
        nvlOptions={{ initialZoom: 2 }}
        nvlCallbacks={{ onLayoutDone: () => nvlRef.current?.fit([]) }}
      />
      <button onClick={() => nvlRef.current?.fit(['1', '2'])}>Zoom to 1,2</button>
    </div>
  )
}
```

---

## Wiring a Neo4j Driver Result

`@neo4j-nvl/base` exports a `ResultTransformer` for the JS driver that deduplicates nodes/relationships across any record shape.

```javascript
import neo4j from 'neo4j-driver'
import { NVL, nvlResultTransformer } from '@neo4j-nvl/base'

const driver = neo4j.driver(process.env.NEO4J_URI,
  neo4j.auth.basic(process.env.NEO4J_USERNAME, process.env.NEO4J_PASSWORD))

const { nodes, relationships } = await driver.executeQuery(
  'MATCH (a)-[r]-(b) RETURN a, r, b LIMIT 25',
  {},
  { database: 'neo4j', resultTransformer: nvlResultTransformer }
)

const nvl = new NVL(document.getElementById('viz'), nodes, relationships)
```

```javascript
// ❌ raw EagerResult — records are not Node/Relationship objects
const result = await driver.executeQuery('MATCH (a)-[r]-(b) RETURN a, r, b')
new NVL(container, result.records, [])   // breaks

// ✅ use the transformer
const { nodes, relationships } = await driver.executeQuery(
  'MATCH (a)-[r]-(b) RETURN a, r, b',
  {},
  { database: 'neo4j', resultTransformer: nvlResultTransformer }
)
new NVL(container, nodes, relationships)
```

For driver lifecycle, session management, Integer handling, and TypeScript types → `neo4j-driver-javascript-skill`.

---

## Updating the Graph

| Method | Behavior |
|---|---|
| `addAndUpdateElementsInGraph(nodes, rels)` | Insert new; update existing by id (only specified fields) |
| `updateElementsInGraph(nodes, rels)` | Update existing only; ignores unknown ids |
| `addElementsToGraph(nodes, rels)` | Insert only; throws on existing id |
| `removeNodesWithIds(ids)` | Remove nodes; adjacent relationships auto-removed |
| `removeRelationshipsWithIds(ids)` | Remove relationships |
| `setNodePositions(nodes, updateLayout?)` | Override positions; optionally re-run layout |
| `restart(options?, retainPositions?)` | Restart with new options; positions optional |

Diff updates use `PartialNode` / `PartialRelationship` — only `id` is required:

```javascript
nvl.updateElementsInGraph(
  [{ id: '1', color: '#f00', selected: true }],   // PartialNode
  [{ id: '12', width: 4 }]                         // PartialRelationship
)
```

---

## Hit Testing (Manual)

Use when NOT using the interaction-handlers package. `getHits()` resolves which node/relationship is under a pointer event.

```javascript
const nvl = new NVL(container, nodes, rels)

container.addEventListener('click', (evt) => {
  const { nvlTargets } = nvl.getHits(evt, ['node', 'relationship'], { hitNodeMarginWidth: 4 })
  const hitNode = nvlTargets.nodes[0]
  const hitRel  = nvlTargets.relationships[0]
  if (hitNode) console.log('hit node', hitNode.data.id)
  else if (hitRel) console.log('hit rel', hitRel.data.id)
  else console.log('hit canvas')
})
```

`HitTargetNode` / `HitTargetRelationship` carry `data`, `pointerCoordinates`, `distance`, `insideNode` (nodes only). See [references/api-surface.md](references/api-surface.md).

---

## Common Mistakes

| Mistake | Fix |
|---|---|
| Container with no `height` → invisible graph | Set explicit `width` and `height` on the container |
| Pass `driver.executeQuery` result directly | Use `nvlResultTransformer` and consume `{ nodes, relationships }` |
| WebGL for small label-rich graphs | Use `'canvas'`; labels are fully supported |
| Canvas for 10k+ nodes | Switch to `'webgl'` via `renderer` option or `setRenderer` |
| New `NVL` per React render | Use `<InteractiveNvlWrapper>` / `<BasicNvlWrapper>` or wrap in `useEffect` + `destroy()` |
| Forgetting `nvl.destroy()` on teardown | Call `destroy()` on unmount; React wrappers handle this automatically |
| Vanilla handlers not torn down | Call `.destroy()` on every interaction before `nvl.destroy()` |
| Worker construction blocked (strict CSP / sandboxed runtime / older bundler) | `nvlOptions: { disableWebWorkers: true }` (NVL has a non-worker fallback) |
| Telemetry enabled in regulated env | `nvlOptions: { disableTelemetry: true }` |
| Layout never settles | Pin anchor nodes with `pinNode(id)`; tune `layoutTimeLimit` |
| `selectOnClick` fires double | Toggle once at mount; don't flip `interactionOptions` per render |
| Hit test misses near node edge | Pass `{ hitNodeMarginWidth: N }` to `getHits` |
| Captions missing on WebGL | GPU max texture size exceeded; fall back to Canvas or shrink captions |

---

## References

Load on demand:
- [references/api-surface.md](references/api-surface.md) — complete `NVL` method table; `Node`, `Relationship`, `NvlOptions`, `LayoutOptions`, `ExternalCallbacks`, `HitTargets`, `NvlMouseEvent`, `StyledCaption`, `Point`; every interaction-handler class + its options + its callback signatures; React `<InteractiveNvlWrapper>` / `<BasicNvlWrapper>` / `<StaticPictureWrapper>` props; `MouseEventCallbacks` and `KeyboardEventCallbacks` shapes; named exports inventory; `nvlResultTransformer` signature
- [references/troubleshooting.md](references/troubleshooting.md) — zero-height container, build-tool-agnostic `disableWebWorkers` fallback, Canvas/WebGL trade-offs + WebGL2 note, WebGL texture-size cap, `onWebGLContextLost` recovery, telemetry opt-out, memory leaks, stuck layouts, double selection, hit-margin tuning, license restriction

Canonical web documentation (use `WebFetch` when references above are insufficient):
- https://neo4j.com/docs/nvl/current/ — user guide (installation, base library, interaction handlers, React wrappers)
- https://neo4j.com/docs/api/nvl/current/ — TypeDoc API reference
- https://neo4j.com/docs/api/nvl/current/examples.html — runnable examples
- https://github.com/neo4j-devtools/nvl-boilerplates — official starter templates per supported framework
- https://github.com/neo4j/python-graph-visualization — Python port of NVL (use this skill only for the JavaScript/browser path)

---

## Checklist
- [ ] Container has explicit `width` AND `height` CSS
- [ ] Correct paradigm chosen from the decision table (vanilla / handlers / React)
- [ ] Renderer matches expected node count (Canvas ≲1k / WebGL 100k+)
- [ ] Driver `executeQuery` results piped through `nvlResultTransformer`
- [ ] `database` specified on every `executeQuery` call (delegate to `neo4j-driver-javascript-skill`)
- [ ] All interaction handlers `.destroy()`-ed before `nvl.destroy()` on teardown
- [ ] `nvl.destroy()` called on React unmount (manual instances only — wrappers handle it)
- [ ] `disableTelemetry: true` set when in regulated / offline environments
- [ ] `disableWebWorkers: true` set when bundler / CSP blocks worker construction
- [ ] Graph updates use `addAndUpdateElementsInGraph` / `updateElementsInGraph` — not `restart`
- [ ] License compatible: target is a Neo4j product
