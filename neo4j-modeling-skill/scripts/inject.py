#!/usr/bin/env python3
"""
Unified injector for graph-schema-studio.

Reads a schema definition from one of several sources, normalises it into the
editor's initialGraph shape, and writes a ready-to-use React artifact to
/mnt/user-data/outputs/graph-schema-editor.jsx by default.

INPUT SOURCES
-------------
The script auto-detects the input source from the positional argument (or from
stdin when no argument is given):

  1. Reference-model ID (e.g. "claims-fraud"):
        python3 inject.py claims-fraud
     → resolves to references/claims-fraud.json in this skill

  2. File path (absolute or relative):
        python3 inject.py /home/claude/my_schema.json
     → reads that file

  3. Stdin (when no argument or when the argument is "-"):
        cat <<EOF | python3 inject.py
        { "nodes": [...], "relationships": [...] }
        EOF

  4. List available reference models:
        python3 inject.py --list

ACCEPTED SCHEMA SHAPES
----------------------
The normaliser accepts both the minimal custom shape and the full
reference-model shape, unwrapping common containers automatically:

  - Minimal custom:   { "nodes": [...], "relationships": [...] }
  - arrows.app:       { "graph": { "nodes": [...], "relationships": [...] } }
  - Reference model:  { "initialGraph": { "nodes": [...], "relationships": [...] }, ... }

In minimal custom schemas, relationship endpoints can be given as `from`/`to`
with node captions (the normaliser resolves them to ids) — or as explicit
`fromId`/`toId` when two nodes share a caption.

Any optional field (id, position, style, labels) is auto-filled with a
sensible default when omitted, but any value the caller DOES supply is
respected unchanged. This is what lets reference models keep their curated
positions and colours while custom domains stay terse.

OUTPUT
------
Pass an optional output path as the second positional argument:

    python3 inject.py claims-fraud /tmp/my-editor.jsx

Defaults to /mnt/user-data/outputs/graph-schema-editor.jsx.
"""
import json
import sys
import re
import os
import math

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)

TEMPLATE_PATH = os.path.join(SKILL_DIR, "assets", "graph-editor-template.jsx")
REFERENCES_DIR = os.path.join(SKILL_DIR, "references")


def _default_output_dir():
    """Pick a sensible default output directory for the running environment.

    claude.ai chat mounts /mnt/user-data/outputs/, but other runtimes
    (Cowork, Claude Code, API harnesses) may not. Fall back to the current
    working directory so the injector still works there. Callers can always
    override with an explicit second positional argument.
    """
    canonical = "/mnt/user-data/outputs"
    if os.path.isdir(canonical):
        return canonical
    return os.getcwd()


DEFAULT_OUTPUT = os.path.join(_default_output_dir(), "graph-schema-editor.jsx")

# Keep in sync with the COLORS array at the top of the JSX template
COLORS = [
    "#4C8BF5", "#E5484D", "#30A46C", "#E38627", "#8B5CF6",
    "#06B6D4", "#EC4899", "#F59E0B", "#6366F1", "#14B8A6",
]

DEFAULT_RADIUS = 55


# ---------------------------------------------------------------------------
# Reference model catalog
# ---------------------------------------------------------------------------
def list_reference_models():
    """Return the reference model catalog, preferring model-index.json."""
    index_path = os.path.join(REFERENCES_DIR, "model-index.json")
    if os.path.exists(index_path):
        with open(index_path) as f:
            return json.load(f).get("models", [])
    # Fallback: scan the references directory
    models = []
    if not os.path.isdir(REFERENCES_DIR):
        return models
    for f in sorted(os.listdir(REFERENCES_DIR)):
        if f.endswith(".json") and f != "model-index.json":
            with open(os.path.join(REFERENCES_DIR, f)) as fh:
                m = json.load(fh)
            models.append({
                "id": m.get("id", f[:-5]),
                "name": m.get("name", f[:-5]),
                "industry": m.get("industry", ""),
                "nodeCount": len(m.get("initialGraph", {}).get("nodes", [])),
                "relationshipCount": len(m.get("initialGraph", {}).get("relationships", [])),
            })
    return models


