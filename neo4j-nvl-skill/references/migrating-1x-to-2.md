# Migrating from NVL 1.x to 2.0

When you need this: code or examples written for 1.x behave differently, or an option is reported as unknown.

Verification tags: **source**, **types**, **runtime** (see `SKILL.md`).

## React wrapper props

`layout` and `layoutOptions` are no longer props of the wrappers; they live in `nvlOptions`. Passing them as props is a type error and has no effect. *types*

```tsx
// 1.x
<InteractiveNvlWrapper layout="hierarchical" layoutOptions={{ direction: 'down' }} />

// 2.0
<InteractiveNvlWrapper nvlOptions={{ layout: 'hierarchical', layoutOptions: { direction: 'down' } }} />
```

## `onZoom` removed

The `ZoomInteraction` callback is `onZoomAndPan(zoomLevel, panX, panY, event)`. In the React wrapper the key is `mouseEventCallbacks.onZoomAndPan`; it is also what enables wheel zoom. *source*

## Removed options

- `intelWorkaround` (GPU shader workaround) is gone.
- `enableCytoscape` and other Cytoscape-related layout settings are gone.

*types*

## Renderer

- WebGL rendering and the force-directed physics require **WebGL2**; WebGL1 is not supported.
- The WebGL renderer supports node icons and relationship arrowheads but **not captions**. Use the Canvas renderer when labels matter.
- `disableWebGL: true` forces Canvas rendering and non-GPU layouts.

*types*

## Return types

`getNodes()` and `onLayoutStep` return `NodeWithClientPosition[]`: `x` / `y` are layout coordinates and `clientPosition` is relative to the canvas element. *types*

## Styling

`styling.minimapViewportBoxColor` is deprecated; use `styling.overlayLineColor`, which also colours cluster outlines for mixed-colour clusters. *types*

## New in 2.0

- Clustering: `layoutOptions.clustering` for force-directed, `layoutOptions.clusterBy` for hierarchical (see [clustering](clustering.md)).
- `onClusterClick` / `onClusterDoubleClick` / `onClusterRightClick` in `ClickInteraction` and `getHits(event, ['cluster'])`.
- `minFps` / `maxFps` presentation targets and `layoutOptions.seedingMethod` for force-directed.
