#!/usr/bin/env python3
"""Fetch the AuraDB graph schema and save it to schema.json.

Uses neo4j-graphrag get_structured_schema() to retrieve node properties,
relationship patterns, and index metadata. Enriches each STRING property with:
  - aura_data_type: Aura-compatible data_type value
  - low_cardinality: True if ≤ CARDINALITY_THRESHOLD distinct values exist
  - values: sorted list of distinct values (only when low_cardinality=True)
  - has_fulltext_index: True if a FULLTEXT index covers this property

Output: schema.json with keys: node_props, rel_props, relationships, metadata
"""

import json
import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass

try:
    import neo4j
except ImportError:
    sys.exit("neo4j package not found — run: uv add neo4j")

try:
    from neo4j_graphrag.schema import get_structured_schema
except ImportError:
    sys.exit("neo4j-graphrag not found — run: uv add neo4j-graphrag")

OUTPUT_PATH = Path(__file__).parent.parent / "schema.json"

# Properties with more distinct values than this are not enumerated
CARDINALITY_THRESHOLD = 50

NEO4J_TYPE_TO_AURA = {
    "STRING": "string",
    "INTEGER": "integer",
    "LONG": "integer",
    "FLOAT": "number",
    "DOUBLE": "number",
    "BOOLEAN": "boolean",
    "DATE": "string",
    "DATE_TIME": "string",
    "LOCAL_DATE_TIME": "string",
    "LOCAL_TIME": "string",
    "TIME": "string",
    "DURATION": "string",
    "POINT": "string",
    "LIST": "string",
    "MAP": "string",
}


def aura_type(neo4j_type: str) -> str:
    return NEO4J_TYPE_TO_AURA.get(neo4j_type.upper(), "string")