def print_reference_list():
    models = list_reference_models()
    if not models:
        print(f"No reference models found in {REFERENCES_DIR}", file=sys.stderr)
        sys.exit(1)
    print(f"{'ID':<42} {'Industry':<28} {'N':>3} {'R':>3}")
    print("-" * 80)
    for m in models:
        print(f"{m['id']:<42} {m.get('industry',''):<28} "
              f"{m.get('nodeCount','?'):>3} {m.get('relationshipCount','?'):>3}")
    print(f"\n{len(models)} reference models available in {REFERENCES_DIR}")


# ---------------------------------------------------------------------------
# Auto-layout for minimal schemas (nodes without explicit positions)
# ---------------------------------------------------------------------------
def auto_layout(n_nodes):
    """Return (x, y) positions arranged around a circle centred on the viewport."""
    if n_nodes == 0:
        return []
    if n_nodes == 1:
        return [(450, 350)]
    if n_nodes == 2:
        return [(300, 300), (600, 300)]
    cx, cy = 450, 350
    radius = max(180, 60 * n_nodes / (2 * math.pi))
    radius = min(radius, 320)
    positions = []
    for i in range(n_nodes):
        angle = -math.pi / 2 + (2 * math.pi * i / n_nodes)
        x = round(cx + radius * math.cos(angle))
        y = round(cy + radius * math.sin(angle))
        positions.append((x, y))
    return positions


# ---------------------------------------------------------------------------
# Schema normalisation: converts any accepted input shape to a full initialGraph
# ---------------------------------------------------------------------------
def unwrap(raw):
    """Unwrap common container keys so downstream logic sees a bare graph dict."""
    if isinstance(raw, dict):
        if "graph" in raw and isinstance(raw["graph"], dict):
            return raw["graph"]
        if "initialGraph" in raw and isinstance(raw["initialGraph"], dict):
            return raw["initialGraph"]
    return raw


