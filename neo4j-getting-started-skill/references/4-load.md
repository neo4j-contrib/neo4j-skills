# Stage 4 — load
# Import data into the database. Always apply schema constraints first.

## Step L0 — Apply schema constraints (always, before any data)

```bash
source .env
cypher-shell -a "$NEO4J_URI" -u "$NEO4J_USERNAME" -p "$NEO4J_PASSWORD" --file schema/schema.cypher
```

Or via Python if cypher-shell unavailable:
```python
from neo4j import GraphDatabase; import os
driver = GraphDatabase.driver(os.environ["NEO4J_URI"],
                               auth=(os.environ["NEO4J_USERNAME"], os.environ["NEO4J_PASSWORD"]))
with driver.session() as s:
    for stmt in open("schema/schema.cypher").read().split(";"):
        stmt = stmt.strip()
        if stmt and not stmt.startswith("//"):
            s.run(stmt)
driver.close()
print("Schema applied")
```

## Import rules (apply to all paths)

- **MERGE nodes first** — complete all node MERGE statements before any relationship MERGE
- **MERGE relationships second** — only after all endpoint node types are loaded
- **Batch size**: 500 rows per call — pass as `$rows` parameter list from Python
- **Use MERGE not CREATE** — idempotent, safe to re-run
- **All scripts go in `data/`** — user can re-run them for updates

## Preferred pattern — Python batch loading via DataFrame

Load into pandas DataFrame, push to Neo4j in batches via `driver.execute_query(..., rows=batch)`. Works with any source (local files, HTTPS, S3/GCS, Parquet, relational DBs, MongoDB) — no Neo4j import directory access required (works on Aura).

```python
import os
import pandas as pd
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()
driver = GraphDatabase.driver(
    os.environ["NEO4J_URI"],
    auth=(os.environ["NEO4J_USERNAME"], os.environ["NEO4J_PASSWORD"])
)

BATCH = 500

def load_batches(query: str, rows: list[dict]) -> int:
    total = 0
    for i in range(0, len(rows), BATCH):
        records, summary, _ = driver.execute_query(query, rows=rows[i:i+BATCH])
        total += summary.counters.nodes_created + summary.counters.relationships_created
    return total

# ── Step 0: apply constraints before any data (idempotent) ────────────────────
schema = open("schema/schema.cypher").read()
with driver.session() as s:
    for stmt in schema.split(";"):
        stmt = stmt.strip()
        if stmt and not stmt.startswith("//"):
            s.run(stmt)
print("✓ Constraints applied")

# ── Read data — swap in any pandas-compatible source ──────────────────────────
# CSV (local or HTTPS):   pd.read_csv("https://data.neo4j.com/northwind/products.csv")
# Parquet / S3:           pd.read_parquet("s3://bucket/file.parquet")
# Relational (SQLAlchemy):pd.read_sql("SELECT * FROM products", engine)
# MongoDB:                pd.DataFrame(collection.find())

products   = pd.read_csv("https://data.neo4j.com/northwind/products.csv")
categories = pd.read_csv("https://data.neo4j.com/northwind/categories.csv")

# ── Phase 1: all node types (MERGE nodes before relationships) ─────────────────
n = load_batches("""
    UNWIND $rows AS row
    MERGE (p:Product {productID: row.productID})
    SET p.productName  = row.productName,
        p.unitPrice    = toFloat(row.unitPrice),
        p.unitsInStock = toInteger(row.unitsInStock)
""", products.to_dict("records"))
print(f"Products: {n}")

n = load_batches("""
    UNWIND $rows AS row
    MERGE (c:Category {categoryID: row.categoryID})
    SET c.categoryName = row.categoryName,
        c.description  = row.description
""", categories.to_dict("records"))
print(f"Categories: {n}")

# ── Phase 2: relationships (after all nodes exist) ─────────────────────────────
n = load_batches("""
    UNWIND $rows AS row
    MATCH (p:Product  {productID:  row.productID})
    MATCH (c:Category {categoryID: row.categoryID})
    MERGE (p)-[:PART_OF]->(c)
""", products.to_dict("records"))
print(f"PART_OF rels: {n}")

driver.close()
```

Run: `.venv/bin/python3 data/import.py`

