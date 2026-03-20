#!/usr/bin/env python3
"""
extract-changelog.py — Parse deprecations-additions-removals-compatibility.adoc
from the docs-cypher submodule and emit a Markdown changelog summary.

Usage:
  python scripts/extract-changelog.py \
    --src docs-cypher/modules/ROOT/pages/deprecations-additions-removals-compatibility.adoc \
    --out neo4j-cypher-authoring-skill/changelog.md \
    [--since 2026.01]   # optional: only emit entries for this version or newer
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Asciidoc cleanup helpers
# ---------------------------------------------------------------------------

# Labels used in feature cells
_LABEL_RE = re.compile(r"label:\w+\[\]")
# xref: cross-references → strip
_XREF_RE = re.compile(r"xref:[^\[]+\[([^\]]*)\]")
# link: external links → keep display text
_LINK_RE = re.compile(r"link:[^\[]+\[([^\]]*)\]")
# AsciiDoc inline backtick pass-through `++...++` → backtick-quote
_PASSTHROUGH_RE = re.compile(r"\+\+([^+]+)\+\+")
# {attr} attribute references
_ATTR_RE = re.compile(r"\{[^}]+\}")
# Role/options annotations on source blocks
_ROLE_RE = re.compile(r'\[source[^\]]*\]')
# Code-block delimiter
_DELIM_RE = re.compile(r"^-{4,}$")


def clean_text(line: str) -> str:
    """Strip AsciiDoc markup from a text line, leaving readable plain text."""
    line = _LABEL_RE.sub("", line)
    # Strip [[anchor]] inline anchors
    line = re.sub(r"\[\[[^\]]+\]\]", "", line)
    line = _XREF_RE.sub(r"\1", line)
    line = _LINK_RE.sub(r"\1", line)
    line = _PASSTHROUGH_RE.sub(r"`\1`", line)
    line = _ATTR_RE.sub("", line)
    # Remove leading `a|` cell markers
    line = re.sub(r"^a?\|", "", line)
    # Remove trailing ` |` (end of table row in single-column lines)
    line = re.sub(r"\s*\|$", "", line)
    return line.strip()


def strip_adoc_source_block(lines: list[str], start: int) -> tuple[list[str], int]:
    """
    Starting just after a [source,...] annotation, consume the ---- block.
    Returns (code_lines, next_index).
    """
    code: list[str] = []
    i = start
    # skip the opening ----
    if i < len(lines) and _DELIM_RE.match(lines[i].rstrip()):
        i += 1
    while i < len(lines):
        raw = lines[i].rstrip()
        if _DELIM_RE.match(raw):
            i += 1
            break
        code.append(raw)
        i += 1
    return code, i


# ---------------------------------------------------------------------------
# Entry dataclass (plain dict is fine for simplicity)
# ---------------------------------------------------------------------------


def make_entry(version: str, category: str, details: str, code_blocks: list[str]) -> dict:
    return {
        "version": version,
        "category": category,
        "details": details.strip(),
        "code_blocks": code_blocks,
    }


# ---------------------------------------------------------------------------
# Changelog section categories
# ---------------------------------------------------------------------------

# Map AsciiDoc subsection heading patterns to output categories
_SECTION_CATEGORY: dict[str, str] = {
    "new": "Additions",
    "added": "Additions",
    "updated": "Additions",
    "deprecated": "Deprecations",
    "removed": "Removals",
    "restricted": "Removals",
}

_SUBSECTION_RE = re.compile(
    r"^===\s+(Removed|Deprecated|Restricted|Updated|New|Added)\s+in\s+",
    re.IGNORECASE,
)

_VERSION_RE = re.compile(r"^==\s+Neo4j\s+([\d.]+)")


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


def parse_changelog(src: Path) -> list[dict]:
    """
    Parse the adoc changelog file and return a list of entry dicts.

    Table structure (two-column):
      a| <feature cell: labels + optional code blocks>
      | <details cell: human-readable description>

    Each `a| ... | ...` pair is ONE changelog entry. The `a|` cell carries
    code examples; the `|` cell carries the description text.
    """
    text = src.read_text(encoding="utf-8")
    lines = text.splitlines()

    entries: list[dict] = []
    current_version: str = ""
    current_category: str = ""
    in_table = False
    in_feature_cell = False   # inside the `a|` feature cell (code examples)
    in_details_cell = False   # inside the `|` details cell (description)
    row_codes: list[str] = []    # code blocks for current row
    row_details: list[str] = []  # detail text lines for current row

    def flush_row():
        """Emit one entry from the accumulated row_codes + row_details."""
        if current_version and current_category and (row_codes or row_details):
            details = " ".join(
                clean_text(l) for l in row_details if clean_text(l)
            )
            entries.append(make_entry(current_version, current_category, details, row_codes[:]))
        row_codes.clear()
        row_details.clear()

    i = 0
    while i < len(lines):
        raw = lines[i]
        stripped = raw.strip()

        # --- Version heading ---
        vm = _VERSION_RE.match(stripped)
        if vm:
            flush_row()
            in_table = False
            in_feature_cell = False
            in_details_cell = False
            current_version = vm.group(1)
            current_category = ""
            i += 1
            continue

        # --- Subsection heading ---
        sm = _SUBSECTION_RE.match(stripped)
        if sm:
            flush_row()
            in_table = False
            in_feature_cell = False
            in_details_cell = False
            keyword = sm.group(1).lower()
            current_category = _SECTION_CATEGORY.get(keyword, "")
            i += 1
            continue

        # Skip if no version/category context yet
        if not current_version or not current_category:
            i += 1
            continue

        # --- Table delimiter (start or end) ---
        if re.match(r"^\|={3,}", stripped):
            if not in_table:
                in_table = True
                in_feature_cell = False
                in_details_cell = False
                i += 1
                continue
            else:
                # Table ends — flush the last row
                flush_row()
                in_table = False
                in_feature_cell = False
                in_details_cell = False
                i += 1
                continue

        if not in_table:
            i += 1
            continue

        # --- Skip table header row ---
        if stripped.startswith("| Feature") and "| Details" in stripped:
            i += 1
            continue

        # Also skip standalone `| Feature` or `| Details` header column lines
        if stripped in ("| Feature", "| Details"):
            i += 1
            continue

        # --- [source,...] annotation → consume entire code block ---
        if _ROLE_RE.match(stripped):
            # Extract the language from the source annotation (e.g. [source, cypher])
            lang_match = re.search(r"\[source,\s*([a-zA-Z0-9_+\-]+)", stripped)
            lang = (lang_match.group(1) if lang_match else "").strip()
            # Skip non-cypher code blocks (e.g. csv examples); still consume them
            skip_code = lang.lower() not in ("cypher", "", "role=noheader")
            i += 1
            code_lines, i = strip_adoc_source_block(lines, i)
            if in_feature_cell and code_lines and not skip_code:
                row_codes.append("```cypher\n" + "\n".join(code_lines) + "\n```")
            continue

        # --- New row: `a|` starts the feature cell ---
        # This also flushes any prior completed row
        if stripped.startswith("a|"):
            # If we previously had a complete row (codes + details), flush it now
            # A row is complete when we've seen at least the details cell.
            if in_details_cell:
                flush_row()
            elif in_feature_cell and not in_details_cell and (row_codes or row_details):
                # Previous row had only feature cell (no details cell seen yet) —
                # keep accumulating; new a| starts a new row so flush old one first
                flush_row()
            in_feature_cell = True
            in_details_cell = False
            remainder = stripped[2:].strip()
            if remainder:
                cleaned = clean_text(remainder)
                if cleaned:
                    row_details.append(cleaned)
            i += 1
            continue

        # --- Details cell: `| ...` (not `a|`, not `|===`) ---
        if stripped.startswith("|") and not stripped.startswith("|==="):
            # Transition from feature cell to details cell — same row
            in_feature_cell = False
            in_details_cell = True
            remainder = stripped[1:].strip()
            if remainder:
                row_details.append(remainder)
            i += 1
            continue

        # --- Continuation content ---
        if in_feature_cell:
            # Labels, blank lines, xref-only lines — we skip label lines
            cleaned = clean_text(stripped)
            if cleaned and not _LABEL_RE.fullmatch(stripped.strip()):
                row_details.append(cleaned)
        elif in_details_cell:
            if stripped:
                row_details.append(stripped)

        i += 1

    flush_row()
    return entries


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------


def render_markdown(entries: list[dict], since: Optional[str] = None) -> str:
    """Render parsed changelog entries to a Markdown string."""

    # Filter by version if requested
    if since:
        entries = [e for e in entries if _version_gte(e["version"], since)]

    # Group: category → version → list of entries
    category_order = ["Additions", "Deprecations", "Removals"]
    grouped: dict[str, dict[str, list[dict]]] = {c: {} for c in category_order}

    for entry in entries:
        cat = entry["category"]
        if cat not in grouped:
            continue
        ver = entry["version"]
        grouped[cat].setdefault(ver, []).append(entry)

    lines: list[str] = ["# Cypher Changelog Summary\n"]

    for cat in category_order:
        ver_map = grouped[cat]
        lines.append(f"## {cat}\n")
        if not ver_map:
            lines.append("_No entries._\n")
            continue
        for ver in sorted(ver_map.keys(), reverse=True):
            lines.append(f"### Neo4j {ver}\n")
            # Normalise details for all entries in this version group
            clean_entries = []
            for entry in ver_map[ver]:
                details = entry["details"] or ""
                details = _XREF_RE.sub(r"\1", details)
                details = _LINK_RE.sub(r"\1", details)
                details = details.strip()
                if not details and not entry["code_blocks"]:
                    continue
                if not details:
                    details = "_See source for details._"
                clean_entries.append({**entry, "details": details})

            # Deduplicate: remove entries whose details text is a strict prefix
            # of another entry's details text in the same group.
            final_entries = []
            all_details = [e["details"] for e in clean_entries]
            for i, entry in enumerate(clean_entries):
                d = entry["details"]
                is_superseded = any(
                    other.startswith(d) and other != d
                    for j, other in enumerate(all_details)
                    if j != i
                )
                if not is_superseded:
                    final_entries.append(entry)

            for entry in final_entries:
                lines.append(f"- {entry['details']}")
                for code in entry["code_blocks"]:
                    lines.append("")
                    lines.append("  " + code.replace("\n", "\n  "))
                    lines.append("")
            lines.append("")

    return "\n".join(lines)


def _version_gte(ver: str, since: str) -> bool:
    """Return True if ver >= since (compare as dot-separated integers)."""
    def parts(v: str) -> tuple[int, ...]:
        return tuple(int(x) for x in v.split(".") if x.isdigit())

    try:
        return parts(ver) >= parts(since)
    except (ValueError, TypeError):
        return True  # include on parse error


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Parse Neo4j changelog adoc and emit a Markdown summary."
    )
    parser.add_argument(
        "--src",
        required=True,
        help="Path to deprecations-additions-removals-compatibility.adoc",
    )
    parser.add_argument(
        "--out",
        required=True,
        help="Path to write the Markdown output file",
    )
    parser.add_argument(
        "--since",
        default=None,
        help="Only include entries for Neo4j versions >= this version (e.g. 2026.01)",
    )
    args = parser.parse_args()

    src = Path(args.src)
    out = Path(args.out)

    if not src.exists():
        print(f"ERROR: source file not found: {src}", file=sys.stderr)
        return 1

    entries = parse_changelog(src)
    md = render_markdown(entries, since=args.since)

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(md, encoding="utf-8")

    # Report counts after applying the --since filter (same logic as render_markdown)
    filtered = entries
    if args.since:
        filtered = [e for e in entries if _version_gte(e["version"], args.since)]

    total = len(filtered)
    additions = sum(1 for e in filtered if e["category"] == "Additions")
    deprecations = sum(1 for e in filtered if e["category"] == "Deprecations")
    removals = sum(1 for e in filtered if e["category"] == "Removals")

    print(
        f"Changelog written to {out} — "
        f"{total} entries: {additions} additions, {deprecations} deprecations, {removals} removals"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
