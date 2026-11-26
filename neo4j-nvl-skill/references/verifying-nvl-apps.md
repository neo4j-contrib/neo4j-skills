# Verifying NVL apps

When you need this: you want to check from a test, a script or a headless browser that the graph rendered, the layout finished, or nodes are where you expect.

Verification tags: **source**, **types**, **runtime** (see `SKILL.md`).

## Window hooks

Every NVL instance registers these on `window` (declared in `nvl-window-functions.d.ts`). They are read-only test hooks; `instanceId` is the `nvlOptions.instanceId` you gave (default `'default'`). With several instances and no id, the most recently created one answers. *source*

| Hook | Returns |
|---|---|
| `__Nvl_dumpNodes(instanceId?)` | `NodeWithClientPosition[]`: every node with `x`, `y` and `clientPosition` |
| `__Nvl_dumpRelationships(instanceId?)` | `Relationship[]` |
| `__Nvl_getNodesOnScreen(instanceId?)` | `{ nodes, rels }` currently inside the viewport |
| `__Nvl_getZoomLevel(instanceId?)` | current zoom |
| `__Nvl_registerDoneCallback(cb, instanceId)` | registers `cb` for `onLayoutDone`; note the argument order |

Playwright example (the pattern used by this repository's build-tool tests): *source*

```typescript
await expect.poll(() => page.evaluate('window.__Nvl_dumpNodes !== undefined')).toBeTruthy()
await expect.poll(() => page.evaluate(() => window.__Nvl_dumpNodes().length)).toBe(42)
await page.evaluate(() => new Promise<void>((resolve) => window.__Nvl_registerDoneCallback(resolve, 'default')))
```

## Detecting a settled layout

- Preferred: `onLayoutDone` (or `__Nvl_registerDoneCallback`).
- Alternative: poll `__Nvl_dumpNodes()` and compare positions between two polls.
- `onLayoutComputing(false)` fires when a computation ends; the force-directed layout may compute again after interactions.

## What a screenshot can and cannot show

- The WebGL canvas is not inspectable through the DOM; pixels are the only evidence. Captions are absent with WebGL (see [labels-and-overlays](labels-and-overlays.md)), so a text-based check needs the Canvas renderer or `html` overlays.
- `getImageDataUrl()` returns the main canvas as PNG for in-process comparisons. *types*

## Headless Chrome and WebGL2

Headless Chrome uses software GL by default. The force-directed GPU simulation then runs so slowly that it looks hung. Launch with hardware GL: *runtime*

```
--use-angle=gl --use-gl=angle --enable-gpu --ignore-gpu-blocklist --disable-gpu-sandbox
```

Playwright: pass them in `launchOptions.args`. Allow long timeouts for the first layout. If no GPU is available, set `disableWebGL: true` in the test build so NVL uses the Canvas renderer and CPU layouts.

## Checklist

- Wait for `__Nvl_dumpNodes` to exist, then for the expected node count, then for `onLayoutDone`.
- Set `instanceId` when a page has more than one graph.
- Set `disableTelemetry: true` in test builds.
