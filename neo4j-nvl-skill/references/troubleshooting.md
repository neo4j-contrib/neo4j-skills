# NVL — Troubleshooting & Gotchas

## Container renders nothing / 0×0

**Cause:** Parent `<div>` has no explicit height. NVL inherits `0` → graph invisible.

```html
<!-- ❌ -->
<div id="viz"></div>

<!-- ✅ -->
<div id="viz" style="width: 100%; height: 600px;"></div>
```

React: wrap `<InteractiveNvlWrapper>` or `<BasicNvlWrapper>` in a sized parent OR pass `style={{ width, height }}` directly (the wrappers forward `HTMLProps<HTMLDivElement>`).

---

## Driver `EagerResult` rejected by NVL

**Cause:** Default `executeQuery` returns `{ records, summary, keys }` — records are not `Node`/`Relationship` shapes.

```javascript
// ❌
const res = await driver.executeQuery('MATCH (a)-[r]-(b) RETURN a,r,b LIMIT 25')
new NVL(container, res.records, [])    // ids missing, shape wrong

// ✅
import { nvlResultTransformer } from '@neo4j-nvl/base'
const { nodes, relationships } = await driver.executeQuery(
  'MATCH (a)-[r]-(b) RETURN a,r,b LIMIT 25', {},
  { database: 'neo4j', resultTransformer: nvlResultTransformer }
)
new NVL(container, nodes, relationships)
```

For driver setup → `neo4j-driver-javascript-skill`.

---

## Web Worker construction blocked

**Cause:** NVL's `@neo4j-nvl/layout-workers` spawns Web Workers for the force-directed and hierarchical layouts. Some environments block worker construction — strict CSP (`worker-src 'none'`), sandboxed iframes, custom runtimes, or older build tools that don't bundle workers correctly.

**Fix:** Disable workers — NVL has a synchronous fallback (slower for large graphs, identical output). Applies to any build tool (Vite, Webpack, Rollup, esbuild, Parcel, etc.):

```javascript
const nvl = new NVL(container, nodes, rels, { disableWebWorkers: true })
```

React:

```tsx
<InteractiveNvlWrapper nvlOptions={{ disableWebWorkers: true }} ... />
```

Most modern bundlers handle worker construction natively — try the default setup first, fall back to `disableWebWorkers: true` only when worker errors actually appear.

---

## Renderer trade-off (Canvas vs WebGL)

| Renderer | Practical ceiling | Captions | Hit-test |
|---|---|---|---|
| Canvas (default) | ~1,000 nodes | Full styling | Pixel-perfect |
| WebGL | 100,000+ nodes | Not supported | Approximate |

NVL 2.0's GPU renderer and physics engine require **WebGL2**. WebGL1 is not supported. WebGL rendering now supports node icons and relationship arrowheads, but not captions.

```javascript
// At construction
new NVL(container, nodes, rels, { renderer: 'webgl' })

// At runtime
nvl.setRenderer('webgl')   // or 'canvas'
```

Pick based on node count and whether captions are required. Switching at runtime triggers a re-render. Set `disableWebGL: true` to explicitly use non-WebGL rendering and layout implementations.

---

## WebGL captions/labels are missing

**Cause:** Expected NVL 2.0 behavior. The WebGL renderer does not support captions.

**Fix:** Use Canvas when captions are required:

```javascript
nvl.setRenderer('canvas')
```

---

## React `layout` or `layoutOptions` has no effect

**Cause:** NVL 2.0 removed the deprecated standalone React wrapper props.

```tsx
// ❌ removed in 2.0
<InteractiveNvlWrapper layout="hierarchical" layoutOptions={{ direction: 'down' }} />

// ✅ put both options in nvlOptions
<InteractiveNvlWrapper
  nvlOptions={{ layout: 'hierarchical', layoutOptions: { direction: 'down' } }}
/>
```

---

## `onZoom` callback no longer fires

**Cause:** NVL 2.0 removed `onZoom`.

**Fix:** Use `onZoomAndPan`, which includes the complete viewport state:

```javascript
zoom.updateCallback('onZoomAndPan', (zoomLevel, panX, panY, event) => {
  console.log({ zoomLevel, panX, panY })
})
```

For React, set `mouseEventCallbacks={{ onZoomAndPan: callback }}`.

---

## Force-directed clusters do not appear

**Cause:** Force-directed clustering options must be nested under `layoutOptions.clustering`; hierarchical `clusterBy` is placed directly under `layoutOptions`.

```javascript
// Force-directed
const options = {
  layout: 'forceDirected',
  layoutOptions: {
    clustering: {
      clusterBy: (nodeId) => categoryByNodeId[nodeId],
      drawOutline: true,
      drawHalo: true
    }
  }
}

// Hierarchical
const hierarchicalOptions = {
  layout: 'hierarchical',
  layoutOptions: {
    direction: 'down',
    clusterBy: (nodeId) => categoryByNodeId[nodeId]
  }
}
```

The callback must return the same string or number for nodes in one cluster. Return `undefined` for independent nodes. In React, keep the callback stable with `useCallback`; otherwise changing its identity can cause repeated cluster evaluation.

---

## Cluster click callback misses clicks