def normalise_schema(raw):
    """Convert a minimal or fully-specified schema into a complete initialGraph.

    Accepts THREE input flavours:
      1. Minimal custom: {nodes:[{caption, properties}], relationships:[...]}
      2. Our editor's arrows-ish format with explicit caption + style.color
      3. Pure arrows.app format: caption empty, display text comes from
         labels[0]; node colour lives in style.node-color (kebab-case);
         radius may be inherited from a top-level style block.

    The caller (whether the editor's Import button or inject.py on the CLI)
    sees the same normalised output regardless of which flavour came in.
    """
    raw = unwrap(raw)

    raw_nodes = raw.get("nodes") or []
    raw_rels = raw.get("relationships") or []
    # Top-level style block in arrows.app holds graph-wide defaults like
    # `radius` and the giant set of styling keys. We preserve it opaquely
    # for round-tripping, but also peek at it to inherit defaults.
    top_style = raw.get("style") or {}
    default_radius_from_style = top_style.get("radius") if isinstance(top_style, dict) else None

    if not isinstance(raw_nodes, list):
        raise ValueError("'nodes' must be a list")
    if not isinstance(raw_rels, list):
        raise ValueError("'relationships' must be a list")

    positions = auto_layout(len(raw_nodes))
    caption_to_id = {}
    duplicate_captions = set()
    nodes = []

    for i, n in enumerate(raw_nodes):
        if not isinstance(n, dict):
            raise ValueError(f"Node {i} is not an object")

        # Caption derivation: arrows.app often emits caption="" and relies on
        # labels[0] for the display text. When caption is missing OR an empty
        # string, fall through to labels[0]. Our editor will continue to keep
        # caption populated internally, but we round-trip it correctly to
        # arrows-style on output (see export below).
        raw_caption = n.get("caption")
        caption = raw_caption if (raw_caption and raw_caption.strip()) else None
        if not caption:
            labs = n.get("labels") or []
            caption = labs[0] if labs else None
        if not caption:
            raise ValueError(f"Node {i} is missing both 'caption' and 'labels'")

        nid = n.get("id") or f"n{i}"
        # Track duplicates but don't fail yet — duplicate captions are only a
        # problem if a relationship tries to resolve by caption later.
        if caption in caption_to_id and caption_to_id[caption] != nid:
            duplicate_captions.add(caption)
        else:
            caption_to_id[caption] = nid

        pos = n.get("position") or {"x": positions[i][0], "y": positions[i][1]}
        style = n.get("style") or {}
        # Colour: accept BOTH our internal `color` and arrows.app's
        # `node-color` (kebab-case). Internal form wins if both are set.
        color = (
            style.get("color")
            or style.get("node-color")
            or COLORS[i % len(COLORS)]
        )
        # Radius: node-level radius wins, then fall back to the graph-wide
        # default in the top-level style block, then to our internal default.
        radius = (
            style.get("radius")
            or default_radius_from_style
            or DEFAULT_RADIUS
        )
        props = n.get("properties") or {}

        # Label normalisation: the labels array always starts with caption,
        # followed by any additional labels (Neo4j multi-label syntax
        # :Account:Internal). This invariant keeps the editor UI, the Cypher
        # export, and the arrows.app export consistent with each other.
        raw_labels = n.get("labels") or [caption]
        seen = set()
        extras = []
        for lab in raw_labels:
            if not isinstance(lab, str):
                continue
            lab = lab.strip()
            if not lab or lab == caption or lab in seen:
                continue
            seen.add(lab)
            extras.append(lab)
        labels = [caption] + extras

        nodes.append({
            "id": nid,
            "position": {"x": pos["x"], "y": pos["y"]},
            "caption": caption,
            "labels": labels,
            "properties": props,
            "style": {"color": color, "radius": radius},
        })

    rels = []
    for i, r in enumerate(raw_rels):
        if not isinstance(r, dict):
            raise ValueError(f"Relationship {i} is not an object")

        rtype = r.get("type")
        if not rtype:
            raise ValueError(f"Relationship {i} is missing 'type'")

        # Explicit ids win. Only fall back to caption lookup when the caller
        # didn't supply them. Duplicate captions are only fatal if actually
        # consulted.
        from_id = r.get("fromId")
        if not from_id:
            from_caption = r.get("from")
            if from_caption in duplicate_captions:
                raise ValueError(
                    f"Relationship {i} ({rtype}): 'from' references duplicate "
                    f"caption '{from_caption}'. Use explicit fromId instead."
                )
            from_id = caption_to_id.get(from_caption)

        to_id = r.get("toId")
        if not to_id:
            to_caption = r.get("to")
            if to_caption in duplicate_captions:
                raise ValueError(
                    f"Relationship {i} ({rtype}): 'to' references duplicate "
                    f"caption '{to_caption}'. Use explicit toId instead."
                )
            to_id = caption_to_id.get(to_caption)

        if not from_id:
            raise ValueError(
                f"Relationship {i} ({rtype}): cannot resolve 'from' / 'fromId'. "
                f"Known captions: {list(caption_to_id.keys())}"
            )
        if not to_id:
            raise ValueError(
                f"Relationship {i} ({rtype}): cannot resolve 'to' / 'toId'. "
                f"Known captions: {list(caption_to_id.keys())}"
            )

        rid = r.get("id") or f"r{i}"
        rels.append({
            "id": rid,
            "type": rtype,
            "fromId": from_id,
            "toId": to_id,
            "properties": r.get("properties") or {},
        })

    return {"nodes": nodes, "relationships": rels}


# ---------------------------------------------------------------------------
# JS emission (same single-line-per-node format the editor expects)
# ---------------------------------------------------------------------------
def to_js_initial_graph(ig):
    lines = ["const initialGraph = {", "  nodes: ["]
    for n in ig["nodes"]:
        lines.append(
            f'    {{ id: "{n["id"]}", position: {json.dumps(n["position"])}, '
            f'caption: "{n["caption"]}", labels: {json.dumps(n["labels"])}, '
            f'properties: {json.dumps(n["properties"])}, style: {json.dumps(n["style"])} }},'
        )
    lines.append("  ],")
    lines.append("  relationships: [")
    for r in ig["relationships"]:
        lines.append(
            f'    {{ id: "{r["id"]}", type: "{r["type"]}", '
            f'fromId: "{r["fromId"]}", toId: "{r["toId"]}", '
            f'properties: {json.dumps(r["properties"])} }},'
        )
    lines.append("  ],")
    lines.append("  style: {},")
    lines.append("};")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Input resolution
