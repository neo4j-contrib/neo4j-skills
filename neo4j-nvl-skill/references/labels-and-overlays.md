# Labels, icons and overlays

When you need this: text or images on nodes, especially with the WebGL renderer, or you want to draw your own overlay (axes, legends, tooltips) that follows pan and zoom.

Verification tags: **source**, **types**, **runtime** (see `SKILL.md`).

## Renderer trade-off

| Renderer | Practical ceiling | Captions | Icons / arrowheads | Hit-test |
|---|---|---|---|---|
| `'canvas'` (default) | ~1,000 nodes | yes | yes | exact |
| `'webgl'` | 100,000+ nodes | **no** | yes | approximate |

WebGL rendering and the force-directed physics need **WebGL2**. `disableWebGL: true` forces Canvas and the non-GPU layout implementations. Switch at runtime with `setRenderer`. *types*

An experimental `'svg'` renderer exists internally but is excluded from the public `Renderer` type; use `saveToSvg()` for SVG output. *types*

## Captions

`caption` (single string) or `captions: StyledCaption[]` (styled, multiple); `captions` wins if both are set. Captions are drawn by the Canvas renderer only; with WebGL they are silently absent. There is no texture-size limit involved; it is a renderer feature gap. *types*

Options when you need text and WebGL:

1. `html` overlay per node (see below) for a few hundred visible nodes.
2. `icon` for an image glyph instead of text.
3. Draw your own overlay from `getNodes()` positions.
4. Switch to `'canvas'` when zoomed in.

## `icon`

- URL of a square image drawn inside the node. Icons are expected to be black; on dark node colours they are inverted to white. *types*
- The WebGL renderer holds at most 256 distinct icon images (`url` × inverted/not); further icons are silently not drawn, with no warning. The Canvas renderer has no such cap. Keep the set of distinct images small. *source, runtime*

## `overlayIcon`

`{ url, position?: number[], size?: number }` draws a square image anywhere over the element; `size` is relative to the node size (default `1`). *types*

## `html`

`html: HTMLElement` is placed in an absolutely positioned `<div>` over the node, scaled with the zoom level. Experimental. *types, source*

- Each node with `html` keeps about two DOM elements alive; 3,825 nodes gave ~7,700 elements and idle FPS fell from ~60 to ~50. *runtime*
- Any `html` overlay disables the GPU position fast path, because positions must be read back to the CPU each frame. *source*
- Relationship HTML captions are hidden with the WebGL renderer. *source*

## Drawing your own overlay

Use a sibling element over the container and convert coordinates:

```javascript
const toScreen = ({ x, y }) => {
  const scale = nvl.getScale()
  const pan = nvl.getPan()
  const { width, height } = nvl.getContainer().getBoundingClientRect()
  return { x: (x - pan.x) * scale + width / 2, y: (y - pan.y) * scale + height / 2 }
}
```

- Node `size` is the radius in world units, so the screen radius is `size * scale`. *runtime*
- `getNodes()` already includes `clientPosition` relative to the canvas, which is the same conversion. *types*
- Redraw on `onZoomAndPan`, `onPan` and `onLayoutStep` (or on `onLayoutDone` if per-frame updates are not needed, to keep the GPU fast path).

## Hit testing without interaction handlers

```javascript
container.addEventListener('click', (evt) => {
  const { nvlTargets } = nvl.getHits(evt, ['node', 'relationship', 'cluster'], { hitNodeMarginWidth: 4 })
  const node = nvlTargets.nodes[0]?.data
  const rel = nvlTargets.relationships[0]?.data
  const cluster = nvlTargets.clusters[0]?.data
})
```

`HitTargetNode` / `HitTargetRelationship` carry `data`, `pointerCoordinates`, `distance` and `insideNode` (nodes). `HitTargetCluster` carries `data`, `pointerCoordinates` and the convex `hull`. Default `hitNodeMarginWidth` is `0`, so widen it when clicks near the edge miss. *types*

## Image export

Call `saveToFile({ filename, backgroundColor })`, `saveToSvg(...)` or `getImageDataUrl(...)` from `onLayoutDone`; before that the positions are still settling and the PNG can be blank. *types, runtime*