**Cause:** `onClusterClick`, `onClusterDoubleClick`, and `onClusterRightClick` apply to empty space inside a force-directed cluster hull. A node or relationship under the pointer takes priority.

**Fix:** Use node/relationship callbacks for direct element hits and cluster callbacks for hull space. For hover, inspect `hitElements.clusters` from `onHover`:

```javascript
hover.updateCallback('onHover', (_element, hitElements) => {
  const cluster = hitElements.clusters[0]?.data
  if (cluster) console.log(cluster.id, cluster.nodeIds)
})
```

---

## `onWebGLContextLost` fires

**Cause:** GPU dropped the context (tab backgrounded too long, driver crash, OS swap).

**Fix:** Implement `onWebGLContextLost` callback — call `nvl.setRenderer('canvas')` as recovery, or `nvl.restart(options, true)` to reinitialize while keeping positions:

```javascript
const nvl = new NVL(container, nodes, rels,
  { renderer: 'webgl' },
  { onWebGLContextLost: () => nvl.restart({ renderer: 'canvas' }, true) }
)
```

---

## Telemetry — opting out

**Cause:** NVL ships Segment Analytics; runs by default.

**Fix:**

```javascript
new NVL(container, nodes, rels, { disableTelemetry: true })
```

Mandatory in regulated / air-gapped / customer-data-sensitive deployments.

---

## Memory leak after route change (React)

**Cause:** Custom `useRef` + manual `new NVL(...)` not torn down on unmount.

**Fix:** Always call `nvl.destroy()` in cleanup:

```tsx
useEffect(() => {
  const nvl = new NVL(ref.current!, nodes, rels)
  return () => nvl.destroy()
}, [])
```

`<InteractiveNvlWrapper>` / `<BasicNvlWrapper>` handle this automatically — prefer them over manual refs.

For vanilla, destroy all interaction handlers BEFORE the NVL instance:

```javascript
for (const h of handlers) h.destroy()
nvl.destroy()
```

---

## Layout never settles / `isLayoutMoving` stays true

**Cause:** Graph has competing forces or is unsolvable; or workers disabled and synchronous fallback is throttled.

**Fix options:**
- Pin anchor nodes: `nvl.pinNode(id)` for known fixed positions
- Cap iterations: `nvlOptions: { layoutTimeLimit: 3000 }` (ms)
- Switch layout: `nvl.setLayout('hierarchical')` for DAG-like data
- Reduce nodes (paginate query, increase `LIMIT`)

---

## Selection callback fires twice

**Cause:** `selectOnClick` toggled mid-render OR both base handler + wrapper handling clicks.

**Fix:** Set `interactionOptions={{ selectOnClick: true }}` once at mount and leave it; don't flip the value across renders. If using vanilla `ClickInteraction`, do not also register a manual `container.addEventListener('click', ...)`.

---

## Hit test misses near node edge

**Cause:** Default `hitNodeMarginWidth: 0` requires pointer strictly inside the node circle.

**Fix:** Widen the hit margin:

```javascript
const { nvlTargets } = nvl.getHits(evt, ['node', 'relationship'], { hitNodeMarginWidth: 8 })
```

For pan-on-relationship sensitivity, set `excludeNodeMargin: true` in `PanInteraction` options.

To include cluster hulls when supplying an explicit target list, add `'cluster'`. Cluster hits are included by default when the target list is omitted:

```javascript
const { nvlTargets } = nvl.getHits(evt, ['node', 'relationship', 'cluster'])
```

---

## Layout / hierarchy looks wrong

**Cause:** Default `'forceDirected'` not suited for tree / pipeline / circular data.

**Fix:** Pick the right layout up front:

| Data shape | Layout |
|---|---|
| Generic network | `'forceDirected'` |
| Tree / DAG | `'hierarchical'` (set `direction` in `layoutOptions`) |
| Sorted ring | `'circular'` (provide `sortFunction`) |
| Manual positioning | `'free'` |
| Snapped grid | `'grid'` |
| Force-directed via d3-force | `'d3Force'` |

---

## License pitfall

**Cause:** NVL is licensed under the Neo4j Visualization Library License — for use with Neo4j products only.

**Implication:** Cannot ship NVL inside an application that uses a non-Neo4j graph backend (Neptune, JanusGraph, ArangoDB, etc.) as its primary data store. Refer to the LICENSE.txt in `@neo4j-nvl/base` and confirm with legal before redistribution.

---

## Image export returns blank PNG

**Cause:** Called `saveToFile()` before `onLayoutDone` fires — initial positions still settling.

**Fix:** Trigger export from the callback:

```javascript
const nvl = new NVL(container, nodes, rels, {},
  { onLayoutDone: () => nvl.saveToFile({ filename: 'graph.png' }) })
```

Or `getImageDataUrl()` for in-memory data URL.

---

## `restart()` vs `addAndUpdateElementsInGraph()`

**`restart()`** rebuilds internal state; expensive; resets selection unless `retainPositions=true` is passed AND positions are preserved. Use for option changes (renderer, layout, styling).

**`addAndUpdateElementsInGraph()`** is the correct API for streaming data changes. Use for live updates.

```javascript
// ❌ data update via restart — full rebuild every tick
nvl.restart()

// ✅ diff update
nvl.addAndUpdateElementsInGraph(newNodes, newRels)
```