# ---------------------------------------------------------------------------
def resolve_input(arg):
    """Turn the user's argument into a raw parsed JSON dict + a source label.

    Tries in order:
      - arg is a readable file path
      - arg matches a reference model filename (references/<arg>.json or references/<arg>)
      - arg matches a reference model's `id` field (scans references/*.json)

    Returns (raw_dict, source_label, is_reference_model).
    """
    # 1. Explicit file path (absolute, relative, or just existing)
    if os.path.exists(arg):
        with open(arg) as f:
            return json.load(f), arg, False

    # 2. Reference model by filename
    if os.path.isdir(REFERENCES_DIR):
        candidate_id = os.path.join(REFERENCES_DIR, f"{arg}.json")
        if os.path.exists(candidate_id):
            with open(candidate_id) as f:
                return json.load(f), candidate_id, True
        candidate_file = os.path.join(REFERENCES_DIR, arg)
        if os.path.exists(candidate_file):
            with open(candidate_file) as f:
                return json.load(f), candidate_file, True

        # 3. Reference model by id field (handles cases where filename differs
        #    from the id — e.g. fraud-event-sequence lives in
        #    fraud-event-sequence-model.json)
        for fname in sorted(os.listdir(REFERENCES_DIR)):
            if not fname.endswith(".json") or fname == "model-index.json":
                continue
            fpath = os.path.join(REFERENCES_DIR, fname)
            try:
                with open(fpath) as f:
                    data = json.load(f)
            except (json.JSONDecodeError, OSError):
                continue
            if isinstance(data, dict) and data.get("id") == arg:
                return data, fpath, True

    # 4. Not found
    hint = ""
    if os.path.isdir(REFERENCES_DIR):
        hint = " Run with --list to see reference model IDs."
    raise FileNotFoundError(f"Could not resolve '{arg}' as a file or reference model id.{hint}")


def read_stdin_json():
    if sys.stdin.isatty():
        print("ERROR: No input. Pipe schema JSON on stdin, pass a file path, or pass a reference model id.", file=sys.stderr)
        print_usage(sys.stderr)
        sys.exit(1)
    try:
        return json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON on stdin: {e}", file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# Output format converters
# ---------------------------------------------------------------------------
# arrows.app's default style block. We emit this on every export so that
# pasting our JSON into https://arrows.app produces a sensible starting look,
# and so that schemas exported from arrows.app and re-injected by us preserve
# their look on a future export.
ARROWS_DEFAULT_STYLE = {
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
}


def to_arrows_app(ig):
    """Produce arrows.app-compatible JSON from our normalised graph.

    Conventions arrows.app uses (which differ from our internal shape):
      - No top-level {graph: ...} wrapper. style/nodes/relationships sit at the root.
      - caption is OPTIONAL and typically empty when it would equal labels[0];
        the display text comes from labels[0]. We follow that rule here:
        emit caption="" when caption == labels[0], otherwise pass the explicit
        caption through. This keeps round-trips byte-stable and preserves any
        unusual case where the user set a caption deliberately distinct from
        the first label.
      - Per-node style uses kebab-case (`node-color`, not `color`).
    """
    nodes_out = []
    for n in ig["nodes"]:
        labels = list(n["labels"])
        primary = labels[0] if labels else ""
        # Emit caption only when it diverges from the primary label
        caption_out = "" if n["caption"] == primary else n["caption"]
        nodes_out.append({
            "id": n["id"],
            "position": n["position"],
            "caption": caption_out,
            "style": {
                "node-color": n["style"]["color"],
                "radius": n["style"]["radius"],
            },
            "labels": labels,
            "properties": dict(n["properties"]),
        })
    rels_out = [
        {
            "id": r["id"],
            "type": r["type"],
            "style": {},
            "properties": dict(r["properties"]),
            "fromId": r["fromId"],
            "toId": r["toId"],
        }
        for r in ig["relationships"]
    ]
    return {
        "style": dict(ARROWS_DEFAULT_STYLE),
        "nodes": nodes_out,
        "relationships": rels_out,
    }


