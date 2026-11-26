# Lifecycle and graph updates

When you need this: you add, change or remove elements after the first render, restart NVL, tear it down, or handle WebGL context loss.

Verification tags: **source**, **types**, **runtime** (see `SKILL.md`).

## Updating the graph

| Method | Behaviour |
|---|---|
| `addAndUpdateElementsInGraph(nodes, rels)` | Insert new ids; update existing ones with the given fields |
| `updateElementsInGraph(nodes, rels)` | Update existing only; unknown ids are ignored |
| `addElementsToGraph(nodes, rels)` | Insert only; **existing ids are silently skipped** |
| `removeNodesWithIds(ids)` | Remove nodes and their relationships |
| `removeRelationshipsWithIds(ids)` | Remove relationships |
| `setNodePositions(nodes, updateLayout?)` | Move nodes; optionally let the layout continue |
| `restart(options?, retainPositions?)` | Rebuild with merged options |

*source*

Updates take `PartialNode` / `PartialRelationship`: only `id` is required. *types*

```javascript
nvl.updateElementsInGraph(
  [{ id: '1', color: '#f00', selected: true }],
  [{ id: '12', width: 4 }]
)
```

Prefer the update methods over `restart` for data changes: `restart` recreates the renderer and layout and resets interaction state.

Invalid elements (missing `id`, or a relationship whose `from` / `to` is unknown) go to `onError` when it is registered; otherwise a `TypeError` is thrown. *source*

## Teardown

Vanilla: destroy every interaction handler, then the instance.

```javascript
for (const h of handlers) h.destroy()
nvl.destroy()
```

React: the wrappers do this on unmount. A manual `new NVL(...)` inside `useEffect` needs `return () => nvl.destroy()`, or the instance leaks across route changes.

## `restart`

`restart(options, retainPositions)` merges `options` into the current ones and rebuilds. With `retainPositions: true` nodes keep their coordinates. Use it to change creation-time options such as `styling` or `minZoom`; it does not restart a settled force-directed simulation (see [layouts-and-positions](layouts-and-positions.md)). *types, runtime*

## WebGL context lost

`onWebGLContextLost(event)` fires when the GPU drops the context (tab backgrounded, driver reset). Recover by switching renderer or restarting: *types*

```javascript
new NVL(container, nodes, rels, { renderer: 'webgl' }, {
  onWebGLContextLost: () => nvl.restart({ renderer: 'canvas' }, true)
})
```

## Telemetry

NVL sends anonymous usage events through Segment unless `disableTelemetry: true` is set. Set it in regulated, offline and test environments. *source*

## Errors

Register `onError` to receive validation errors instead of exceptions; without it they throw. Worker construction failures are only logged with `console.warn` and fall back silently; a worker that loads but fails is not reported at all (see [vite-and-bundlers](vite-and-bundlers.md)). *source*