### Type coercion in Cypher vs Python

Prefer coercing types in Python before passing rows (faster, avoids Cypher `toFloat()`):
```python
products["unitPrice"]    = pd.to_numeric(products["unitPrice"],    errors="coerce")
products["unitsInStock"] = pd.to_numeric(products["unitsInStock"], errors="coerce").astype("Int64")
```
Then use `row.unitPrice` directly in Cypher without wrapping functions.

---

## Path A — Demo dataset

```bash
source .env
# Movies
curl -s https://raw.githubusercontent.com/neo4j-graph-examples/movies/main/data/movies.cypher \
  | cypher-shell -a "$NEO4J_URI" -u "$NEO4J_USERNAME" -p "$NEO4J_PASSWORD"
```

For other demos, fetch the import URL from https://github.com/neo4j-graph-examples.

## Path B — Synthetic data

**Two-step approach: generate CSVs first, then import via DataFrame.**
This is faster to write, easier to inspect, and reuses the same batch loading pattern as Path C.

### Step B1 — Generate CSVs (`data/generate.py`)

Generate one CSV per entity type using Python's `csv` module — no DB connection needed:

```python
import csv, os, random
from datetime import datetime, timedelta

os.makedirs("data", exist_ok=True)
random.seed(42)

CITIES = ["London", "New York", "Berlin", "Tokyo", "Sydney"]

# ── Nodes ─────────────────────────────────────────────────────────────────────
with open("data/persons.csv", "w", newline="") as f:
    w = csv.DictWriter(f, ["id", "name", "age", "city", "joined_at"])
    w.writeheader()
    for i in range(1, 201):
        w.writerow({
            "id": f"p{i}",
            "name": f"Person {i}",
            "age": random.randint(18, 65),
            "city": random.choice(CITIES),
            "joined_at": (datetime.now() - timedelta(days=random.randint(0, 730))).strftime("%Y-%m-%d"),
        })

# (add more node CSVs for other labels in schema.json)

# ── Relationships ─────────────────────────────────────────────────────────────
ids = [f"p{i}" for i in range(1, 201)]
with open("data/follows.csv", "w", newline="") as f:
    w = csv.DictWriter(f, ["from_id", "to_id"])
    w.writeheader()
    for src in ids:
        for tgt in random.sample(ids, k=random.randint(3, 15)):
            if src != tgt:
                w.writerow({"from_id": src, "to_id": tgt})

print("✓ CSVs written:", [f for f in os.listdir("data") if f.endswith(".csv")])
```

Run: `.venv/bin/python3 data/generate.py`

### Step B2 — Import CSVs (`data/import.py`)

Use the standard batch loading pattern — same as Path C:

```python
import os, pandas as pd
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()
driver = GraphDatabase.driver(
    os.environ["NEO4J_URI"],
    auth=(os.environ["NEO4J_USERNAME"], os.environ["NEO4J_PASSWORD"])
)

BATCH = 500

def load_batches(query, rows):
    total = 0
    for i in range(0, len(rows), BATCH):
        _, summary, _ = driver.execute_query(query, rows=rows[i:i+BATCH])
        total += summary.counters.nodes_created + summary.counters.relationships_created
    return total

# ── Phase 1: nodes ─────────────────────────────────────────────────────────────
persons = pd.read_csv("data/persons.csv")
n = load_batches("""
    UNWIND $rows AS row
    MERGE (p:Person {id: row.id})
    SET p.name = row.name, p.age = toInteger(row.age),
        p.city = row.city, p.joinedAt = date(row.joined_at)
""", persons.to_dict("records"))
print(f"  Person nodes: {n}")

# ── Phase 2: relationships ──────────────────────────────────────────────────────
follows = pd.read_csv("data/follows.csv")
n = load_batches("""
    UNWIND $rows AS row
    MATCH (a:Person {id: row.from_id})
    MATCH (b:Person {id: row.to_id})
    MERGE (a)-[:FOLLOWS]->(b)
""", follows.to_dict("records"))
print(f"  FOLLOWS rels: {n}")

records, _, _ = driver.execute_query("MATCH (n) RETURN labels(n)[0] AS l, count(n) AS c")
for r in records:
    print(f"  {r['l']}: {r['c']}")
driver.close()
```