# ---------------------------------------------------------------------------
# SVG renderer — a static rendering for environments where the .jsx can't run
# ---------------------------------------------------------------------------
def _xml_escape(s):
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def render_svg(ig):
    """Render the schema as an SVG that mirrors the editor's dark-theme canvas.

    The point is to be useful in environments where the .jsx cannot render
    (CLI tools, API users, README screenshots, slide decks). It mirrors the
    editor's visual conventions closely — same dark background, label pills
    below circles, fanned parallel relationships, monospace property text —
    so a viewer can pattern-match between SVG and live editor.
    """
    nodes = ig["nodes"]
    rels = ig["relationships"]
    if not nodes:
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" width="320" height="120">'
            '<rect width="320" height="120" fill="#0b1121"/>'
            '<text x="160" y="60" text-anchor="middle" fill="#94a3b8" '
            'font-family="sans-serif" font-size="14">Empty schema</text></svg>'
        )

    # Compute bounding box with padding for pills, properties, and rel labels
    margin = 140
    xs = [n["position"]["x"] for n in nodes]
    ys = [n["position"]["y"] for n in nodes]
    radii = [n["style"]["radius"] for n in nodes]
    x_min = min(x - r for x, r in zip(xs, radii)) - margin
    y_min = min(y - r for y, r in zip(ys, radii)) - margin
    x_max = max(x + r for x, r in zip(xs, radii)) + margin
    y_max = max(y + r for y, r in zip(ys, radii)) + margin
    width = max(400, x_max - x_min)
    height = max(300, y_max - y_min)

    by_id = {n["id"]: n for n in nodes}

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="{x_min:.1f} {y_min:.1f} {width:.1f} {height:.1f}" '
        f'width="{int(width)}" height="{int(height)}" '
        f'font-family="-apple-system, BlinkMacSystemFont, sans-serif">',
        f'<rect x="{x_min:.1f}" y="{y_min:.1f}" width="{width:.1f}" height="{height:.1f}" fill="#0b1121"/>',
        '<defs><marker id="arrow" markerWidth="10" markerHeight="7" refX="9" refY="3.5" '
        'orient="auto" markerUnits="strokeWidth">'
        '<polygon points="0 0, 10 3.5, 0 7" fill="#64748b"/></marker></defs>',
    ]

    # Group rels by node-pair to fan parallel ones (matches the editor)
    pair_groups = {}
    for r in rels:
        key = tuple(sorted([r["fromId"], r["toId"]]))
        pair_groups.setdefault(key, []).append(r["id"])

    # Relationships first (so nodes draw on top)
    for r in rels:
        f = by_id.get(r["fromId"])
        t = by_id.get(r["toId"])
        if not f or not t:
            continue
        type_str = _xml_escape(r["type"])
        type_w = max(40, len(r["type"]) * 6.4 + 12)

        if f["id"] == t["id"]:
            # Self-loop: simple teardrop above the node
            cx, cy = f["position"]["x"], f["position"]["y"]
            rad = f["style"]["radius"]
            parts.append(
                f'<path d="M {cx - rad*0.4:.1f} {cy - rad*0.95:.1f} '
                f'C {cx - rad*1.4:.1f} {cy - rad*2.4:.1f}, '
                f'{cx + rad*1.4:.1f} {cy - rad*2.4:.1f}, '
                f'{cx + rad*0.4:.1f} {cy - rad*0.95:.1f}" '
                f'fill="none" stroke="#64748b" stroke-width="1.5" marker-end="url(#arrow)"/>'
            )
            label_x, label_y = cx, cy - rad * 1.9
        else:
            fx, fy = f["position"]["x"], f["position"]["y"]
            tx, ty = t["position"]["x"], t["position"]["y"]
            dx, dy = tx - fx, ty - fy
            dist = (dx * dx + dy * dy) ** 0.5 or 1
            ux, uy = dx / dist, dy / dist
            # Trim line to node boundaries
            x1 = fx + ux * f["style"]["radius"]
            y1 = fy + uy * f["style"]["radius"]
            x2 = tx - ux * t["style"]["radius"]
            y2 = ty - uy * t["style"]["radius"]
            siblings = pair_groups[tuple(sorted([f["id"], t["id"]]))]
            idx = siblings.index(r["id"])
            n_sib = len(siblings)
            sign = 1 if r["fromId"] == sorted([f["id"], t["id"]])[0] else -1
            lane = ((idx - (n_sib - 1) / 2) * 36 * sign) if n_sib > 1 else 0
            nx_, ny_ = -uy, ux
            ep_off = lane * 0.45
            x1o, y1o = x1 + nx_ * ep_off, y1 + ny_ * ep_off
            x2o, y2o = x2 + nx_ * ep_off, y2 + ny_ * ep_off
            mx = (x1o + x2o) / 2 + nx_ * lane * 0.9
            my = (y1o + y2o) / 2 + ny_ * lane * 0.9
            if lane != 0:
                parts.append(
                    f'<path d="M {x1o:.1f} {y1o:.1f} Q {mx:.1f} {my:.1f} {x2o:.1f} {y2o:.1f}" '
                    f'fill="none" stroke="#64748b" stroke-width="1.5" marker-end="url(#arrow)"/>'
                )
            else:
                parts.append(
                    f'<line x1="{x1o:.1f}" y1="{y1o:.1f}" x2="{x2o:.1f}" y2="{y2o:.1f}" '
                    f'stroke="#64748b" stroke-width="1.5" marker-end="url(#arrow)"/>'
                )
            label_x, label_y = mx, my

        parts.append(
            f'<rect x="{label_x - type_w/2:.1f}" y="{label_y - 16:.1f}" '
            f'width="{type_w:.1f}" height="16" rx="4" fill="#0b1121" opacity="0.85"/>'
        )
        parts.append(
            f'<text x="{label_x:.1f}" y="{label_y - 8:.1f}" text-anchor="middle" '
            f'dominant-baseline="central" fill="#e2e8f0" font-size="10" '
            f'font-family="monospace" font-weight="600">{type_str}</text>'
        )

    # Nodes
    for n in nodes:
        cx, cy = n["position"]["x"], n["position"]["y"]
        rad = n["style"]["radius"]
        color = n["style"]["color"]
        caption = _xml_escape(n["caption"])
        parts.append(
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{rad}" '
            f'fill="{color}26" stroke="{color}" stroke-width="2"/>'
        )
        font_size = 11 if len(n["caption"]) > 10 else 13
        parts.append(
            f'<text x="{cx:.1f}" y="{cy:.1f}" text-anchor="middle" '
            f'dominant-baseline="central" fill="#ffffff" font-size="{font_size}" '
            f'font-weight="700" letter-spacing="0.5">{caption.upper()}</text>'
        )
        # Additional-label pills
        extras = n["labels"][1:] if len(n["labels"]) > 1 else []
        if extras:
            char_w = 6
            gap = 4
            widths = [max(24, len(l) * char_w + 12) for l in extras]
            total_w = sum(widths) + gap * (len(extras) - 1)
            row_y = cy + rad + 8
            cursor_x = cx - total_w / 2
            for label, w in zip(extras, widths):
                parts.append(
                    f'<rect x="{cursor_x:.1f}" y="{row_y:.1f}" width="{w}" height="14" rx="7" '
                    f'fill="{color}40" stroke="{color}" stroke-width="0.75"/>'
                )
                parts.append(
                    f'<text x="{cursor_x + w/2:.1f}" y="{row_y + 7:.1f}" text-anchor="middle" '
                    f'dominant-baseline="central" fill="#ffffff" font-size="9" '
                    f'font-family="monospace" font-weight="600">:{_xml_escape(label)}</text>'
                )
                cursor_x += w + gap
        # Properties
        pill_row_h = 18 if extras else 0
        for i, (k, v) in enumerate(n["properties"].items()):
            text_y = cy + rad + 14 + pill_row_h + i * 14
            parts.append(
                f'<text x="{cx:.1f}" y="{text_y:.1f}" text-anchor="middle" '
                f'fill="#cbd5e1" font-size="10" font-family="monospace">'
                f'{_xml_escape(k)}: {_xml_escape(v)}</text>'
            )

    parts.append("</svg>")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Main injection routine
