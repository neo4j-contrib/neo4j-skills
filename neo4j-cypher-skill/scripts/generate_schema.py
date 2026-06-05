import os
import json
import sys
from neo4j import GraphDatabase

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv optional; falls back to env vars already set

URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

def fetch_and_map_schema(db_name=None):
    print(f"Connecting to Neo4j instance at {URI}...")
    schema_query = "CALL apoc.meta.schema()"

    try:
        with GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD)) as driver:
            name = db_name or os.getenv("NEO4J_DATABASE", "neo4j")
            records, _, _ = driver.execute_query(schema_query, database_=name)

            if not records:
                print("No schema records returned from the database.")
                return

            raw_schema = records[0].data()
            output_path = f"{name}-schema.json"

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(raw_schema, f, indent=2)

            print(f"Success! Schema saved to {output_path}")

    except Exception as e:
        print(f"Failed to generate schema: {e}")

if __name__ == "__main__":
    db_name = sys.argv[1] if len(sys.argv) > 1 else None
    fetch_and_map_schema(db_name)
