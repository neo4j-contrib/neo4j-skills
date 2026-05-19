# NVL — API Surface Reference

Source: `@neo4j-nvl/base@1.1`, `@neo4j-nvl/interaction-handlers@1.1`, `@neo4j-nvl/react@1.1`.

## Packages

| Package | Main export | Notes |
|---|---|---|
| `@neo4j-nvl/base` | `NVL` (also default), types, `nvlResultTransformer`, layout constants | Framework-agnostic core |
| `@neo4j-nvl/interaction-handlers` | `ZoomInteraction`, `PanInteraction`, `ClickInteraction`, `HoverInteraction`, `DragNodeInteraction`, `BoxSelectInteraction`, `LassoInteraction`, `KeyboardInteraction` | Compose onto an `NVL` instance |
| `@neo4j-nvl/react` | `InteractiveNvlWrapper`, `BasicNvlWrapper`, `StaticPictureWrapper` | React 19 |
| `@neo4j-nvl/layout-workers` | (transitive) | Force-directed + hierarchical workers |

---

## `NVL` Class

### Constructor

```typescript
new NVL(
  frame: HTMLElement,
  nvlNodes?: Node[],                  // default []
  nvlRels?:  Relationship[],          // default []
  options?:  NvlOptions,              // default {}
  callbacks?: ExternalCallbacks       // default {}
)
```

### Element CRUD

| Method | Signature | Purpose |
|---|---|---|
| `addAndUpdateElementsInGraph` | `(nodes: Node[] \| PartialNode[], rels: Relationship[] \| PartialRelationship[]) => void` | Insert new; update existing by id |
| `addElementsToGraph` | `(nodes: Node[], rels: Relationship[]) => void` | Insert only |
| `updateElementsInGraph` | `(nodes: PartialNode[], rels: PartialRelationship[]) => void` | Update existing only; ignores unknown ids |
| `removeNodesWithIds` | `(ids: string[]) => void` | Remove nodes + adjacent relationships |
| `removeRelationshipsWithIds` | `(ids: string[]) => void` | Remove relationships |

### Element Read

| Method | Signature |
|---|---|
| `getNodes` | `() => Node[]` |
| `getRelationships` | `() => Relationship[]` |
| `getNodeById` | `(id: string) => Node` |
| `getRelationshipById` | `(id: string) => Relationship` |
| `getPositionById` | `(id: string) => Node` |
| `getNodesOnScreen` | `() => { nodes: Node[]; rels: Relationship[] }` |
| `getNodePositions` | `() => (Node & Point)[]` |
| `setNodePositions` | `(data: Node[], updateLayout?: boolean) => void` |
| `getSelectedNodes` | `() => (Node & Point)[]` |
| `getSelectedRelationships` | `() => Relationship[]` |
| `deselectAll` | `() => void` |

### Viewport

| Method | Signature |
|---|---|
| `fit` | `(nodeIds: string[], zoomOptions?: ZoomOptions) => void` (empty array = fit all) |
| `resetZoom` | `() => void` |
| `setZoom` | `(zoom: number) => void` |
| `setPan` | `(panX: number, panY: number) => void` |
| `setZoomAndPan` | `(zoom: number, panX: number, panY: number) => void` |
| `getScale` | `() => number` |
| `getPan` | `() => Point` |
| `getZoomLimits` | `() => { minZoom: number; maxZoom: number }` |

### Layout / Renderer / Pin

| Method | Signature |
|---|---|
| `setLayout` | `(layout: Layout) => void` |
| `setLayoutOptions` | `(options: LayoutOptions) => void` |
| `isLayoutMoving` | `() => boolean` |
| `setRenderer` | `(renderer: 'canvas' \| 'webgl') => void` |
| `setDisableWebGL` | `(disabled?: boolean) => void` |
| `pinNode` | `(nodeId: string) => void` |
| `unPinNode` | `(nodeIds: string[]) => void` |

### Export / Save

