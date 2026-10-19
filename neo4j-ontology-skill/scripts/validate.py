# /// script
# requires-python = ">=3.9"
# dependencies = ["jsonschema", "pyyaml"]
# ///
"""Validate a Neo4j Ontology Graph Specification v1 document against the vendored JSON Schema.

Usage: validate.py <document> [--schema <path>]

Document may be .json, .yaml, or .yml (sniffed by extension).

Exit codes:
  0 - document is valid
  1 - document failed schema validation (all violations printed)
  2 - document could not be parsed (bad YAML/JSON) or read
"""

import argparse
import json
import sys
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

DEFAULT_SCHEMA = (
    Path(__file__).resolve().parent.parent / "assets" / "ontology-graph-spec.schema.json"
)

JSON_SUFFIXES = {".json"}
YAML_SUFFIXES = {".yaml", ".yml"}


def load_document(path: Path):
    """Parse the document by extension. Raises ValueError on unknown extension."""
    text = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()
    if suffix in JSON_SUFFIXES:
        return json.loads(text)
    if suffix in YAML_SUFFIXES:
        return yaml.safe_load(text)
    raise ValueError(
        f"unsupported file extension '{suffix}': expected one of "
        f"{sorted(JSON_SUFFIXES | YAML_SUFFIXES)}"
    )


def format_path(error) -> str:
    """Render the instance path, e.g. nodes.Actor.properties.id; '$' for the root."""
    parts = [str(p) for p in error.absolute_path]
    return ".".join(parts) if parts else "$"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate a Neo4j Ontology Graph Specification v1 document."
    )
    parser.add_argument("document", help="Path to a .json, .yaml, or .yml ontology document")
    parser.add_argument(
        "--schema",
        default=str(DEFAULT_SCHEMA),
        help=f"Path to the JSON Schema (default: vendored {DEFAULT_SCHEMA.name})",
    )
    args = parser.parse_args()

    doc_path = Path(args.document)
    schema_path = Path(args.schema)

    try:
        document = load_document(doc_path)
    except FileNotFoundError:
        print(f"error: file not found: {doc_path}", file=sys.stderr)
        return 2
    except (json.JSONDecodeError, yaml.YAMLError) as exc:
        print(f"error: cannot parse {doc_path}: {exc}", file=sys.stderr)
        return 2
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"error: schema file not found: {schema_path}", file=sys.stderr)
        return 2
    except json.JSONDecodeError as exc:
        print(f"error: cannot parse schema {schema_path}: {exc}", file=sys.stderr)
        return 2

    # No format checker is passed: 'format' keywords stay annotations, per spec.
    validator = Draft202012Validator(schema)
    errors = sorted(
        validator.iter_errors(document),
        key=lambda e: (list(e.absolute_path), e.validator or ""),
    )

    if errors:
        print(f"{doc_path}: INVALID — {len(errors)} schema violation(s)", file=sys.stderr)
        for error in errors:
            print(
                f"  - at {format_path(error)}: [{error.validator}] {error.message}",
                file=sys.stderr,
            )
        return 1

    nodes = document.get("nodes") or {}
    relationships = document.get("relationships") or {}
    print(
        f"{doc_path}: valid — {len(nodes)} node(s), {len(relationships)} relationship(s)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
