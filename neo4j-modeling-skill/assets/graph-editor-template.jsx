import { useState, useRef, useCallback, useEffect } from "react";

const COLORS = [
  "#4C8BF5", "#E5484D", "#30A46C", "#E38627", "#8B5CF6",
  "#06B6D4", "#EC4899", "#F59E0B", "#6366F1", "#14B8A6",
];

const initialGraph = {
  nodes: [
    { id: "n0", position: { x: 300, y: 250 }, caption: "Person", labels: ["Person"], properties: { name: "string", age: "integer" }, style: { color: COLORS[0], radius: 50 } },
    { id: "n1", position: { x: 600, y: 250 }, caption: "Movie", labels: ["Movie"], properties: { title: "string", released: "integer" }, style: { color: COLORS[1], radius: 50 } },
  ],
  relationships: [
    { id: "r0", type: "ACTED_IN", fromId: "n0", toId: "n1", properties: { role: "string" } },
  ],
  style: {},
};

function uid() { return "n" + Math.random().toString(36).slice(2, 8); }
function rid() { return "r" + Math.random().toString(36).slice(2, 8); }
function vec(a, b) { return { x: b.x - a.x, y: b.y - a.y }; }
function len(v) { return Math.sqrt(v.x * v.x + v.y * v.y); }
function norm(v) { const l = len(v) || 1; return { x: v.x / l, y: v.y / l }; }

function getEdgePoints(from, to, fromR, toR) {
  const d = vec(from, to);
  const n = norm(d);
  return { x1: from.x + n.x * fromR, y1: from.y + n.y * fromR, x2: to.x - n.x * toR, y2: to.y - n.y * toR };
}

// Self-loop that fans out by index so multiple self-rels don't overlap.
// The loop is guaranteed to sit OUTSIDE the node: each control point starts
// on the node boundary and is pushed outward along the centerAngle direction
// (plus a small perpendicular component to give the loop width), so the
// Bezier curve bulges away from the node and never re-enters it.
function getSelfLoopPath(cx, cy, r, index = 0, total = 1) {
  const baseAngle = -Math.PI / 2; // top of node
  const spread = Math.PI * 0.55; // fan between loops when there are multiple
  const fanOffset = total > 1 ? (index - (total - 1) / 2) * spread : 0;
  const centerAngle = baseAngle + fanOffset;

  // Opening on the node where the loop starts and ends
  const halfArc = Math.PI * 0.16;
  const startAngle = centerAngle - halfArc;
  const endAngle = centerAngle + halfArc;

  // How far the loop bulges outward from the node surface. Grows per sibling
  // so stacked loops remain visually distinguishable.
  const reach = r * 1.7 + index * 18;

  const sx = cx + r * Math.cos(startAngle);
  const sy = cy + r * Math.sin(startAngle);
  const ex = cx + r * Math.cos(endAngle);
  const ey = cy + r * Math.sin(endAngle);

  // Unit vectors: radial = direction the loop bulges; tangent = perpendicular
  // spreading for the teardrop shape.
  const rad = { x: Math.cos(centerAngle), y: Math.sin(centerAngle) };
  const tan = { x: -rad.y, y: rad.x };
  const sideSpread = r * 0.9;

  // Control points are offset from each endpoint in the OUTWARD radial
  // direction (never inward toward the node). A tangential component spreads
  // the two controls apart so the curve forms a loop rather than a spike.
  const cpx1 = sx + rad.x * reach - tan.x * sideSpread;
  const cpy1 = sy + rad.y * reach - tan.y * sideSpread;
  const cpx2 = ex + rad.x * reach + tan.x * sideSpread;
  const cpy2 = ey + rad.y * reach + tan.y * sideSpread;

  // Label sits at the outer apex of the loop (t = 0.5 on the Bezier).
  // For a symmetric cubic, the midpoint is at the average of the four points,
  // biased by the Bernstein weights (1, 3, 3, 1) / 8 = (1/8, 3/8, 3/8, 1/8).
  const midX = (sx + 3 * cpx1 + 3 * cpx2 + ex) / 8;
  const midY = (sy + 3 * cpy1 + 3 * cpy2 + ey) / 8;

  return { path: `M ${sx} ${sy} C ${cpx1} ${cpy1}, ${cpx2} ${cpy2}, ${ex} ${ey}`, midX, midY };
}

// Export helpers
// Default style block emitted on export. arrows.app preserves these on
// import, so paste-into-arrows.app produces a sensible starting look. Kept
// in sync with inject.py's ARROWS_DEFAULT_STYLE — change them together.
const ARROWS_DEFAULT_STYLE = {
  "font-family": "sans-serif",
  "background-color": "#ffffff",
  "background-image": "",
  "background-size": "100%",
  "node-color": "#ffffff",
  "border-width": 4,
  "border-color": "#000000",
  "radius": 50,
  "node-padding": 5,
  "node-margin": 2,
  "outside-position": "auto",
  "node-icon-image": "",
  "node-background-image": "",
  "icon-position": "inside",
  "icon-size": 64,
  "caption-position": "inside",
  "caption-max-width": 200,
  "caption-color": "#000000",
  "caption-font-size": 50,
  "caption-font-weight": "normal",
  "label-position": "inside",
  "label-display": "pill",
  "label-color": "#000000",
  "label-background-color": "#ffffff",
  "label-border-color": "#000000",
  "label-border-width": 4,
  "label-font-size": 40,
  "label-padding": 5,
  "label-margin": 4,
  "directionality": "directed",
  "detail-position": "inline",
  "detail-orientation": "parallel",
  "arrow-width": 5,
  "arrow-color": "#000000",
  "margin-start": 5,
  "margin-end": 5,
  "margin-peer": 20,
  "attachment-start": "normal",
  "attachment-end": "normal",
  "relationship-icon-image": "",
  "type-color": "#000000",
  "type-background-color": "#ffffff",
  "type-border-color": "#000000",
  "type-border-width": 0,
  "type-font-size": 16,
  "type-padding": 5,
  "property-position": "outside",
  "property-alignment": "colon",
  "property-color": "#000000",
  "property-font-size": 16,
  "property-font-weight": "normal",
};

