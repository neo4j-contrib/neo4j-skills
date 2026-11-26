# React wrappers

When you need this: you use `<InteractiveNvlWrapper>` or `<BasicNvlWrapper>` from `@neo4j-nvl/react` and something does not react to a prop change, a callback sees stale state, or an interaction does not start.

Verification tags: **source** = `packages/react/src` in the NVL repository, **types** = shipped `.d.ts`, **runtime** = observed in a running app.

## Which wrapper

- `<InteractiveNvlWrapper>`: `<BasicNvlWrapper>` plus every interaction handler, toggled through `mouseEventCallbacks` and `keyboardEventCallbacks`.
- `<BasicNvlWrapper>`: NVL only. Use it when you wire interactions yourself through the `ref`.

Both forward a `ref` to the `NVL` instance (`useRef<NVL>(null)`) and pass unknown props to the container `<div>`. The container is `height: 100%`, so the **parent** needs an explicit height. *source*

## `mouseEventCallbacks` → handler

A key set to a function enables the handler and registers the callback; `true` enables the handler with no callback; `false` destroys the handler; omitted means off. *source*

| Handler | Keys |
|---|---|
| Hover | `onHover` |
| Click | `onNodeClick`, `onRelationshipClick`, `onCanvasClick`, `onClusterClick`, and the `...DoubleClick` / `...RightClick` variants |
| Pan | `onPan` |
| Zoom (wheel) | `onZoomAndPan` |
| Drag nodes | `onDrag`, `onDragStart`, `onDragEnd` |
| Draw | `onHoverNodeMargin`, `onDrawStarted`, `onDrawEnded` |
| Box select | `onBoxStarted`, `onBoxSelect` |
| Lasso | `onLassoStarted`, `onLassoSelect` |
| Keyboard (`keyboardEventCallbacks`) | `onKeyDown`, `onKeyUp`, `onNodeFocus`, `onNodeBlur` |

There is no `onZoom` key. `{ onZoom: true }` is ignored and wheel zoom stays off. *source*

Interaction callbacks are re-registered whenever the function identity changes, so they are **not** subject to the stale-closure problem below. *source*

## `nvlCallbacks` are captured once

`BasicNvlWrapper` passes `nvlCallbacks` to the `NVL` constructor and never updates them. A callback that closes over state sees the state from the first render. *source*

```tsx
const selectedRef = useRef(selected)
selectedRef.current = selected

const nvlCallbacks = useMemo(() => ({
  onLayoutDone: () => console.log('layout done, selected:', selectedRef.current)
}), [])
```

## Which `nvlOptions` update after creation

Only these are watched by effects: `layout` (`setLayout`), `layoutOptions` (deep-compared, `setLayoutOptions`), `renderer` (`setRenderer`), `disableWebGL` (`setDisableWebGL`). Everything else (`styling`, `minZoom`, `initialZoom`, `disableTelemetry`, `disableWebWorkers`, ...) is read at construction. *source*

Separate props with live effects: `positions` (`setNodePositions`), `zoom` and `pan` (`setZoom` / `setPan` / `setZoomAndPan`). *source*

To change a creation-time option, call `nvlRef.current.restart(newOptions, true)` or remount the wrapper with a `key`.

## `nodes` / `rels` diffing

On every render the wrapper diffs the new arrays against the previous ones by `id`, then calls `addAndUpdateElementsInGraph` for added and changed elements and `removeNodesWithIds` / `removeRelationshipsWithIds` for removed ones. *source*

- Only keys whose value changed are sent, so updates are partial. A key set to `undefined` is sent; a key that is omitted is not. To un-pin, send `pinned: false`: the force-directed layout ignores `pinned: undefined`. *source*
- Never set `x` / `y` on `nodes`; they do not position anything. Use the `positions` prop (calls `setNodePositions` without `updateLayout`) or `setNodePositions` via the ref (see [layouts-and-positions](layouts-and-positions.md)). *source*
- `pinned` does apply through the diff. *runtime*
- Keep the arrays referentially stable between renders (`useMemo`) or the diff runs on every render.

## `minimapContainer` must exist first

If `nvlOptions.minimapContainer` is present, NVL is not created until it is non-null. With a plain `useRef` the element is `null` on the first render and NVL never starts; hold the element in state via a callback ref. *source*

```tsx
const [minimapEl, setMinimapEl] = useState<HTMLDivElement | null>(null)
const nvlOptions = useMemo(() => ({ minimapContainer: minimapEl }), [minimapEl])

<div ref={setMinimapEl} style={{ width: 200, height: 150 }} />
<InteractiveNvlWrapper nvlOptions={nvlOptions} ... />
```

## `interactionOptions` replaces the defaults

The default is `{ selectOnClick: false, drawShadowOnHover: true, selectOnRelease: false, excludeNodeMargin: true }`. Passing the prop replaces this object, so `interactionOptions={{ selectOnClick: true }}` turns the hover shadow off. Pass every option you want. *source*

Keep the object stable (`useMemo`); a new object each render re-runs every interaction effect.

## Selection toggles twice / handlers duplicated

Flipping `selectOnClick` or other `interactionOptions` across renders, or registering your own `container.addEventListener('click')` next to the wrapper's `ClickInteraction`, produces double handling. Set the options once and use the wrapper's callbacks.

## Many `<StaticPictureWrapper>`s at once

Each instance holds two WebGL contexts until its image is captured, and browsers allow only about 16 per page. Around eight pictures rendering at the same time hit that limit ("Too many active WebGL contexts"). For galleries or lists, pass `nvlOptions={{ disableWebGL: true }}`, or mount the pictures in batches. *source, runtime*

## Teardown

The wrappers call `nvl.destroy()` on unmount and destroy their handlers. Only manual `new NVL(...)` in a `useEffect` needs an explicit `return () => nvl.destroy()`.