| Method | Signature |
|---|---|
| `saveToFile` | `(opts?: { filename?: string; backgroundColor?: string }) => void` (PNG of current view) |
| `saveFullGraphToLargeFile` | `(opts?: { filename?: string; backgroundColor?: string }) => void` (PNG of full graph) |
| `saveToSvg` | `(opts?: { filename?: string; backgroundColor?: string }) => void` (experimental) |
| `getImageDataUrl` | `(opts?: { backgroundColor?: string }) => string` |
| `getSvgDataUrl` | `(opts?: { backgroundColor?: string }) => Promise<string>` |

### Hit Testing

```typescript
getHits(
  evt: MouseEvent,
  targets?: ('node' | 'relationship')[],     // default ['node','relationship']
  hitOptions?: { hitNodeMarginWidth: number } // default 0
): NvlMouseEvent
```

### Lifecycle / Misc

| Method | Signature |
|---|---|
| `getCurrentOptions` | `() => NvlOptions` |
| `getContainer` | `() => HTMLElement` |
| `restart` | `(options?: NvlOptions, retainPositions?: boolean) => void` |
| `destroy` | `() => void` |

---

## Core Types

### `Node`

| Field | Type | Notes |
|---|---|---|
| `id` | `string` | Required; unique across nodes AND relationships |
| `caption` | `string` | Single caption (superseded by `captions`) |
| `captions` | `StyledCaption[]` | Multi-line captions with styles |
| `captionSize` | `number` | Text size |
| `captionAlign` | `'top' \| 'bottom' \| 'center'` | |
| `color` | `string` | Fill color |
| `size` | `number` | Radius |
| `pinned` | `boolean` | Excluded from layout forces |
| `x` / `y` | `number` | Position |
| `selected` | `boolean` | |
| `hovered` | `boolean` | |
| `activated` | `boolean` | |
| `disabled` | `boolean` | |
| `icon` | `string` | URL to image inside node |
| `html` | `HTMLElement` | DOM overlay |
| `overlayIcon` | `{ url: string; position?: number[]; size?: number }` | |

### `Relationship`

| Field | Type | Notes |
|---|---|---|
| `id` | `string` | Required; unique across nodes AND relationships |
| `from` | `string` | Source node id |
| `to` | `string` | Target node id |
| `type` | `string` | Relationship type label |
| `width` | `number` | |
| `color` | `string` | |
| `caption` / `captions` / `captionSize` / `captionAlign` | (same as Node) | |
| `captionHtml` | `HTMLElement` | DOM overlay on caption |
| `selected` / `hovered` / `disabled` | `boolean` | |

### Partial types

```typescript
type PartialNode         = Partial<Node>         & { id: string }
type PartialRelationship = Partial<Relationship> & { id: string }
```

---

## `NvlOptions`

| Field | Type | Default | Notes |
|---|---|---|---|
| `instanceId` | `string` | — | |
| `layout` | `Layout` | `'forceDirected'` | See Layout enum below |
| `layoutOptions` | `LayoutOptions` | — | Layout-specific |
| `layoutTimeLimit` | `number` | — | ms cap for layout iteration |
| `minZoom` | `number` | `0.075` | |
| `maxZoom` | `number` | `10` | |
| `allowDynamicMinZoom` | `boolean` | `true` | Permits going below `minZoom` to fit |
| `initialZoom` | `number` | — | |
| `panX` / `panY` | `number` | — | |
| `renderer` | `'canvas' \| 'webgl'` | `'canvas'` | |
| `disableWebGL` | `boolean` | `false` | Force-off WebGL even if requested |
| `disableWebWorkers` | `boolean` | `false` | Use synchronous layout fallback |
| `disableTelemetry` | `boolean` | `false` | |
| `disableAria` | `boolean` | `false` | |
| `minimapContainer` | `HTMLElement \| null` | — | |
| `styling` | `StylingOptions` | — | |
| `callbacks` | `ExternalCallbacks` | — | (also passable as 5th constructor arg) |
| `logging` | `{ level: LogLevelDesc }` | — | |

### `StylingOptions`