Run: `.venv/bin/python3 data/import.py`

## Path C — CSV / tabular data (any source)

Use the **Python batch loading pattern** above. Install dependencies first:
```bash
.venv/bin/pip install neo4j-rust-ext pandas python-dotenv
```

Adapt the DataFrame source to match:

| Source | pandas call |
|--------|-------------|
| Local CSV | `pd.read_csv("./data/file.csv")` |
| HTTPS CSV | `pd.read_csv("https://…/file.csv")` |
| Parquet / S3 | `pd.read_parquet("s3://bucket/file.parquet")` |
| PostgreSQL | `pd.read_sql("SELECT * FROM table", engine)` |
| MongoDB | `pd.DataFrame(collection.find({}, {"_id": 0}))` |
| Excel | `pd.read_excel("file.xlsx")` |

Always follow **Phase 1 (all nodes) → Phase 2 (all relationships)** regardless of source.

## Path D — Document / GraphRAG pipeline (DATA_SOURCE=documents)

**STOP — do NOT generate synthetic data for this path.**
Ingest what is already in `data/`. Fall back to synthetic only if the user explicitly confirms they have no files.

### Step D0 — Inventory data/

```bash
find data/ -type f | sort
wc -l data/*   # rough size check
```

- **Files present** → proceed with ingestion of those files
- **data/ empty or missing** → stop and ask the user where their documents are;
  offer to generate synthetic only if they confirm they have no real files
- **Large files (>500 KB)** → note they will take longer to embed; proceed anyway
- **PDFs** → set `from_pdf=True` in SimpleKGPipeline and install `pypdf`
- **Encoding issues** → read with `errors="replace"` and log any decoding problems

### Step D1 — Install dependencies

```bash
.venv/bin/pip install neo4j-rust-ext "neo4j-graphrag[openai]>=1.13.0" python-dotenv --quiet
# If PDFs are present:
# .venv/bin/pip install pypdf --quiet
```

### Step D2 — Verify .env has LLM and embedding keys

```bash
grep -E "OPENAI_API_KEY|EMBEDDING_MODEL|LLM_MODEL" .env || echo "⚠ Missing LLM keys in .env"
```

If `OPENAI_API_KEY` is missing: check `aura.env` and append to `.env`.

### Step D3 — Write and run import/ingest_docs.py

Follow `${CLAUDE_SKILL_DIR}/references/capabilities/kg-from-documents.md` for the full pipeline template. Key points:

```python
from neo4j_graphrag.experimental.pipeline.kg_builder import SimpleKGPipeline
from neo4j_graphrag.indexes import create_vector_index

pipeline = SimpleKGPipeline(
    llm=llm,
    driver=driver,
    embedder=embedder,
    from_pdf=False,           # set True if .pdf files present
    neo4j_database=os.environ.get("NEO4J_DATABASE", "neo4j"),
    schema={
        "node_types":         NODE_TYPES,       # adapt to domain
        "relationship_types": RELATIONSHIP_TYPES,
        "patterns":           PATTERNS,
    },
    perform_entity_resolution=True,
)

# Load ALL files found in data/ — .txt, .md, .pdf
for path in sorted(Path("data/").glob("**/*")):
    if path.is_file() and path.suffix in (".txt", ".md", ".pdf"):
        try:
            text = path.read_text(encoding="utf-8", errors="replace") if path.suffix != ".pdf" else None
            if path.suffix == ".pdf":
                await pipeline.run_async(file_path=str(path))
            else:
                await pipeline.run_async(text=text)
            print(f"  ✓ {path.name}")
        except Exception as e:
            print(f"  ✗ {path.name}: {e}")   # log and continue — don't abort

# IMPORTANT: SimpleKGPipeline does NOT create the vector index automatically.
# Always create it explicitly after ingestion using the graphrag library helper.
create_vector_index(
    driver,
    name="chunk_embeddings",
    label="Chunk",
    embedding_property="embedding",
    dimensions=int(os.environ.get("EMBEDDING_DIMENSIONS", "1536")),
    similarity_fn="cosine",
    neo4j_database=os.environ.get("NEO4J_DATABASE", "neo4j"),
)
print("  ✓ Vector index 'chunk_embeddings' ready")
```