def main():
    uri = os.environ.get("NEO4J_URI")
    user = os.environ.get("NEO4J_USERNAME", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD")
    database = os.environ.get("NEO4J_DATABASE", "neo4j")

    if not uri or not password:
        sys.exit("ERROR: NEO4J_URI and NEO4J_PASSWORD must be set in .env or environment")

    driver = neo4j.GraphDatabase.driver(uri, auth=(user, password))
    try:
        driver.verify_connectivity()
        print(f"Connected: {uri}")

        print("Fetching schema (sample=1000)...")
        schema = get_structured_schema(driver, database=database, sample=1000)

        # Annotate aura_data_type early — cardinality filter depends on it
        for label, props in schema.get("node_props", {}).items():
            for p in props:
                p["aura_data_type"] = aura_type(p.get("type", ""))
        for rel_type, props in schema.get("rel_props", {}).items():
            for p in props:
                p["aura_data_type"] = aura_type(p.get("type", ""))

        # Fast data gate — exits before any expensive queries if DB is too empty
        node_count = _count_nodes(driver, database)
        schema.setdefault("metadata", {})["node_count"] = node_count
        _validate_data(schema, node_count)  # sys.exit(1) on failure; finally still runs

        # Vector indexes
        records, _, _ = driver.execute_query(
            "SHOW INDEXES YIELD name, type, labelsOrTypes, properties, state, options "
            "WHERE type = 'VECTOR'",
            database_=database,
        )
        schema["metadata"]["vector_index"] = [dict(r) for r in records]

        # Full-text indexes
        records, _, _ = driver.execute_query(
            "SHOW INDEXES YIELD name, type, labelsOrTypes, properties, state "
            "WHERE type = 'FULLTEXT'",
            database_=database,
        )
        schema["metadata"]["fulltext_index"] = [dict(r) for r in records]

        # Cardinality — one query per STRING property on nodes and relationships
        string_prop_count = sum(
            1 for props in schema.get("node_props", {}).values()
            for p in props if p.get("aura_data_type") == "string"
        ) + sum(
            1 for props in schema.get("rel_props", {}).values()
            for p in props if p.get("aura_data_type") == "string"
        )
        print(f"Checking cardinality for {string_prop_count} string properties...")
        _enrich_with_cardinality(driver, database, schema)

    finally:
        driver.close()

    # Cross-reference full-text index metadata with property entries
    _mark_fulltext_indexed_props(schema)

    with open(OUTPUT_PATH, "w") as f:
        json.dump(schema, f, indent=2, default=str)

    print(f"Schema saved → {OUTPUT_PATH}")
    _print_gitignore_warning()
    _print_summary(schema)


# ── Data gate ────────────────────────────────────────────────────────────────

def _count_nodes(driver, database: str) -> int:
    # LIMIT 2 stops the scan as soon as the minimum is satisfied
    records, _, _ = driver.execute_query(
        "MATCH (n) WITH n LIMIT 2 RETURN count(n) AS node_count",
        database_=database,
    )
    return records[0]["node_count"] if records else 0


def _validate_data(schema: dict, node_count: int) -> None:
    rel_types = {r["type"] for r in schema.get("relationships", [])}
    errors = []
    if node_count < 2:
        errors.append(f"Database contains {node_count} node(s) — at least 2 required.")
    if not rel_types:
        errors.append("Database contains no relationship types — at least 1 required.")
    if errors:
        print("\nERROR: AuraDB does not have enough data to create an agent:")
        for e in errors:
            print(f"  • {e}")
        print("\nLoad data into the database before running fetch_schema.py.")
        print("schema.json was NOT written.")
        sys.exit(1)


# ── Cardinality enrichment ────────────────────────────────────────────────────

def _enrich_with_cardinality(driver, database: str, schema: dict) -> None:
    for label, props in schema.get("node_props", {}).items():
        for prop in props:
            if prop.get("aura_data_type") != "string":
                continue
            pname = prop["property"]
            query = (
                f"MATCH (n:`{label}`) WHERE n.`{pname}` IS NOT NULL "
                f"WITH DISTINCT n.`{pname}` AS v LIMIT {CARDINALITY_THRESHOLD + 1} "
                f"RETURN collect(v) AS values"
            )
            _check_cardinality(driver, database, prop, query)

    for rel_type, props in schema.get("rel_props", {}).items():
        for prop in props:
            if prop.get("aura_data_type") != "string":
                continue
            pname = prop["property"]
            query = (
                f"MATCH ()-[r:`{rel_type}`]->() WHERE r.`{pname}` IS NOT NULL "
                f"WITH DISTINCT r.`{pname}` AS v LIMIT {CARDINALITY_THRESHOLD + 1} "
                f"RETURN collect(v) AS values"
            )
            _check_cardinality(driver, database, prop, query)


def _check_cardinality(driver, database: str, prop: dict, query: str) -> None:
    try:
        records, _, _ = driver.execute_query(query, database_=database)
        values = list(records[0]["values"]) if records else []
        if len(values) <= CARDINALITY_THRESHOLD:
            prop["low_cardinality"] = True
            prop["values"] = sorted(str(v) for v in values if v is not None)
        else:
            prop["low_cardinality"] = False
    except Exception:
        prop["low_cardinality"] = False


# ── Full-text index cross-reference ─────────────────────────────────────────

def _mark_fulltext_indexed_props(schema: dict) -> None:
    ft_lookup: dict[str, set] = {}
    for idx in schema.get("metadata", {}).get("fulltext_index", []):
        for entity in idx.get("labelsOrTypes", []):
            for p in idx.get("properties", []):
                ft_lookup.setdefault(entity, set()).add(p)

    for label, props in schema.get("node_props", {}).items():
        for prop in props:
            prop["has_fulltext_index"] = prop["property"] in ft_lookup.get(label, set())

    for rel_type, props in schema.get("rel_props", {}).items():
        for prop in props:
            prop["has_fulltext_index"] = prop["property"] in ft_lookup.get(rel_type, set())


# ── Output ───────────────────────────────────────────────────────────────────

def _print_summary(schema: dict) -> None:
    node_props = schema.get("node_props", {})
    rel_props = schema.get("rel_props", {})
    relationships = schema.get("relationships", [])
    metadata = schema.get("metadata", {})
    node_count = metadata.get("node_count", "?")
    rel_type_count = len({r["type"] for r in relationships})

    print(f"\n── Data Summary ────────────────────────────────────────────────────")
    print(f"  Nodes sampled (≥): {node_count}  |  Relationship types: {rel_type_count}")

    print("\n── Node Labels & Properties ────────────────────────────────────────")
    for label, props in node_props.items():
        prop_strs = [f"{p['property']}({p['type']}→{p['aura_data_type']})" for p in props]
        print(f"  ({label}): {', '.join(prop_strs) if prop_strs else '(no properties)'}")

    if rel_props:
        print("\n── Relationship Properties ─────────────────────────────────────────")
        for rel_type, props in rel_props.items():
            prop_strs = [f"{p['property']}({p['type']}→{p['aura_data_type']})" for p in props]
            print(f"  [{rel_type}]: {', '.join(prop_strs)}")

    if relationships:
        print("\n── Relationship Patterns ───────────────────────────────────────────")
        for r in relationships:
            print(f"  ({r['start']})-[:{r['type']}]->({r['end']})")

    vector_indexes = metadata.get("vector_index", [])
    if vector_indexes:
        print("\n── Vector Indexes (usable in SimilaritySearch) ─────────────────────")
        for idx in vector_indexes:
            options = idx.get("options") or {}
            config = options.get("indexConfig") or {}
            dims = config.get("vector.dimensions", "?")
            provider = options.get("indexProvider", "?")
            print(
                f"  name={idx.get('name','?')}  labels={idx.get('labelsOrTypes',[])}  "
                f"props={idx.get('properties',[])}  state={idx.get('state','?')}  "
                f"dims={dims}  provider={provider}"
            )
    else:
        print("\n── Vector Indexes: none found ──────────────────────────────────────")
        print("  SimilaritySearch requires a vector index — use neo4j-vector-index-skill.")

    ft_indexes = metadata.get("fulltext_index", [])
    if ft_indexes:
        print("\n── Full-Text Indexes ────────────────────────────────────────────────")
        for idx in ft_indexes:
            print(
                f"  name={idx.get('name','?')}  labels={idx.get('labelsOrTypes',[])}  "
                f"props={idx.get('properties',[])}  state={idx.get('state','?')}"
            )
    else:
        print("\n── Full-Text Indexes: none found ───────────────────────────────────")

    low_card_rows = []
    for label, props in node_props.items():
        for p in props:
            if p.get("low_cardinality"):
                ft = " [fulltext]" if p.get("has_fulltext_index") else ""
                vals = ", ".join(f'"{v}"' for v in p.get("values", []))
                low_card_rows.append(f"  ({label}).{p['property']}{ft}: {vals}")
    for rel_type, props in rel_props.items():
        for p in props:
            if p.get("low_cardinality"):
                ft = " [fulltext]" if p.get("has_fulltext_index") else ""
                vals = ", ".join(f'"{v}"' for v in p.get("values", []))
                low_card_rows.append(f"  [{rel_type}].{p['property']}{ft}: {vals}")

    if low_card_rows:
        print(f"\n── Low Cardinality Properties (≤{CARDINALITY_THRESHOLD} values) ────────────────────────")
        print("  ⚠ Include valid values in CypherTemplate parameter descriptions")
        for row in low_card_rows:
            print(row)
    else:
        print(f"\n── Low Cardinality Properties: none found (threshold: ≤{CARDINALITY_THRESHOLD}) ────")

    print()


def _print_gitignore_warning() -> None:
    gitignore = Path(__file__).parent.parent.parent / ".gitignore"
    if gitignore.exists():
        content = gitignore.read_text()
        if "schema.json" not in content:
            print("\nWARNING: schema.json not in .gitignore — add it to avoid committing graph metadata")
    else:
        print("\nNOTE: Add schema.json to .gitignore to avoid committing graph metadata")


if __name__ == "__main__":
    main()