# ---------------------------------------------------------------------------
def inject(raw_schema, output_path, source_label=None, is_reference_model=False):
    ig = normalise_schema(raw_schema)

    if not os.path.exists(TEMPLATE_PATH):
        print(f"ERROR: Editor template not found at {TEMPLATE_PATH}", file=sys.stderr)
        sys.exit(1)

    with open(TEMPLATE_PATH, "r") as f:
        template = f.read()

    new_initial = to_js_initial_graph(ig)
    pattern = r"const initialGraph = \{[\s\S]*?\n\};"
    if not re.search(pattern, template):
        print("ERROR: Could not find 'const initialGraph = {...};' in template.", file=sys.stderr)
        sys.exit(1)

    output = re.sub(pattern, new_initial, template, count=1)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w") as f:
        f.write(output)

    # Companion files share the .jsx basename. Three outputs from one schema:
    #   .jsx  — the interactive editor (renders in claude.ai artifacts)
    #   .json — arrows.app-compatible schema (paste into https://arrows.app)
    #   .svg  — static rendering for environments without a JSX renderer
    base = os.path.splitext(output_path)[0]
    json_path = base + ".json"
    svg_path = base + ".svg"

    with open(json_path, "w") as f:
        json.dump(to_arrows_app(ig), f, indent=2)

    with open(svg_path, "w") as f:
        f.write(render_svg(ig))

    # Report
    if is_reference_model and source_label:
        meta = raw_schema if isinstance(raw_schema, dict) else {}
        name = meta.get("name", os.path.basename(source_label))
        desc = meta.get("description", "")
        source = desc.split("Source: ")[-1] if "Source: " in desc else ""
        print(f"Model:  {name}")
        if source:
            print(f"Source: {source}")
    print(f"Nodes:  {len(ig['nodes'])}")
    print(f"Rels:   {len(ig['relationships'])}")
    print(f"Editor: {output_path}")
    print(f"Schema: {json_path}")
    print(f"Image:  {svg_path}")


