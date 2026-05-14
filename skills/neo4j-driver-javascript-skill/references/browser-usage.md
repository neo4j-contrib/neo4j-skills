# Browser / WebSocket Usage — Neo4j JavaScript Driver

## URI Scheme

Browser uses **WebSockets**, not TCP. Use `neo4j+s://` (WSS) or `neo4j://` (WS).

```javascript
// ❌ bolt:// uses TCP — not supported in browsers
neo4j.driver('bolt://localhost:7687', auth)

// ✅ neo4j+s:// → WSS (TLS) — Aura and production
neo4j.driver('neo4j+s://xxx.databases.neo4j.io', auth)

// ✅ neo4j:// → WS (plaintext) — local dev without TLS
neo4j.driver('neo4j://localhost:7687', auth)
```

## Bundling

`neo4j-driver` works in browsers bundled with webpack, Vite, or Rollup. No separate browser package needed.

## CORS

Bolt/WebSocket connections bypass CORS — not HTTP. Browser connects directly to Neo4j's Bolt port (default 7687). Ensure Neo4j allows WebSocket connections from your origin.

## Security

**Never embed production credentials in client-side JavaScript.** Proxy through a backend API.