| Field | Type |
|---|---|
| `defaultNodeColor` | `string` |
| `defaultRelationshipColor` | `string` |
| `nodeDefaultBorderColor` | `string` |
| `selectedBorderColor` | `string` |
| `selectedInnerBorderColor` | `string` |
| `dropShadowColor` | `string` |
| `disabledItemColor` | `string` |
| `disabledItemFontColor` | `string` |
| `minimapViewportBoxColor` | `string` |

### Layout enum + constants

```typescript
type Layout = 'forceDirected' | 'hierarchical' | 'grid' | 'free' | 'd3Force' | 'circular'

// Exported constants (string literals):
ForceDirectedLayoutType   // 'forceDirected'
HierarchicalLayoutType    // 'hierarchical'
GridLayoutType            // 'grid'
FreeLayoutType            // 'free'
d3ForceLayoutType         // 'd3Force'
CircularLayoutType        // 'circular'
```

### `LayoutOptions` union

```typescript
type LayoutOptions = ForceDirectedOptions | HierarchicalOptions | CircularOptions

interface ForceDirectedOptions {
  intelWorkaround?: boolean   // workaround for Intel GPU shader issues; requires restart
  enableCytoscape?: boolean   // deprecated; auto-cose for small graphs
}

interface HierarchicalOptions {
  direction?: 'up' | 'down' | 'left' | 'right'
  packing?:   'bin' | 'stack'
}

interface CircularOptions {
  sortFunction?: (nodes: Node[]) => Node[]
}
```

### `ZoomOptions`

| Field | Type | Purpose |
|---|---|---|
| `noPan` | `boolean` | Zoom without changing pan |
| `outOnly` | `boolean` | Only zoom out to fit |
| `minZoom` | `number` | Override for this op |
| `maxZoom` | `number` | Override for this op |
| `animated` | `boolean` | Animate transition |

### Renderer constants

```typescript
type Renderer = 'webgl' | 'canvas'

WebGLRendererType   // 'webgl'
CanvasRendererType  // 'canvas'
```

### `StyledCaption`

```typescript
type StyledCaption = {
  styles: string[]   // e.g. ['bold','italic']
  value:  string
  key:    string
}
```

### `Point`

```typescript
type Point = { x: number; y: number }
```

---

## `ExternalCallbacks`

| Callback | Signature |
|---|---|
| `onInitialization` | `() => void` |
| `onLayoutDone` | `() => void` |
| `onLayoutStep` | `(nodes: Node[]) => void` |
| `onLayoutComputing` | `(isComputing: boolean) => void` |
| `onError` | `(error: Error) => void` |
| `onWebGLContextLost` | `(event: WebGLContextEvent) => void` |
| `onZoomTransitionDone` | `() => void` |
| `restart` | `() => void` |

---

## Hit Testing Types

```typescript
interface NvlMouseEvent extends MouseEvent {
  nvlTargets: HitTargets
}

type HitTargets = {
  nodes:         HitTargetNode[]
  relationships: HitTargetRelationship[]
}

interface HitTargetNode {
  data:               Node
  targetCoordinates:  Point
  pointerCoordinates: Point
  distanceVector:     Point
  distance:           number
  insideNode:         boolean
}

interface HitTargetRelationship {
  data:                   Relationship
  fromTargetCoordinates:  Point
  toTargetCoordinates:    Point
  pointerCoordinates:     Point
  distance:               number
}
```

---

## `nvlResultTransformer`

```typescript
import type { ResultTransformer, EagerResult } from 'neo4j-driver'

const nvlResultTransformer: ResultTransformer<
  EagerResult,
  { nodes: Node[]; relationships: Relationship[] }
>
```

Usage: `driver.executeQuery(cypher, params, { database: 'neo4j', resultTransformer: nvlResultTransformer })`. Returns deduplicated `{ nodes, relationships }`.

---

## Named Exports — `@neo4j-nvl/base`

