# Layouts and positions

When you need this: a layout does not re-run when you expect it to, nodes do not move when you set coordinates, or you need to choose a layout.

Verification tags: **source**, **types**, **runtime** (see `SKILL.md`).

## Choosing a layout

| Data shape | `layout` | Notes |
|---|---|---|
| Generic network | `'forceDirected'` (default) | GPU physics on WebGL2; `layoutOptions.clustering`, `seedingMethod: 'box' \| 'circle'` |
| Tree / DAG | `'hierarchical'` | `layoutOptions.direction`, `packing`; runs in a `SharedWorker` (see [vite-and-bundlers](vite-and-bundlers.md)) |
| Ring | `'circular'` | `layoutOptions.sortFunction: (nodes) => nodes` |
| Your own coordinates | `'free'` | Nothing moves; use `setNodePositions` |
| Grid | `'grid'` | |
| CPU force (d3) | `'d3Force'` | |

*types*

`minFps` / `maxFps` (defaults `3` / `30`, capped `1..120`) set the presentation rate while a layout is active. *types*

## Callbacks

- `onLayoutComputing(isComputing)` fires at start and end of a computation.
- `onLayoutDone()` fires when the layout settles. Trigger `fit`, exports and screenshots from here.
- `onLayoutStep(nodes)` fires every step with `NodeWithClientPosition[]`. Registering it disables the GPU position fast path (positions must be read back to the CPU each frame), so use it only when you need per-frame positions. *source*

## When a layout re-runs, and when it does not

- `setLayout(type)` with a **different** type switches and runs the new layout. Calling it with the current type does nothing visible. *source*
- `setLayoutOptions(options)` updates the layout's options and redraws the cluster overlay when `clustering` is present. For the circular layout, changing `sortFunction` does **not** re-run the layout or fire `onLayoutDone`. *source, runtime*
- Un-pinning nodes while `forceDirected` is active does not restart a settled simulation. *runtime*
- `restart(options, true)` rebuilds NVL with merged options and keeps positions; it did not restart the simulation in the un-pin case. *runtime*

Working restarts:

```javascript
// circular with a new order
nvl.setLayout('free')
nvl.setLayoutOptions({ sortFunction: byDegree })
nvl.setLayout('circular')

// wake a settled force-directed layout
nvl.setNodePositions(nvl.getNodePositions(), true)
```

## Setting positions

- `setNodePositions(nodes, updateLayout = false)` moves nodes to the given `x` / `y`. With `updateLayout: true` the current layout continues from there. *types*
- Never set `x` / `y` on node data (`addAndUpdateElementsInGraph`, `updateElementsInGraph`, the React `nodes` prop). Positions are owned by the layout, and these properties are slated for removal from `Node`. `setNodePositions` (or the React `positions` prop) is the way to position nodes. *source*
- `pinNode(id)` / `unPinNode(ids: string[])` or `pinned: true` in node data hold nodes in place for the force-directed layout, at whatever position they currently have. Clustering forces ignore pins (see [clustering](clustering.md)). *types, runtime*
- Fixed anchors under `forceDirected`: insert the anchors with `pinned: true`, then `setNodePositions(anchors, true)` right after construction so the layout continues around them. Releasing them: `unPinNode(ids)` then `setNodePositions(getNodePositions(), true)`. *runtime*

## Coordinates

`getNodes()` returns `x` / `y` in layout space and `clientPosition` relative to the canvas element. `getNodePositions()` returns layout coordinates only. *types*

Layout → screen: `screen = (world - pan) * scale + containerSize / 2`, with `scale = getScale()` and `pan = getPan()`. A node's `size` is its radius in world units. *runtime*

## Layout never settles

- Pin anchor nodes (`pinNode`).
- Use `hierarchical` for tree-shaped data.
- Reduce the node count.
- There is no `layoutTimeLimit` option; older guidance that mentions it is wrong. *types*
