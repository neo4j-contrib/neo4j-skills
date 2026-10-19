# /// script
# requires-python = ">=3.9"
# dependencies = ["jsonschema", "pyyaml"]
# ///
"""Validate a Neo4j ontology document against the published JSON Schema.

Usage: validate.py <document> [--schema <path-or-url>]

Document may be .json, .yaml, or .yml (sniffed by extension).

Schema resolution order:
  1. --schema given: a local path if it exists on disk, else an http(s) URL
     to fetch. No fallback — an explicit schema must load or the run fails.
  2. The document's own `schema` field, when it is an http(s) URL.
  3. The published `current` alias.
  4. TRANSITIONAL: the raw schema from the neo4j/ontology-graph-spec repo (until the
     published URLs go live).

Exit codes:
  0 - document is valid
  1 - document failed schema validation (all violations printed)
  2 - document or schema could not be parsed / fetched
"""

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

# Published schema locations (Linear ONT-31). Not live yet — see fallback below.
SCHEMA_BASE_URL = "https://neo4j.com/docs/ontology-graph-spec/"
SCHEMA_VERSIONED_URL_TEMPLATE = SCHEMA_BASE_URL + "{version}/schema.json"  # immutable, e.g. .../1.0.0/schema.json
SCHEMA_CURRENT_URL = SCHEMA_BASE_URL + "current/schema.json"  # moving alias → newest stable

# TRANSITIONAL (pre-ONT-31): raw schema from the source repo, used while the
# published URLs above are not live. Remove once ONT-31 ships.
SCHEMA_REPO_FALLBACK_URL = (
    "https://raw.githubusercontent.com/neo4j/ontology-graph-spec/main/ontology-graph-spec.schema.json"
)

FETCH_TIMEOUT_SECONDS = 30

JSON_SUFFIXES = {".json"}
YAML_SUFFIXES = {".yaml", ".yml"}


def is_http_url(value) -> bool:
    return isinstance(value, str) and value.lower().startswith(("http://", "https://"))


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


def fetch_json(url: str):
    """Fetch a URL and parse it as JSON. Raises ValueError with the reason on failure."""
    request = urllib.request.Request(url, headers={"User-Agent": "neo4j-ontology-validate"})
    try:
        with urllib.request.urlopen(request, timeout=FETCH_TIMEOUT_SECONDS) as response:
            body = response.read()
    except (urllib.error.URLError, OSError) as exc:
        raise ValueError(f"fetch failed: {exc}") from exc
    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise ValueError(f"response is not valid JSON: {exc}") from exc


def resolve_schema(schema_arg, document):
    """Return (schema, source_label). Prints the error and exits 2 on total failure."""
    if schema_arg is not None:
        path = Path(schema_arg)
        if path.is_file():
            try:
                return json.loads(path.read_text(encoding="utf-8")), str(path)
            except (OSError, json.JSONDecodeError) as exc:
                print(f"error: cannot read schema {path}: {exc}", file=sys.stderr)
                sys.exit(2)
        if is_http_url(schema_arg):
            try:
                return fetch_json(schema_arg), schema_arg
            except ValueError as exc:
                print(f"error: cannot fetch schema {schema_arg}: {exc}", file=sys.stderr)
                sys.exit(2)
        print(
            f"error: --schema {schema_arg!r} is neither an existing file nor an http(s) URL",
            file=sys.stderr,
        )
        sys.exit(2)

    candidates = []
    doc_schema = document.get("schema") if isinstance(document, dict) else None
    if is_http_url(doc_schema):
        candidates.append(doc_schema)
    candidates.append(SCHEMA_CURRENT_URL)
    candidates.append(SCHEMA_REPO_FALLBACK_URL)  # TRANSITIONAL, pre-ONT-31

    tried = []
    for url in candidates:
        try:
            schema = fetch_json(url)
        except ValueError as exc:
            tried.append(f"  - {url}: {exc}")
            continue
        source = url if not tried else f"{url} (fallback: {candidates[0]} unavailable)"
        return schema, source

    print("error: could not fetch a schema from any source tried:", file=sys.stderr)
    print("\n".join(tried), file=sys.stderr)
    sys.exit(2)


def format_path(error) -> str:
    """Render the instance path, e.g. nodes.Actor.properties.id; '$' for the root."""
    parts = [str(p) for p in error.absolute_path]
    return ".".join(parts) if parts else "$"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate a Neo4j ontology document against the published JSON Schema."
    )
    parser.add_argument("document", help="Path to a .json, .yaml, or .yml ontology document")
    parser.add_argument(
        "--schema",
        default=None,
        help="Local path or http(s) URL of the JSON Schema (default: resolve from the "
        "document's `schema` field, then the published `current` alias)",
    )
    args = parser.parse_args()

    doc_path = Path(args.document)

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

    schema, schema_source = resolve_schema(args.schema, document)
    print(f"schema source: {schema_source}", file=sys.stderr)

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