function toArrowsJSON(graph) {
  // Match arrows.app's native export shape: flat (no `graph` wrapper),
  // kebab-case style keys, and caption="" when it equals labels[0] (the
  // common case — arrows.app uses labels[0] as the display text). We emit
  // an explicit caption only when it diverges from labels[0], preserving
  // any deliberate user choice.
  return JSON.stringify({
    style: { ...ARROWS_DEFAULT_STYLE },
    nodes: graph.nodes.map(n => {
      const labels = n.labels || [];
      const primary = labels[0] || "";
      const caption = n.caption === primary ? "" : (n.caption || "");
      return {
        id: n.id,
        position: n.position,
        caption,
        style: {
          "node-color": n.style?.color || "#4C8BF5",
          "radius": n.style?.radius || 50,
        },
        labels: [...labels],
        properties: { ...(n.properties || {}) },
      };
    }),
    relationships: graph.relationships.map(r => ({
      id: r.id,
      type: r.type,
      style: {},
      properties: { ...(r.properties || {}) },
      fromId: r.fromId,
      toId: r.toId,
    })),
  }, null, 2);
}

function toCypher(graph) {
  const lines = [];
  graph.nodes.forEach(n => {
    const labels = n.labels.length ? ":" + n.labels.join(":") : "";
    const props = Object.entries(n.properties || {}).map(([k, v]) => `${k}: '${v}'`).join(", ");
    lines.push(`CREATE (${n.id}${labels} {${props}})`);
  });
  graph.relationships.forEach(r => {
    const props = Object.entries(r.properties || {}).map(([k, v]) => `${k}: '${v}'`).join(", ");
    const propStr = props ? ` {${props}}` : "";
    lines.push(`CREATE (${r.fromId})-[:${r.type}${propStr}]->(${r.toId})`);
  });
  return lines.join("\n");
}

// --- Sub-components ---
const labelStyle = { fontWeight: 600, fontSize: 11, textTransform: "uppercase", letterSpacing: 1, color: "#94a3b8", display: "block", marginBottom: 2 };
const monoInputStyle = { flex: 1, background: "#1e293b", border: "1px solid #334155", color: "#e2e8f0", borderRadius: 4, padding: "4px 6px", fontSize: 12, fontFamily: "'JetBrains Mono', monospace" };
const fieldInputStyle = { width: "100%", marginTop: 4, marginBottom: 10, background: "#1e293b", border: "1px solid #334155", color: "#e2e8f0", borderRadius: 4, padding: "6px 8px", fontSize: 13, boxSizing: "border-box" };
const smallBtnStyle = { background: "none", border: "1px solid #334155", color: "#94a3b8", borderRadius: 4, cursor: "pointer", fontSize: 11, padding: "2px 8px" };

function PropertyEditor({ properties, onChange }) {
  const entries = Object.entries(properties || {});
  return (
    <div style={{ marginTop: 8 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 4 }}>
        <span style={labelStyle}>Properties</span>
        <button onClick={() => onChange({ ...properties, "": "" })} style={smallBtnStyle}>+ Add</button>
      </div>
      {entries.map(([k, v], i) => (
        <div key={i} style={{ display: "flex", gap: 4, marginBottom: 4, alignItems: "center" }}>
          <input value={k} onChange={e => {
            const copy = {};
            Object.entries(properties).forEach(([ok, ov]) => { copy[ok === k ? e.target.value : ok] = ov; });
            onChange(copy);
          }} placeholder="key" style={monoInputStyle} />
          <span style={{ color: "#475569" }}>:</span>
          <input value={v} onChange={e => onChange({ ...properties, [k]: e.target.value })} placeholder="type" style={monoInputStyle} />
          <button onClick={() => { const c = { ...properties }; delete c[k]; onChange(c); }} style={{ background: "none", border: "none", color: "#64748b", cursor: "pointer", fontSize: 14, padding: 0, lineHeight: 1 }}>×</button>
        </div>
      ))}
    </div>
  );
}

// Parse a comma-separated string into a clean extras array (trim, drop empties,
// drop the primary caption if it's been typed again, dedup). Used by
// AdditionalLabelsInput and also wherever we need the same semantics.
function parseExtraLabels(text, caption) {
  const seen = new Set();
  const out = [];
  for (const raw of text.split(",")) {
    const lab = raw.trim();
    if (!lab || lab === caption || seen.has(lab)) continue;
    seen.add(lab);
    out.push(lab);
  }
  return out;
}

// The separator-disappears bug this fixes: if the input's displayed value is
// derived from the parsed labels array every render, then a trailing comma or
// space gets normalised away between keystrokes, the input shortens, and the
// cursor lands in the wrong place — making it impossible to actually type a
// separator. The fix: keep the input's displayed text as local state, and only
// propagate the parsed array upward. When the user selects a different node,
// reset the local text from the new node's labels.
function AdditionalLabelsInput({ nodeId, extras, caption, onChange }) {
  const [text, setText] = useState(extras.join(", "));

  // Reset the text when the user selects a different node. We key on nodeId
  // (stable for the life of the node) rather than on `extras` (which changes
  // as the user types), so typing doesn't fight itself.
  useEffect(() => {
    setText(extras.join(", "));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nodeId]);

  return (
    <input
      value={text}
      onChange={e => {
        const next = e.target.value;
        setText(next);
        onChange(parseExtraLabels(next, caption));
      }}
      placeholder="Internal, Active"
      style={{ ...fieldInputStyle, fontFamily: "'JetBrains Mono', monospace", fontSize: 12 }}
    />
  );
}