def print_usage(stream=sys.stdout):
    print("Usage:", file=stream)
    print("  python3 inject.py <reference-model-id>       [output.jsx]", file=stream)
    print("  python3 inject.py <path/to/schema.json>      [output.jsx]", file=stream)
    print("  cat schema.json | python3 inject.py          [output.jsx]", file=stream)
    print("  python3 inject.py --list", file=stream)


def main():
    args = sys.argv[1:]

    if args and args[0] in ("-h", "--help"):
        print(__doc__)
        print_usage()
        return

    if args and args[0] == "--list":
        print_reference_list()
        return

    # Optional trailing .jsx output path
    output_path = DEFAULT_OUTPUT
    if args and args[-1].endswith(".jsx"):
        output_path = args[-1]
        args = args[:-1]

    if len(args) > 1:
        print("ERROR: Too many arguments.", file=sys.stderr)
        print_usage(sys.stderr)
        sys.exit(1)

    source_label = None
    is_reference_model = False

    if len(args) == 1 and args[0] != "-":
        try:
            raw_schema, source_label, is_reference_model = resolve_input(args[0])
        except FileNotFoundError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"ERROR: Invalid JSON in input file: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        raw_schema = read_stdin_json()

    try:
        inject(raw_schema, output_path, source_label=source_label,
               is_reference_model=is_reference_model)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
