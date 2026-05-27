#!/usr/bin/env python3
"""Extract Cypher examples selected by a test manifest."""
from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

DEFAULT_MANIFEST = Path("neo4j-vector-index-skill/tests/cypher-examples.json")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


@dataclass
class CypherExample:
    manifest: str
    file: str
    block_number: int
    cypher_block_number: int
    start_line: int
    end_line: int
    heading: str
    name: str
    setup: str | None
    minVersion: str | None
    parameters: dict[str, Any]
    query: str


def load_manifest(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}: invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{path}: manifest must be a JSON object")
    if not data.get("skill"):
        raise ValueError(f"{path}: missing required field: skill")
    if not isinstance(data.get("examples"), list):
        raise ValueError(f"{path}: missing required list field: examples")
    return data


def strip_cypher_version_pragma(query: str) -> str:
    lines = query.splitlines()
    while lines and not lines[0].strip():
        lines.pop(0)
    if lines and re.match(r"^CYPHER\s+\S+\s*$", lines[0].strip(), re.I):
        lines.pop(0)
    return "\n".join(lines).strip()


def iter_cypher_blocks(path: Path):
    lines = path.read_text(encoding="utf-8").splitlines()
    current_heading = ""
    block_number = 0
    cypher_block_number = 0
    in_fence = False
    fence_info = ""
    fence_start = 0
    fence_heading = ""
    fence_lines: list[str] = []

    for idx, line in enumerate(lines, start=1):
        if not in_fence:
            heading = HEADING_RE.match(line)
            if heading:
                current_heading = heading.group(2).strip()
                continue
            if line.startswith("```"):
                in_fence = True
                block_number += 1
                fence_info = line[3:].strip()
                fence_start = idx
                fence_heading = current_heading
                fence_lines = []
                if fence_info.split(maxsplit=1)[0:1] == ["cypher"]:
                    cypher_block_number += 1
            continue

        if line.startswith("```"):
            if fence_info.split(maxsplit=1)[0:1] == ["cypher"]:
                yield {
                    "block_number": block_number,
                    "cypher_block_number": cypher_block_number,
                    "start_line": fence_start,
                    "end_line": idx,
                    "heading": fence_heading,
                    "query": "\n".join(fence_lines).strip(),
                }
            in_fence = False
            fence_info = ""
            fence_heading = ""
            fence_lines = []
            continue

        fence_lines.append(line)


def select_block(skill_file: Path, spec: dict[str, Any]) -> dict[str, Any]:
    heading = spec.get("heading")
    cypher_block = spec.get("cypherBlock")
    if not isinstance(heading, str) or not heading:
        raise ValueError("example missing string field: heading")
    if not isinstance(cypher_block, int) or cypher_block < 1:
        raise ValueError(f"example {spec.get('name', '<unnamed>')}: cypherBlock must be a positive integer")

    matches = [block for block in iter_cypher_blocks(skill_file) if block["heading"] == heading]
    if not matches:
        raise ValueError(f"{skill_file}: no Cypher blocks found under heading {heading!r}")
    if cypher_block > len(matches):
        raise ValueError(
            f"{skill_file}: heading {heading!r} has {len(matches)} Cypher block(s), requested {cypher_block}"
        )
    return matches[cypher_block - 1]


def extract_from_manifest(manifest_path: Path) -> list[CypherExample]:
    manifest = load_manifest(manifest_path)
    skill_file = Path(manifest["skill"])
    if not skill_file.is_absolute():
        skill_file = manifest_path.parent.parent.parent / skill_file if manifest_path.parts[-3:-1] == ("neo4j-vector-index-skill", "tests") else Path.cwd() / skill_file
    skill_file = skill_file.resolve()
    if not skill_file.exists():
        raise ValueError(f"{manifest_path}: skill file does not exist: {skill_file}")

    examples: list[CypherExample] = []
    seen_names: set[str] = set()
    for spec in manifest["examples"]:
        if not isinstance(spec, dict):
            raise ValueError(f"{manifest_path}: each example must be an object")
        name = spec.get("name")
        if not isinstance(name, str) or not name:
            raise ValueError(f"{manifest_path}: example missing string field: name")
        if name in seen_names:
            raise ValueError(f"{manifest_path}: duplicate example name: {name}")
        seen_names.add(name)

        block = select_block(skill_file, spec)
        query = str(block["query"])
        if spec.get("dropCypherVersionPragma") is True:
            query = strip_cypher_version_pragma(query)
        parameters = spec.get("parameters", {})
        if not isinstance(parameters, dict):
            raise ValueError(f"{manifest_path}: example {name}: parameters must be an object")

        examples.append(
            CypherExample(
                manifest=str(manifest_path),
                file=str(skill_file),
                block_number=int(block["block_number"]),
                cypher_block_number=int(block["cypher_block_number"]),
                start_line=int(block["start_line"]),
                end_line=int(block["end_line"]),
                heading=str(block["heading"]),
                name=name,
                setup=spec.get("setup"),
                minVersion=spec.get("minVersion"),
                parameters=parameters,
                query=query,
            )
        )
    return examples


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract Cypher examples selected by a test manifest")
    parser.add_argument("--manifest", action="append", default=[], help="Cypher example manifest to read")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    args = parser.parse_args()

    try:
        manifests = [Path(p) for p in (args.manifest or [str(DEFAULT_MANIFEST)])]
        examples: list[CypherExample] = []
        for manifest in manifests:
            examples.extend(extract_from_manifest(manifest))
        data = [asdict(example) for example in examples]
        print(json.dumps(data, indent=2 if args.pretty else None))
        return 0
    except ValueError as exc:
        print(f"ERROR: {exc}", flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
