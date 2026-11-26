# Clustering

When you need this: you want nodes grouped by a property, drawn with outlines or halos, or you need to react to clicks and hovers on a cluster.

Verification tags: **source**, **types**, **runtime** (see `SKILL.md`).

## Options per layout

`clusterBy` is `(nodeId: string) => string | number | undefined`. Nodes returning the same value share a cluster; `undefined` means independent. Keep the function reference stable (`useCallback` in React) or the clustering is re-evaluated on every render. *types*

| Layout | Where | Decorations | Hulls / hit-testing |
|---|---|---|---|
| `forceDirected` | `layoutOptions.clustering: { clusterBy, drawOutline, drawHalo, crossClusterRelationshipMultiplier }` | yes | yes |
| `hierarchical` | `layoutOptions.clusterBy` (experimental) | no | no |
| `circular` | none; order nodes with `layoutOptions.sortFunction` | no | no |
| `free`, `grid`, `d3Force` | not supported | no | no |

*types, source*

```javascript
const clusterBy = (nodeId) => categoryByNodeId[nodeId]

// force-directed
new NVL(container, nodes, rels, {
  layout: 'forceDirected',
  layoutOptions: {
    clustering: { clusterBy, drawOutline: true, drawHalo: true, crossClusterRelationshipMultiplier: 0.2 }
  }
})

// hierarchical
new NVL(container, nodes, rels, {
  layout: 'hierarchical',
  layoutOptions: { direction: 'down', clusterBy }
})
```

`crossClusterRelationshipMultiplier` (default `0`, capped `0..1`) scales the spring pull of relationships that cross clusters; intra-cluster edges stay at full strength. Values near `1` can destabilise highly connected graphs. *types*

## Outlines and halos

- Outline colour is the shared node colour of the cluster; if colours differ it falls back to `styling.overlayLineColor`. *types*
- A halo is drawn **only** when every node in the cluster has the same colour. Mixed colours → no halo, no error. *types*
- Decorations are drawn for the force-directed layout only. Switching to `free` keeps positions but removes the overlay. *source, runtime*
- Changing `layoutOptions.clustering` through `setLayoutOptions` redraws the overlay. *source*

## A `Cluster` is not a graph element

`Cluster = { id: string | number, nodeIds: string[] }`. It has no colour or position of its own; its hull is computed from the member positions. *types*

## Clicks

`ClickInteraction` resolves hits in priority order: nodes, then relationships, then clusters, then canvas. Cluster callbacks (`onClusterClick`, `onClusterDoubleClick`, `onClusterRightClick`) fire only for empty space inside a hull. *source*

With `selectOnClick: true`, clicking inside a hull selects **all** `cluster.nodeIds`; clicking again deselects them (a cluster counts as selected when all members are). *source*

To select single nodes but still know when a hull is clicked:

```javascript
const click = new ClickInteraction(nvl, { selectOnClick: false })
click.updateCallback('onNodeClick', (node) => nvl.updateElementsInGraph([{ id: node.id, selected: true }], []))
click.updateCallback('onClusterClick', (cluster) => console.log('hull', cluster.id, cluster.nodeIds.length))
```

## Hover

`HoverInteraction` has a single `onHover(element, hitElements, event)` callback where `element` is a node, a relationship or `undefined`. There is no cluster hover event, but `hitElements.clusters` is filled: *types, source*

```javascript
hover.updateCallback('onHover', (element, hits) => {
  const cluster = hits.clusters[0]?.data
  if (!element && cluster) showTooltip(cluster.id)
})
```

Without the interaction handlers: `nvl.getHits(event, ['cluster'])` returns `nvlTargets.clusters` with `data`, `pointerCoordinates` and the convex `hull` points. Clusters are included by default when the target list is omitted. *types*

## Clustering and pinned nodes

With `clustering.clusterBy` set, the force simulation moves pinned nodes too; re-applying positions does not hold them. Do not combine pinning with clustering. *runtime*

## Checklist

- Force-directed for decorations and hull interactions; hierarchical only groups.
- One colour per cluster if you want halos.
- `selectOnClick: false` if a hull click must not select every member.
- Stable `clusterBy` reference in React.