function RelationshipListForNode({ nodeId, graph, setGraph, setSelected, selected }) {
  const rels = graph.relationships.filter(r => r.fromId === nodeId || r.toId === nodeId);
  if (rels.length === 0) return <div style={{ fontSize: 11, color: "#475569", marginTop: 8 }}>No relationships.</div>;

  const nodeMap = {};
  graph.nodes.forEach(n => { nodeMap[n.id] = n; });

  return (
    <div style={{ marginTop: 10 }}>
      <span style={labelStyle}>Relationships ({rels.length})</span>
      <div style={{ display: "flex", flexDirection: "column", gap: 4, marginTop: 4 }}>
        {rels.map(r => {
          const isSelf = r.fromId === r.toId;
          const otherId = r.fromId === nodeId ? r.toId : r.fromId;
          const otherNode = nodeMap[otherId];
          const direction = r.fromId === nodeId ? "→" : "←";
          const isActive = selected?.type === "relationship" && selected?.id === r.id;
          return (
            <div key={r.id}
              onClick={() => setSelected({ type: "relationship", id: r.id })}
              style={{
                display: "flex", alignItems: "center", gap: 6, padding: "5px 8px",
                background: isActive ? "#1e3a5f" : "#0f172a", border: `1px solid ${isActive ? "#3b82f6" : "#1e293b"}`,
                borderRadius: 6, cursor: "pointer", transition: "all 0.15s",
              }}>
              <span style={{ fontSize: 11, color: "#64748b", minWidth: 14, textAlign: "center" }}>{isSelf ? "↻" : direction}</span>
              <span style={{ fontSize: 11, color: "#93c5fd", fontFamily: "'JetBrains Mono', monospace", fontWeight: 600, flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                :{r.type}
              </span>
              {!isSelf && <span style={{ fontSize: 10, color: "#475569" }}>{otherNode?.caption || otherId}</span>}
              {isSelf && <span style={{ fontSize: 10, color: "#475569" }}>self</span>}
              <button onClick={(e) => {
                e.stopPropagation();
                setGraph(g => ({ ...g, relationships: g.relationships.filter(x => x.id !== r.id) }));
                if (isActive) setSelected({ type: "node", id: nodeId });
              }} style={{ background: "#7f1d1d", border: "none", color: "#fca5a5", borderRadius: 3, cursor: "pointer", fontSize: 10, padding: "1px 6px", fontWeight: 600, flexShrink: 0 }}>✕</button>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function Inspector({ selected, graph, setGraph, setSelected }) {
  if (!selected) {
    return (
      <div style={{ padding: 20, color: "#64748b", fontSize: 13 }}>
        <p style={{ marginBottom: 12 }}>Click a node or relationship to edit.</p>
        <p style={{ marginBottom: 12 }}><strong style={{ color: "#94a3b8" }}>Add Node</strong> button or <strong style={{ color: "#94a3b8" }}>double-click</strong> to create a node.</p>
        <p style={{ marginBottom: 12 }}><strong style={{ color: "#94a3b8" }}>Drag from node edge</strong> to another node to create a relationship.</p>
        <p style={{ marginBottom: 12 }}><strong style={{ color: "#94a3b8" }}>Scroll wheel</strong> to zoom in/out.</p>
        <p style={{ fontSize: 11, color: "#475569" }}>Relationships must connect to a target node.</p>
      </div>
    );
  }

  if (selected.type === "node") {
    const node = graph.nodes.find(n => n.id === selected.id);
    if (!node) return null;
    const updateNode = (patch) => setGraph(g => ({ ...g, nodes: g.nodes.map(n => n.id === node.id ? { ...n, ...patch } : n) }));
    const deleteNode = () => {
      setGraph(g => ({ ...g, nodes: g.nodes.filter(n => n.id !== node.id), relationships: g.relationships.filter(r => r.fromId !== node.id && r.toId !== node.id) }));
      setSelected(null);
    };

    return (
      <div style={{ padding: 16 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
          <span style={{ fontWeight: 700, fontSize: 13, textTransform: "uppercase", letterSpacing: 1, color: "#e2e8f0" }}>Node</span>
          <button onClick={deleteNode} style={{ background: "#7f1d1d", border: "none", color: "#fca5a5", borderRadius: 4, cursor: "pointer", fontSize: 11, padding: "3px 10px", fontWeight: 600 }}>Delete</button>
        </div>
        <span style={labelStyle}>Primary label (caption)</span>
        <input
          value={node.caption}
          onChange={e => {
            const newCaption = e.target.value;
            // The labels array is always [caption, ...additionalLabels]. When
            // the caption changes, keep the additional labels intact and just
            // swap the first element — preserving things like ["Account",
            // "Internal"] → ["BankAccount", "Internal"] as the user types.
            const extras = (node.labels || []).slice(1);
            const newLabels = newCaption ? [newCaption, ...extras] : extras;
            updateNode({ caption: newCaption, labels: newLabels });
          }}
          style={fieldInputStyle}
        />
        <span style={labelStyle}>Additional labels</span>
        <AdditionalLabelsInput
          nodeId={node.id}
          extras={(node.labels || []).slice(1)}
          caption={node.caption}
          onChange={extras => {
            const newLabels = node.caption ? [node.caption, ...extras] : extras;
            updateNode({ labels: newLabels });
          }}
        />
        <div style={{ fontSize: 10, color: "#64748b", marginTop: -6, marginBottom: 10 }}>
          Comma-separated. Exported as <code style={{ color: "#94a3b8" }}>:{node.caption || "Label"}{(node.labels || []).slice(1).map(l => ":" + l).join("")}</code>
        </div>
        <span style={labelStyle}>Color</span>
        <div style={{ display: "flex", gap: 6, marginTop: 4, marginBottom: 10, flexWrap: "wrap" }}>
          {COLORS.map(c => (
            <div key={c} onClick={() => updateNode({ style: { ...node.style, color: c } })} style={{
              width: 22, height: 22, borderRadius: "50%", background: c, cursor: "pointer",
              border: node.style.color === c ? "2px solid #fff" : "2px solid transparent", transition: "border 0.15s"
            }} />
          ))}
        </div>
        <span style={labelStyle}>Radius</span>
        <input type="range" min={30} max={80} value={node.style.radius} onChange={e => updateNode({ style: { ...node.style, radius: +e.target.value } })} style={{ width: "100%", marginTop: 2, marginBottom: 10 }} />
        <PropertyEditor properties={node.properties} onChange={p => updateNode({ properties: p })} />
        <RelationshipListForNode nodeId={node.id} graph={graph} setGraph={setGraph} setSelected={setSelected} selected={selected} />
      </div>
    );
  }

  if (selected.type === "relationship") {
    const rel = graph.relationships.find(r => r.id === selected.id);
    if (!rel) return null;
    const updateRel = (patch) => setGraph(g => ({ ...g, relationships: g.relationships.map(r => r.id === rel.id ? { ...r, ...patch } : r) }));
    const deleteRel = () => { setGraph(g => ({ ...g, relationships: g.relationships.filter(r => r.id !== rel.id) })); setSelected(null); };
    const reverseRel = () => updateRel({ fromId: rel.toId, toId: rel.fromId });
    const nodeMap = {};
    graph.nodes.forEach(n => { nodeMap[n.id] = n; });
    const fromNode = nodeMap[rel.fromId];
    const toNode = nodeMap[rel.toId];

    return (
      <div style={{ padding: 16 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
          <span style={{ fontWeight: 700, fontSize: 13, textTransform: "uppercase", letterSpacing: 1, color: "#e2e8f0" }}>Relationship</span>
          <div style={{ display: "flex", gap: 6 }}>
            <button onClick={reverseRel} style={{ background: "#1e3a5f", border: "none", color: "#93c5fd", borderRadius: 4, cursor: "pointer", fontSize: 11, padding: "3px 10px", fontWeight: 600 }}>⇄ Reverse</button>
            <button onClick={deleteRel} style={{ background: "#7f1d1d", border: "none", color: "#fca5a5", borderRadius: 4, cursor: "pointer", fontSize: 11, padding: "3px 10px", fontWeight: 600 }}>Delete</button>
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 12, padding: "6px 10px", background: "#0b1121", borderRadius: 6, border: "1px solid #1e293b" }}>
          <span style={{ fontSize: 11, color: fromNode?.style.color || "#94a3b8", fontWeight: 700 }}>{fromNode?.caption || rel.fromId}</span>
          <span style={{ fontSize: 11, color: "#475569" }}>→</span>
          <span style={{ fontSize: 11, color: toNode?.style.color || "#94a3b8", fontWeight: 700 }}>{toNode?.caption || rel.toId}</span>
        </div>
        <span style={labelStyle}>Type</span>
        <input value={rel.type} onChange={e => updateRel({ type: e.target.value })} style={{ ...fieldInputStyle, fontFamily: "'JetBrains Mono', monospace" }} />
        <PropertyEditor properties={rel.properties} onChange={p => updateRel({ properties: p })} />
      </div>
    );
  }
  return null;
}

function ExportModal({ graph, onClose }) {
  const [tab, setTab] = useState("json");
  const content = tab === "json" ? toArrowsJSON(graph) : toCypher(graph);
  const [copied, setCopied] = useState(false);
  const preRef = useRef(null);

  const copy = () => {
    const ta = document.createElement("textarea");
    ta.value = content;
    ta.style.cssText = "position:fixed;left:-9999px;top:-9999px;opacity:0";
    document.body.appendChild(ta);
    ta.focus();
    ta.select();
    try { document.execCommand("copy"); } catch (e) {}
    document.body.removeChild(ta);
    setCopied(true);
    setTimeout(() => setCopied(false), 3000);
  };

  const selectAll = () => {
    if (preRef.current) {
      const range = document.createRange();
      range.selectNodeContents(preRef.current);
      const sel = window.getSelection();
      sel.removeAllRanges();
      sel.addRange(range);
    }
  };

  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.6)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 999 }} onClick={onClose}>
      <div onClick={e => e.stopPropagation()} style={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: 12, width: 620, maxHeight: "80vh", display: "flex", flexDirection: "column", boxShadow: "0 25px 50px rgba(0,0,0,0.5)" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "14px 20px", borderBottom: "1px solid #1e293b" }}>
          <span style={{ fontWeight: 700, fontSize: 15, color: "#e2e8f0" }}>Export Graph</span>
          <button onClick={onClose} style={{ background: "none", border: "none", color: "#64748b", cursor: "pointer", fontSize: 18 }}>✕</button>
        </div>
        <div style={{ display: "flex", gap: 0, borderBottom: "1px solid #1e293b" }}>
          {["json", "cypher"].map(t => (
            <button key={t} onClick={() => { setTab(t); setCopied(false); }} style={{ flex: 1, padding: "10px 0", border: "none", cursor: "pointer", fontSize: 12, fontWeight: 600, textTransform: "uppercase", letterSpacing: 1, background: tab === t ? "#1e293b" : "transparent", color: tab === t ? "#e2e8f0" : "#64748b", borderBottom: tab === t ? "2px solid #4C8BF5" : "2px solid transparent" }}>
              {t === "json" ? "Arrows JSON" : "Cypher"}
            </button>
          ))}
        </div>
        <pre ref={preRef} onClick={selectAll} style={{ flex: 1, overflow: "auto", padding: 20, margin: 0, fontSize: 12, fontFamily: "'JetBrains Mono', monospace", color: "#94a3b8", lineHeight: 1.6, whiteSpace: "pre-wrap", userSelect: "text", WebkitUserSelect: "text", cursor: "text" }}>{content}</pre>
        <div style={{ padding: "12px 20px", borderTop: "1px solid #1e293b", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <span style={{ fontSize: 11, color: "#64748b" }}>{copied ? "Now paste into chat to continue with data generation" : "Click the code above to select all, or use the button"}</span>
          <button onClick={copy} style={{ background: copied ? "#30A46C" : "#4C8BF5", border: "none", color: "#fff", borderRadius: 6, cursor: "pointer", fontSize: 13, padding: "9px 20px", fontWeight: 600, minWidth: 160, transition: "background 0.2s" }}>
            {copied ? "✓ Copied to Clipboard!" : ("Copy " + (tab === "json" ? "JSON" : "Cypher"))}
          </button>
        </div>
      </div>
    </div>
  );
}

function ImportModal({ onImport, onClose }) {
  const [text, setText] = useState("");
  const [error, setError] = useState(null);
  const handleImport = () => {
    try {
      const parsed = JSON.parse(text);
      const g = parsed.graph || parsed;
      if (!g.nodes || !g.relationships) throw new Error("Invalid");
      // arrows.app puts default radius (and other styling) in a top-level
      // `style` block. Pick up the radius default once so per-node overrides
      // can fall back to it, matching arrows.app's own rendering.
      const topRadius = (g.style && typeof g.style.radius === "number") ? g.style.radius : null;
      onImport({
        nodes: g.nodes.map(n => {
          // Caption derivation: arrows.app commonly emits caption="" and
          // expects labels[0] to drive the display. Treat empty/whitespace
          // captions as missing so the fallback to labels[0] kicks in.
          const rawCaption = (n.caption && n.caption.trim()) ? n.caption : null;
          const caption = rawCaption || (n.labels?.[0]) || "";
          // Enforce labels = [caption, ...rest], no dupes, no empties — same
          // invariant inject.py enforces on the CLI side.
          const seen = new Set();
          const extras = [];
          for (const lab of (n.labels || [])) {
            if (typeof lab !== "string") continue;
            const trimmed = lab.trim();
            if (!trimmed || trimmed === caption || seen.has(trimmed)) continue;
            seen.add(trimmed);
            extras.push(trimmed);
          }
          const labels = caption ? [caption, ...extras] : extras;
          // Style: accept BOTH our internal `color` (camelCase) and arrows.app's
          // `node-color` (kebab-case). Radius can be node-level OR inherited
          // from the top-level style block.
          const ns = n.style || {};
          const color = ns.color || ns["node-color"] || COLORS[Math.floor(Math.random() * COLORS.length)];
          const radius = ns.radius || topRadius || 50;
          return {
            id: n.id || uid(),
            position: n.position || { x: 200 + Math.random() * 400, y: 200 + Math.random() * 300 },
            caption,
            labels,
            properties: n.properties || {},
            style: { color, radius },
          };
        }),
        relationships: g.relationships.map(r => ({ id: r.id || rid(), type: r.type || "RELATED_TO", fromId: r.fromId || r.startNode, toId: r.toId || r.endNode, properties: r.properties || {} })),
        style: g.style || {},
      });
      onClose();
    } catch { setError("Invalid JSON. Paste an arrows.app export."); }
  };

  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.6)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 999 }} onClick={onClose}>
      <div onClick={e => e.stopPropagation()} style={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: 12, width: 550, boxShadow: "0 25px 50px rgba(0,0,0,0.5)" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "14px 20px", borderBottom: "1px solid #1e293b" }}>
          <span style={{ fontWeight: 700, fontSize: 15, color: "#e2e8f0" }}>Import Arrows JSON</span>
          <button onClick={onClose} style={{ background: "none", border: "none", color: "#64748b", cursor: "pointer", fontSize: 18 }}>✕</button>
        </div>
        <div style={{ padding: 20 }}>
          <textarea value={text} onChange={e => { setText(e.target.value); setError(null); }} placeholder='Paste arrows.app JSON here...' rows={12} style={{ width: "100%", background: "#1e293b", border: "1px solid #334155", color: "#e2e8f0", borderRadius: 6, padding: 12, fontSize: 12, fontFamily: "'JetBrains Mono', monospace", resize: "vertical", boxSizing: "border-box" }} />
          {error && <div style={{ color: "#f87171", fontSize: 12, marginTop: 6 }}>{error}</div>}
        </div>
        <div style={{ display: "flex", justifyContent: "flex-end", padding: "12px 20px", borderTop: "1px solid #1e293b", gap: 8 }}>
          <button onClick={onClose} style={{ background: "#1e293b", border: "1px solid #334155", color: "#e2e8f0", borderRadius: 6, cursor: "pointer", fontSize: 12, padding: "8px 16px" }}>Cancel</button>
          <button onClick={handleImport} style={{ background: "#4C8BF5", border: "none", color: "#fff", borderRadius: 6, cursor: "pointer", fontSize: 12, padding: "8px 16px", fontWeight: 600 }}>Import</button>
        </div>
      </div>
    </div>
  );
}

// --- Main ---
export default function GraphEditor() {
  const [graph, setGraph] = useState(initialGraph);
  const [selected, setSelected] = useState(null);
  const [dragging, setDragging] = useState(null);
  const [drawingRel, setDrawingRel] = useState(null);
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });
  const [showExport, setShowExport] = useState(false);
  const [showImport, setShowImport] = useState(false);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [panning, setPanning] = useState(null);
  const [zoom, setZoom] = useState(1);
  const [hoveredTarget, setHoveredTarget] = useState(null);
  const [relDropFailed, setRelDropFailed] = useState(false);
  const svgRef = useRef(null);

  const MIN_ZOOM = 0.15;
  const MAX_ZOOM = 3;

  const toSVG = useCallback((clientX, clientY) => {
    const rect = svgRef.current?.getBoundingClientRect();
    if (!rect) return { x: clientX, y: clientY };
    return { x: (clientX - rect.left - pan.x) / zoom, y: (clientY - rect.top - pan.y) / zoom };
  }, [pan, zoom]);

  const handleCanvasDoubleClick = (e) => {
    if (e.target !== svgRef.current && e.target.tagName !== "rect") return;
    const pos = toSVG(e.clientX, e.clientY);
    const id = uid();
    const color = COLORS[graph.nodes.length % COLORS.length];
    setGraph(g => ({ ...g, nodes: [...g.nodes, { id, position: pos, caption: "Node", labels: ["Node"], properties: {}, style: { color, radius: 50 } }] }));
    setSelected({ type: "node", id });
  };

  const addNodeAtCenter = () => {
    const rect = svgRef.current?.getBoundingClientRect();
    const cx = rect ? (rect.width / 2 - pan.x) / zoom : 400;
    const cy = rect ? (rect.height / 2 - pan.y) / zoom : 300;
    const jitter = () => (Math.random() - 0.5) * 60;
    const id = uid();
    const color = COLORS[graph.nodes.length % COLORS.length];
    setGraph(g => ({ ...g, nodes: [...g.nodes, { id, position: { x: cx + jitter(), y: cy + jitter() }, caption: "Node", labels: ["Node"], properties: {}, style: { color, radius: 50 } }] }));
    setSelected({ type: "node", id });
  };

  const applyZoom = useCallback((newZoom, centerX, centerY) => {
    const nz = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, newZoom));
    const ratio = nz / zoom;
    setPan(p => ({ x: centerX - ratio * (centerX - p.x), y: centerY - ratio * (centerY - p.y) }));
    setZoom(nz);
  }, [zoom]);

  const handleMouseDown = (e) => {
    if (e.button === 1 || (e.button === 0 && (e.target === svgRef.current || e.target.tagName === "rect"))) {
      setPanning({ startX: e.clientX, startY: e.clientY, startPanX: pan.x, startPanY: pan.y });
    }
  };

  const handleWheel = useCallback((e) => {
    e.preventDefault();
    const rect = svgRef.current?.getBoundingClientRect();
    if (!rect) return;
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;
    const factor = e.deltaY > 0 ? 0.9 : 1.1;
    applyZoom(zoom * factor, mx, my);
  }, [zoom, applyZoom]);

  useEffect(() => {
    const svg = svgRef.current;
    if (!svg) return;
    svg.addEventListener("wheel", handleWheel, { passive: false });
    return () => svg.removeEventListener("wheel", handleWheel);
  }, [handleWheel]);

  const handleMouseMove = useCallback((e) => {
    const svgPt = toSVG(e.clientX, e.clientY);
    setMousePos(svgPt);

    if (panning) {
      setPan({ x: panning.startPanX + (e.clientX - panning.startX), y: panning.startPanY + (e.clientY - panning.startY) });
      return;
    }
    if (dragging) {
      setGraph(g => ({ ...g, nodes: g.nodes.map(n => n.id === dragging.id ? { ...n, position: { x: svgPt.x + dragging.offX, y: svgPt.y + dragging.offY } } : n) }));
    }
    if (drawingRel) {
      const target = graph.nodes.find(n => Math.sqrt((n.position.x - svgPt.x) ** 2 + (n.position.y - svgPt.y) ** 2) <= n.style.radius + 10);
      setHoveredTarget(target ? target.id : null);
    }
  }, [dragging, panning, toSVG, drawingRel, graph.nodes]);

  const handleMouseUp = useCallback((e) => {
    if (panning) { setPanning(null); return; }
    if (drawingRel) {
      const svgPt = toSVG(e.clientX, e.clientY);
      const target = graph.nodes.find(n => Math.sqrt((n.position.x - svgPt.x) ** 2 + (n.position.y - svgPt.y) ** 2) <= n.style.radius + 10);
      if (target) {
        const id = rid();
        setGraph(g => ({ ...g, relationships: [...g.relationships, { id, type: "RELATED_TO", fromId: drawingRel.fromId, toId: target.id, properties: {} }] }));
        setSelected({ type: "relationship", id });
      } else {
        setRelDropFailed(true);
        setTimeout(() => setRelDropFailed(false), 1200);
      }
      setDrawingRel(null);
      setHoveredTarget(null);
    }
    setDragging(null);
  }, [drawingRel, graph.nodes, panning, toSVG]);

  useEffect(() => {
    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
    return () => { window.removeEventListener("mousemove", handleMouseMove); window.removeEventListener("mouseup", handleMouseUp); };
  }, [handleMouseMove, handleMouseUp]);

  const nodeMap = {};
  graph.nodes.forEach(n => { nodeMap[n.id] = n; });

  const relGroups = {};
  graph.relationships.forEach(r => {
    const key = [r.fromId, r.toId].sort().join("-");
    if (!relGroups[key]) relGroups[key] = [];
    relGroups[key].push(r.id);
  });

  const selfLoopGroups = {};
  graph.relationships.forEach(r => {
    if (r.fromId === r.toId) {
      if (!selfLoopGroups[r.fromId]) selfLoopGroups[r.fromId] = [];
      selfLoopGroups[r.fromId].push(r.id);
    }
  });

  const zoomPercent = Math.round(zoom * 100);
  const zoomBtnStyle = { background: "#0f172a", border: "1px solid #1e293b", color: "#94a3b8", borderRadius: 6, cursor: "pointer", fontSize: 14, width: 32, height: 32, display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 700 };

  return (
    <div style={{ width: "100%", height: "100vh", display: "flex", fontFamily: "'Inter', -apple-system, sans-serif", background: "#0b1121", color: "#e2e8f0", overflow: "hidden" }}>
      <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet" />

      <div style={{ flex: 1, position: "relative" }}>
        {/* Toolbar */}
        <div style={{ position: "absolute", top: 12, left: 12, right: 12, zIndex: 10, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 6, background: "#0f172a", border: "1px solid #1e293b", borderRadius: 8, padding: "6px 14px" }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#4C8BF5" strokeWidth="2"><circle cx="6" cy="6" r="3"/><circle cx="18" cy="18" r="3"/><line x1="8.5" y1="8.5" x2="15.5" y2="15.5"/></svg>
              <span style={{ fontWeight: 700, fontSize: 14, color: "#e2e8f0" }}>Graph Schema Editor</span>
            </div>
          </div>
          <div style={{ display: "flex", gap: 6 }}>
            <button onClick={addNodeAtCenter} style={{ background: "#0f172a", border: "1px solid #1e293b", color: "#94a3b8", borderRadius: 6, cursor: "pointer", fontSize: 12, padding: "7px 14px", fontWeight: 500, display: "flex", alignItems: "center", gap: 5 }}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><circle cx="12" cy="12" r="9"/><line x1="12" y1="8" x2="12" y2="16"/><line x1="8" y1="12" x2="16" y2="12"/></svg>
              Add Node
            </button>
            <button onClick={() => setShowImport(true)} style={{ background: "#0f172a", border: "1px solid #1e293b", color: "#94a3b8", borderRadius: 6, cursor: "pointer", fontSize: 12, padding: "7px 14px", fontWeight: 500 }}>Import</button>
            <button onClick={() => setShowExport(true)} style={{ background: "#4C8BF5", border: "none", color: "#fff", borderRadius: 6, cursor: "pointer", fontSize: 12, padding: "7px 14px", fontWeight: 600 }}>Export</button>
          </div>
        </div>

        {/* Bottom bar */}
        <div style={{ position: "absolute", bottom: 12, left: 12, right: 12, zIndex: 10, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div style={{ display: "flex", gap: 8, fontSize: 11, color: "#64748b" }}>
            <span style={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: 6, padding: "4px 10px" }}>{graph.nodes.length} nodes</span>
            <span style={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: 6, padding: "4px 10px" }}>{graph.relationships.length} rels</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 4, background: "#0f172a", border: "1px solid #1e293b", borderRadius: 8, padding: 4 }}>
            <button onClick={() => { const rect = svgRef.current?.getBoundingClientRect(); applyZoom(zoom * 0.8, rect ? rect.width / 2 : 400, rect ? rect.height / 2 : 300); }} style={zoomBtnStyle}>−</button>
            <button onClick={() => { setPan({ x: 0, y: 0 }); setZoom(1); }} style={{ ...zoomBtnStyle, width: 52, fontSize: 11, fontWeight: 600, fontFamily: "'JetBrains Mono', monospace" }}>{zoomPercent}%</button>
            <button onClick={() => { const rect = svgRef.current?.getBoundingClientRect(); applyZoom(zoom * 1.25, rect ? rect.width / 2 : 400, rect ? rect.height / 2 : 300); }} style={zoomBtnStyle}>+</button>
          </div>
        </div>

        <svg ref={svgRef} style={{ width: "100%", height: "100%", cursor: panning ? "grabbing" : dragging ? "grabbing" : "default" }} onDoubleClick={handleCanvasDoubleClick} onMouseDown={handleMouseDown}>
          <defs>
            <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse" patternTransform={`translate(${pan.x % (40 * zoom)} ${pan.y % (40 * zoom)}) scale(${zoom})`}>
              <circle cx="20" cy="20" r="0.5" fill="#1e293b" />
            </pattern>
            <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto" markerUnits="strokeWidth"><polygon points="0 0, 10 3.5, 0 7" fill="#64748b" /></marker>
            <marker id="arrowhead-active" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto" markerUnits="strokeWidth"><polygon points="0 0, 10 3.5, 0 7" fill="#4C8BF5" /></marker>
            <marker id="arrowhead-drawing" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto" markerUnits="strokeWidth"><polygon points="0 0, 10 3.5, 0 7" fill="#4C8BF5" opacity="0.6" /></marker>
          </defs>
          <rect width="100%" height="100%" fill="url(#grid)" />

          <g transform={`translate(${pan.x}, ${pan.y}) scale(${zoom})`}>
            {/* Relationships */}
            {graph.relationships.map(rel => {
              const from = nodeMap[rel.fromId];
              const to = nodeMap[rel.toId];
              if (!from || !to) return null;
              const isSelected = selected?.type === "relationship" && selected?.id === rel.id;

              if (rel.fromId === rel.toId) {
                const siblings = selfLoopGroups[rel.fromId] || [];
                const idx = siblings.indexOf(rel.id);
                const total = siblings.length;
                const { path, midX, midY } = getSelfLoopPath(from.position.x, from.position.y, from.style.radius, idx, total);
                return (
                  <g key={rel.id}>
                    <path d={path} fill="none" stroke="transparent" strokeWidth={22} style={{ cursor: "pointer" }} onClick={(e) => { e.stopPropagation(); setSelected({ type: "relationship", id: rel.id }); }} />
                    <path d={path} fill="none" stroke={isSelected ? "#4C8BF5" : "#64748b"} strokeWidth={isSelected ? 2.5 : 1.5} markerEnd={isSelected ? "url(#arrowhead-active)" : "url(#arrowhead)"} />
                    {rel.type && (
                      <g transform={`translate(${midX}, ${midY})`}>
                        <rect x={-rel.type.length * 3.2 - 6} y={-8} width={rel.type.length * 6.4 + 12} height={16} rx={4} fill="#0b1121" opacity={0.9} />
                        <text x={0} y={0} textAnchor="middle" dominantBaseline="central" fill={isSelected ? "#bfdbfe" : "#e2e8f0"} fontSize="10" fontFamily="'JetBrains Mono', monospace" fontWeight="600" style={{ pointerEvents: "none" }}>{rel.type}</text>
                      </g>
                    )}
                  </g>
                );
              }

              const pairKey = [rel.fromId, rel.toId].sort().join("-");
              const siblings = relGroups[pairKey] || [];
              const idx = siblings.indexOf(rel.id);
              const siblingCount = siblings.length;
              // Give rels in the same direction (from->to) one sign and the
              // reverse direction (to->from) the opposite sign, so back-and-forth
              // pairs naturally separate without the user having to reorder.
              const sortedPair = [rel.fromId, rel.toId].sort();
              const directionSign = rel.fromId === sortedPair[0] ? 1 : -1;
              // Perpendicular fan: each sibling is offset off the centerline.
              // 36px step keeps labels readable without pushing edges too far.
              const laneOffset = siblingCount > 1
                ? (idx - (siblingCount - 1) / 2) * 36 * directionSign
                : 0;

              const ep = getEdgePoints(from.position, to.position, from.style.radius, to.style.radius);
              const dx = ep.x2 - ep.x1; const dy = ep.y2 - ep.y1; const l = Math.sqrt(dx * dx + dy * dy) || 1;
              const nx = -dy / l; const ny = dx / l;

              // Offset the start/end points perpendicular to the line so each
              // sibling leaves and arrives at a different spot on the node
              // boundary — this is what actually prevents visual overlap at
              // the arrowhead.
              const endpointOffset = laneOffset * 0.45;
              const x1 = ep.x1 + nx * endpointOffset;
              const y1 = ep.y1 + ny * endpointOffset;
              const x2 = ep.x2 + nx * endpointOffset;
              const y2 = ep.y2 + ny * endpointOffset;

              // Midpoint bulge: curve arcs out further than the endpoint offset
              // so the label sits in clear space between the edges.
              const midX = (x1 + x2) / 2 + nx * laneOffset * 0.9;
              const midY = (y1 + y2) / 2 + ny * laneOffset * 0.9;
              const pathD = laneOffset !== 0
                ? `M ${x1} ${y1} Q ${midX} ${midY} ${x2} ${y2}`
                : `M ${x1} ${y1} L ${x2} ${y2}`;

              return (
                <g key={rel.id}>
                  <path d={pathD} fill="none" stroke="transparent" strokeWidth={16} style={{ cursor: "pointer" }} onClick={(e) => { e.stopPropagation(); setSelected({ type: "relationship", id: rel.id }); }} />
                  <path d={pathD} fill="none" stroke={isSelected ? "#4C8BF5" : "#64748b"} strokeWidth={isSelected ? 2.5 : 1.5} markerEnd={isSelected ? "url(#arrowhead-active)" : "url(#arrowhead)"} />
                  {rel.type && (
                    <g transform={`translate(${midX}, ${midY})`}>
                      <rect x={-rel.type.length * 3.2 - 6} y={-16} width={rel.type.length * 6.4 + 12} height={16} rx={4} fill="#0b1121" opacity={0.85} />
                      <text x={0} y={-8} textAnchor="middle" dominantBaseline="central" fill={isSelected ? "#bfdbfe" : "#e2e8f0"} fontSize="10" fontFamily="'JetBrains Mono', monospace" fontWeight="600" style={{ pointerEvents: "none" }}>{rel.type}</text>
                    </g>
                  )}
                  {Object.keys(rel.properties || {}).length > 0 && <text x={midX} y={midY} textAnchor="middle" dy="10" fill={isSelected ? "#cbd5e1" : "#94a3b8"} fontSize="9" fontFamily="'JetBrains Mono', monospace" style={{ pointerEvents: "none" }}>{"{"}{Object.keys(rel.properties).join(", ")}{"}"}</text>}
                </g>
              );
            })}

            {drawingRel && (() => {
              const from = nodeMap[drawingRel.fromId];
              if (!from) return null;
              const ep = getEdgePoints(from.position, mousePos, from.style.radius, 0);
              const hasTarget = hoveredTarget !== null;
              return <line x1={ep.x1} y1={ep.y1} x2={mousePos.x} y2={mousePos.y} stroke={hasTarget ? "#30A46C" : "#4C8BF5"} strokeWidth={2} strokeDasharray="6 4" opacity={hasTarget ? 0.9 : 0.5} markerEnd="url(#arrowhead-drawing)" />;
            })()}

            {/* Nodes */}
            {graph.nodes.map(node => {
              const isSelected = selected?.type === "node" && selected?.id === node.id;
              const props = Object.entries(node.properties || {});
              return (
                <g key={node.id} style={{ cursor: "grab" }}
                  onMouseDown={(e) => {
                    e.stopPropagation();
                    const svgPt = toSVG(e.clientX, e.clientY);
                    const dist = Math.sqrt((node.position.x - svgPt.x) ** 2 + (node.position.y - svgPt.y) ** 2);
                    if (dist > node.style.radius * 0.7) {
                      setDrawingRel({ fromId: node.id });
                    } else {
                      setDragging({ id: node.id, offX: node.position.x - svgPt.x, offY: node.position.y - svgPt.y });
                      setSelected({ type: "node", id: node.id });
                    }
                  }}
                  onClick={(e) => { e.stopPropagation(); setSelected({ type: "node", id: node.id }); }}
                >
                  <circle cx={node.position.x} cy={node.position.y} r={node.style.radius + 12} fill="transparent" stroke={isSelected ? "#4C8BF5" : "transparent"} strokeWidth={1} strokeDasharray="4 4" opacity={0.3} />
                  {drawingRel && hoveredTarget === node.id && (
                    <circle cx={node.position.x} cy={node.position.y} r={node.style.radius + 8} fill="none" stroke={drawingRel.fromId === node.id ? "#F59E0B" : "#30A46C"} strokeWidth={3} opacity={0.7}>
                      <animate attributeName="r" from={node.style.radius + 6} to={node.style.radius + 14} dur="0.8s" repeatCount="indefinite" />
                      <animate attributeName="opacity" from="0.7" to="0.2" dur="0.8s" repeatCount="indefinite" />
                    </circle>
                  )}
                  <circle cx={node.position.x} cy={node.position.y} r={node.style.radius} fill={node.style.color + "18"} stroke={isSelected ? "#4C8BF5" : node.style.color} strokeWidth={isSelected ? 3 : 2} style={{ transition: "stroke 0.15s, stroke-width 0.15s" }} />
                  <circle cx={node.position.x} cy={node.position.y} r={node.style.radius - 4} fill="none" stroke={node.style.color} strokeWidth={0.5} opacity={0.3} />
                  <text x={node.position.x} y={node.position.y} textAnchor="middle" dominantBaseline="central" fill="#ffffff" fontSize={node.caption.length > 10 ? 11 : 13} fontWeight="700" fontFamily="'Inter', sans-serif" style={{ pointerEvents: "none", textTransform: "uppercase", letterSpacing: 0.5 }}>{node.caption}</text>
                  {/* Secondary labels (arrows.app convention): pills below the circle, above properties. */}
                  {(() => {
                    const extras = (node.labels || []).slice(1);
                    if (extras.length === 0) return null;
                    // Pre-compute per-pill widths so the row is centred as a group.
                    const pillPadX = 6;
                    const charW = 6;
                    const gap = 4;
                    const widths = extras.map(l => Math.max(24, l.length * charW + pillPadX * 2));
                    const totalW = widths.reduce((a, b) => a + b, 0) + gap * (extras.length - 1);
                    const rowY = node.position.y + node.style.radius + 8;
                    let cursorX = node.position.x - totalW / 2;
                    return extras.map((label, i) => {
                      const w = widths[i];
                      const x = cursorX;
                      cursorX += w + gap;
                      return (
                        <g key={label + i} style={{ pointerEvents: "none" }}>
                          <rect x={x} y={rowY} width={w} height={14} rx={7} fill={node.style.color + "30"} stroke={node.style.color} strokeWidth={0.75} />
                          <text x={x + w / 2} y={rowY + 7} textAnchor="middle" dominantBaseline="central" fill="#ffffff" fontSize="9" fontFamily="'JetBrains Mono', monospace" fontWeight="600" style={{ letterSpacing: 0.3 }}>:{label}</text>
                        </g>
                      );
                    });
                  })()}
                  {props.map(([k, v], i) => {
                    // Push properties down to make room for the label-pill row.
                    const extrasCount = (node.labels || []).length - 1;
                    const pillRowHeight = extrasCount > 0 ? 18 : 0;
                    return (
                      <text key={k} x={node.position.x} y={node.position.y + node.style.radius + 14 + pillRowHeight + i * 14} textAnchor="middle" fill="#cbd5e1" fontSize="10" fontFamily="'JetBrains Mono', monospace" style={{ pointerEvents: "none" }}>{k}: {v}</text>
                    );
                  })}
                </g>
              );
            })}
          </g>
        </svg>
      </div>

      {/* Sidebar */}
      <div style={{ width: 280, minWidth: 280, background: "#0f172a", borderLeft: "1px solid #1e293b", overflowY: "auto", display: "flex", flexDirection: "column" }}>
        <div style={{ padding: "12px 16px", borderBottom: "1px solid #1e293b", fontWeight: 700, fontSize: 12, textTransform: "uppercase", letterSpacing: 1, color: "#64748b" }}>Inspector</div>
        <Inspector selected={selected} graph={graph} setGraph={setGraph} setSelected={setSelected} />
      </div>

      {showExport && <ExportModal graph={graph} onClose={() => setShowExport(false)} />}
      {showImport && <ImportModal onImport={g => setGraph(g)} onClose={() => setShowImport(false)} />}
      {relDropFailed && (
        <div style={{ position: "fixed", bottom: 24, left: "50%", transform: "translateX(-50%)", background: "#1c1917", border: "1px solid #44403c", borderRadius: 8, padding: "10px 20px", color: "#fbbf24", fontSize: 13, fontWeight: 500, display: "flex", alignItems: "center", gap: 8, zIndex: 1000, boxShadow: "0 8px 24px rgba(0,0,0,0.4)", animation: "fadeInUp 0.2s ease-out" }}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#fbbf24" strokeWidth="2" strokeLinecap="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
          Relationship must connect to a node
        </div>
      )}
      <style>{`@keyframes fadeInUp { from { opacity: 0; transform: translateX(-50%) translateY(8px); } to { opacity: 1; transform: translateX(-50%) translateY(0); } }`}</style>
    </div>
  );
}