```typescript
// values
export {
  NVL,                         // also default export
  nvlResultTransformer,
  colorMapperFunctions,
  CompatibilityError,
  drawCircleBand,
  getZoomTargetForNodePositions,
  ForceDirectedLayoutType,
  HierarchicalLayoutType,
  GridLayoutType,
  FreeLayoutType,
  d3ForceLayoutType,
  CircularLayoutType
}

// types
export type {
  NvlOptions, Renderer, Node, Relationship, PartialNode, PartialRelationship,
  Layout, LayoutOptions, ForceDirectedOptions, HierarchicalOptions, CircularOptions,
  ExternalCallbacks, HitTargets, HitTargetNode, HitTargetRelationship,
  Point, NvlMouseEvent, ZoomOptions, StyledCaption,
  WebGLRendererType, CanvasRendererType
}
```

---

## Interaction Handlers

All extend `BaseInteraction<P>`:

```typescript
class BaseInteraction<P> {
  constructor(nvl: NVL, options?: P)
  updateCallback(name: string, callback: ((...args: unknown[]) => void) | boolean): void
  removeCallback(name: string): void
  destroy(): void
  readonly currentOptions: P
}
```

Callback semantics: `function` = enable + invoke; `true` = enable as no-op; omitted/removed = disable.

### `ZoomInteraction`

```typescript
new ZoomInteraction(nvl, options?: { controlledZoom?: boolean })
```

| Event | Signature |
|---|---|
| `onZoom` | `(zoomLevel: number, event: WheelEvent) => void` |
| `onZoomAndPan` | `(zoomLevel: number, panX: number, panY: number, event: WheelEvent) => void` |

### `PanInteraction`

```typescript
new PanInteraction(nvl, options?: { excludeNodeMargin?: boolean; controlledPan?: boolean })
panInteraction.updateTargets(targets: ('node'|'relationship')[], excludeNodeMargin: boolean): void
```

| Event | Signature |
|---|---|
| `onPan` | `(panning: { x: number; y: number }, event: MouseEvent) => void` |

### `ClickInteraction`

```typescript
new ClickInteraction(nvl, options?: { selectOnClick?: boolean })
```

| Event | Signature |
|---|---|
| `onNodeClick` | `(node: Node, hits: HitTargets, event: MouseEvent) => void` |
| `onRelationshipClick` | `(rel: Relationship, hits: HitTargets, event: MouseEvent) => void` |
| `onCanvasClick` | `(event: MouseEvent) => void` |
| `onNodeDoubleClick` | `(node, hits, event) => void` |
| `onRelationshipDoubleClick` | `(rel, hits, event) => void` |
| `onCanvasDoubleClick` | `(event) => void` |
| `onNodeRightClick` | `(node, hits, event) => void` |
| `onRelationshipRightClick` | `(rel, hits, event) => void` |
| `onCanvasRightClick` | `(event) => void` |

### `HoverInteraction`

```typescript
new HoverInteraction(nvl, options?: { drawShadowOnHover?: boolean })
```

| Event | Signature |
|---|---|
| `onHover` | `(element: Node \| Relationship \| undefined, hits: HitTargets, event: MouseEvent) => void` |

### `DragNodeInteraction`

```typescript
new DragNodeInteraction(nvl)
```

| Event | Signature |
|---|---|
| `onDragStart` | `(nodes: Node[], event: MouseEvent) => void` |
| `onDrag` | `(nodes: Node[], event: MouseEvent) => void` |
| `onDragEnd` | `(nodes: Node[], event: MouseEvent) => void` |

### `BoxSelectInteraction`

```typescript
new BoxSelectInteraction(nvl, options?: { selectOnRelease?: boolean })
```

| Event | Signature |
|---|---|
| `onBoxStarted` | `(event: MouseEvent) => void` |
| `onBoxSelect` | `(selection: { nodes: Node[]; rels: Relationship[] }, event: MouseEvent) => void` |

### `LassoInteraction`

```typescript
new LassoInteraction(nvl, options?: { selectOnRelease?: boolean })
```

| Event | Signature |
|---|---|
| `onLassoStarted` | `(event: MouseEvent) => void` |
| `onLassoSelect` | `(selection: { nodes: Node[]; rels: Relationship[] }, event: MouseEvent) => void` |

### `KeyboardInteraction`