### Messy data — common patterns

| Problem | Symptom | Fix |
|---------|---------|-----|
| Mixed encoding | `UnicodeDecodeError` | `open(path, errors="replace")` |
| Very large files | Slow ingestion | OK — pipeline chunks internally; just wait |
| Scanned PDFs (no text layer) | Empty chunks | Run OCR first (e.g. `pytesseract`) |
| Files with boilerplate headers | Low-value entity extraction | Strip headers before passing `text=` |
| No useful structure | LLM extracts nothing | Try `schema=None` — lets LLM infer types freely |

**Run ingestion synchronously — do NOT use `&` or background execution.**
Script must complete and print "✓ Ingestion complete" before the next stage begins.
LLM-based extraction is slow (minutes for large corpora) — expected, just wait.

**Always inspect the actual graph schema after ingestion before writing queries:**
```cypher
CYPHER 25
CALL db.schema.visualization()
```
```cypher
CYPHER 25
MATCH (n) RETURN labels(n)[0] AS label, count(n) AS cnt ORDER BY cnt DESC
```
```cypher
CYPHER 25
MATCH ()-[r]->() RETURN type(r) AS rel, count(r) AS cnt ORDER BY cnt DESC
```

**SimpleKGPipeline entity label note:**
Extracted entities are stored under `__KGBuilder__` label (not `Entity`, `Party`, etc.).
The relationship from entity to its source chunk is `FROM_CHUNK` (not `MENTIONS`).
The relationship from chunk to document is `FROM_DOCUMENT` (not `HAS_CHUNK`).

Use these actual labels when writing the retrieval_query for VectorCypherRetriever:
```python
retrieval_query = """
OPTIONAL MATCH (entity:__KGBuilder__)-[:FROM_CHUNK]->(node)
RETURN node.text                            AS chunk_text,
       collect(DISTINCT entity.name)[..5]   AS entities,
       score
ORDER BY score DESC
"""
```

## Step L5 — Post-import search indexes

```cypher
CYPHER 25
CREATE FULLTEXT INDEX <label>_name IF NOT EXISTS
  FOR (n:<Label>) ON EACH [n.name];
```

## Step L6 — Write schema/reset.cypher (always)

```bash
cat > schema/reset.cypher << 'EOF'
// Delete all data — keeps schema (constraints + indexes)
CYPHER 25
MATCH (n) CALL (n) { DETACH DELETE n } IN TRANSACTIONS OF 1000 ROWS;
EOF
echo "Reset script: cypher-shell ... --file schema/reset.cypher"
```

## Step L7 — HITL data preview pause

Show row counts and a sample before proceeding:
```bash
source .env
cypher-shell -a "$NEO4J_URI" -u "$NEO4J_USERNAME" -p "$NEO4J_PASSWORD" \
  "CYPHER 25 MATCH (n) RETURN labels(n)[0] AS label, count(n) AS count ORDER BY count DESC"
```

In autonomous mode: log counts and continue.

## Completion condition

- `MATCH (n) RETURN count(n)` ≥ 50
- Each node label has ≥1 node
- `data/` directory contains the import script(s) used
- `schema/reset.cypher` exists

## On Completion — write to progress.md

Record node counts per label and total relationships. For `sample_id`, read the first two rows of the primary node CSV:

```python
import csv
with open("data/persons.csv") as f:       # replace with your primary node CSV
    row = next(csv.DictReader(f))
    print(row["id"])                       # use the primaryKey field from schema.json
```

Or query the DB: `MATCH (n:Person) RETURN n.id LIMIT 1`

```markdown
### 4-load
status: done
nodes=<e.g. "200 Person, 50 Post">
relationships=<e.g. "1400 FOLLOWS, 300 POSTED">
files=data/generate.py,data/import.py,schema/reset.cypher
sample_id=<actual value from first data row, e.g. "p1" or "42" or "abc-uuid">
```

## Error recovery

- Import partially failed → run `reset.cypher`, re-apply `schema.cypher`, retry from scratch
- MERGE slow → check constraint was created before import (Step L0)
- DataFrame empty → verify source URL/path and column names match schema.json
