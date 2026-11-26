# Vite and other bundlers

When you need this: a layout never finishes in development, the console mentions a worker script, or you set up a new project.

Verification tags: **source**, **types**, **runtime** (see `SKILL.md`).

## What runs in a worker

Only the **hierarchical** layout uses a worker: a `SharedWorker` (`type: 'module'`, name `HierarchicalLayout`) created by `@neo4j-nvl/layout-workers` with `new URL('./HierarchicalLayout.worker.js', import.meta.url)`. The worker imports the CommonJS package `bin-pack`. Force-directed, circular, grid, free and d3Force run on the main thread or the GPU. *source*

If the worker constructor throws, NVL logs a warning and falls back to the synchronous implementation automatically. A worker that is created but fails to **load** does not throw, so there is no fallback and the layout never completes. *source*

## Vite dev server

With Vite 7.3 the hierarchical layout works in `vite` dev without configuration: Vite discovers `bin-pack` from the worker graph and pre-bundles it. *runtime*

**Symptom (reported with older Vite versions and npm-installed packages, not reproduced in this repository):** switching to `hierarchical` fires `onLayoutComputing(true)` and nothing else. The page console is clean; the worker's console (DevTools → Sources → Threads, or `chrome://inspect/#workers`) shows "Failed to fetch a worker script" or a CJS resolution error. `vite build` + `vite preview` works.

**Cause:** Vite pre-bundles CommonJS dependencies found from the main module graph. If the worker graph is not scanned, `bin-pack` reaches the worker un-bundled.

**Fix:**

```typescript
// vite.config.ts
import { defineConfig } from 'vite'

export default defineConfig({
  optimizeDeps: { include: ['bin-pack'] }
})
```

Restart `vite` after editing `optimizeDeps`; delete `node_modules/.vite` if the change does not take.

With pnpm or other strict hoisting, `bin-pack` is a transitive dependency and not resolvable from the app root. Use Vite's nested syntax (documented by Vite, not exercised in this repository):

```typescript
optimizeDeps: {
  include: ['@neo4j-nvl/base > @neo4j-nvl/layout-workers > bin-pack']
}
```

## Webpack

Webpack 5 handles `new SharedWorker(new URL(..., import.meta.url))` natively; no configuration is needed. The repository's build-tool tests cover webpack and Vite production builds. *source*

## Other bundlers

Not tested in this repository. Check that the bundler supports `new URL(..., import.meta.url)` in `SharedWorker` constructors and bundles CJS dependencies into worker chunks. If it does not, use `disableWebWorkers`.

## `disableWebWorkers`

```javascript
new NVL(container, nodes, rels, { disableWebWorkers: true })
```

Runs the hierarchical layout synchronously on the main thread: same result, blocks the UI for large graphs. Use it when workers are blocked (CSP `worker-src 'none'`, sandboxed iframes) or a bundler cannot be configured. For the Vite dev case prefer `optimizeDeps`. *types, source*

## Telling a worker failure from a slow layout

- `onLayoutComputing(true)` followed by nothing for more than a few seconds on a small graph is a failure, not slowness.
- `window.__Nvl_registerDoneCallback(cb)` never fires (see [verifying-nvl-apps](verifying-nvl-apps.md)).
- Switch to `disableWebWorkers: true`: if the layout now completes, the worker is the problem.