```typescript
new KeyboardInteraction(nvl, options?: {
  enterGraphKey?:      string[]
  navigateForwardKey?: string[]
  navigateBackwardKey?:string[]
  exitGraphKey?:       string[]
  contextMenuKey?:     string[]
})
keyboard.getFocused(): Node | Relationship | undefined
```

| Event | Signature |
|---|---|
| `onKeyDown` | `(event: KeyboardEvent, focused?: Node \| Relationship) => void` |
| `onKeyUp` | `(event: KeyboardEvent, focused?: Node \| Relationship) => void` |
| `onNodeFocus` / `onNodeBlur` | `(node: Node, event: KeyboardEvent) => void` |
| `onRelationshipFocus` / `onRelationshipBlur` | `(rel: Relationship, event: KeyboardEvent) => void` |
| `onCanvasFocus` / `onCanvasBlur` | `(event: FocusEvent) => void` |
| `onContextMenu` | `(element: Node \| Relationship \| undefined, event: KeyboardEvent) => void` |

---

## React Components

### `<InteractiveNvlWrapper>`

| Prop | Type | Notes |
|---|---|---|
| `nodes` | `Node[]` | |
| `rels` | `Relationship[]` | |
| `layout` | `Layout` | |
| `layoutOptions` | `LayoutOptions` | |
| `nvlOptions` | `NvlOptions` | |
| `nvlCallbacks` | `ExternalCallbacks` | |
| `positions` | `Node[]` | |
| `zoom` | `number` | |
| `pan` | `{ x: number; y: number }` | |
| `mouseEventCallbacks` | `MouseEventCallbacks` | See below |
| `keyboardEventCallbacks` | `KeyboardEventCallbacks` | See below |
| `interactionOptions` | `InteractionOptions` | Defaults: `{ selectOnClick: false, drawShadowOnHover: true, selectOnRelease: false, excludeNodeMargin: true }` |
| `onInitializationError` | `(error: unknown) => void` | |
| `ref` | `Ref<NVL>` | Underlying NVL instance |
| (plus `HTMLProps<HTMLDivElement>`) | | |

### `<BasicNvlWrapper>`

Same prop set EXCEPT no `mouseEventCallbacks` / `keyboardEventCallbacks` / `interactionOptions`. `ref` resolves to `IncludeMethods<NVL>` — exposes all NVL public methods.

### `<StaticPictureWrapper>`

| Prop | Type | Default |
|---|---|---|
| `nodes` | `Node[]` | — |
| `rels` | `Relationship[]` | — |
| `nvlOptions` | `NvlOptions` | — |
| `width` | `number` | `500` |
| `height` | `number` | `500` |
| `format` | `'png' \| 'svg'` | `'png'` |

Renders an ephemeral NVL, fits viewport, captures, destroys. Returns `<img />`.

### `MouseEventCallbacks`

Union of all handler callbacks. Each value can be a function (with the signature above), `true` (enabled, no callback), or omitted / `false` (disabled):

```
onNodeClick, onRelationshipClick, onCanvasClick,
onNodeDoubleClick, onRelationshipDoubleClick, onCanvasDoubleClick,
onNodeRightClick, onRelationshipRightClick, onCanvasRightClick,
onHover,
onPan, onZoom, onZoomAndPan,
onDragStart, onDrag, onDragEnd,
onBoxStarted, onBoxSelect,
onLassoStarted, onLassoSelect,
onHoverNodeMargin, onDrawStarted, onDrawEnded
```

### `KeyboardEventCallbacks`

```
onKeyDown, onKeyUp,
onNodeFocus, onNodeBlur,
onRelationshipFocus, onRelationshipBlur,
onCanvasFocus, onCanvasBlur,
onContextMenu
```

### `InteractionOptions`

Merged union of every handler's options:

```
{ selectOnClick?, drawShadowOnHover?, selectOnRelease?, excludeNodeMargin?, controlledZoom?,
  controlledPan?, enterGraphKey?, navigateForwardKey?, navigateBackwardKey?, exitGraphKey?,
  contextMenuKey?, ghostGraphStyling? }
```
