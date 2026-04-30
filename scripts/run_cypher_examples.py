#!/usr/bin/env python3
"""Run manifest-selected Cypher examples against Neo4j."""
from __future__ import annotations

import argparse
import os
import re
import socket
import subprocess
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from extract_cypher_examples import CypherExample, extract_from_manifest  # noqa: E402

DEFAULT_MANIFEST = Path("neo4j-vector-index-skill/tests/cypher-examples.json")
DEFAULT_IMAGE = "docker.io/library/neo4j:5.26-community"
DEFAULT_USER = "neo4j"
DEFAULT_PASSWORD = "testpassword123"
DESTRUCTIVE_OPT_IN_ENV = "NEO4J_TEST_ALLOW_DESTRUCTIVE"


def require_neo4j_driver():
    try:
        from neo4j import GraphDatabase  # type: ignore
    except ImportError:
        print("ERROR: neo4j package not installed. Run: python3 -m pip install -r requirements-dev.txt", file=sys.stderr)
        raise SystemExit(2)
    return GraphDatabase


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, check=check, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def docker_available() -> bool:
    try:
        run(["docker", "--version"])
        return True
    except Exception:
        return False


def env_flag_enabled(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes"}


def start_neo4j_container() -> tuple[str, str, str, str]:
    if not docker_available():
        print("ERROR: docker command not available and NEO4J_TEST_URI is not set", file=sys.stderr)
        raise SystemExit(2)

    image = os.environ.get("NEO4J_TEST_IMAGE", DEFAULT_IMAGE)
    password = os.environ.get("NEO4J_TEST_PASSWORD", DEFAULT_PASSWORD)
    user = os.environ.get("NEO4J_TEST_USERNAME", DEFAULT_USER)
    port = free_port()
    name = f"neo4j-skills-test-{os.getpid()}"
    cmd = [
        "docker",
        "run",
        "--rm",
        "-d",
        "--name",
        name,
        "-p",
        f"127.0.0.1:{port}:7687",
        "-e",
        f"NEO4J_AUTH={user}/{password}",
        image,
    ]
    try:
        run(cmd)
    except subprocess.CalledProcessError as exc:
        print(exc.stderr, file=sys.stderr)
        raise SystemExit(2)
    return name, f"bolt://127.0.0.1:{port}", user, password


def stop_container(name: str | None) -> None:
    if name:
        subprocess.run(["docker", "stop", name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def version_tuple(version: str) -> tuple[int, ...]:
    parts = []
    for piece in version.replace("-", ".").split("."):
        if piece.isdigit():
            parts.append(int(piece))
        else:
            digits = "".join(ch for ch in piece if ch.isdigit())
            if digits:
                parts.append(int(digits))
            break
    return tuple(parts or [0])


def meets_min_version(server_version: str, minimum: str | None) -> bool:
    if not minimum:
        return True
    return version_tuple(server_version) >= version_tuple(minimum)


def split_cypher_statements(text: str) -> list[str]:
    statements = []
    current = []
    in_single = False
    in_double = False
    escape = False
    for ch in text:
        if escape:
            current.append(ch)
            escape = False
            continue
        if ch == "\\" and (in_single or in_double):
            current.append(ch)
            escape = True
            continue
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        if ch == ";" and not in_single and not in_double:
            statement = "".join(current).strip()
            if statement:
                statements.append(statement)
            current = []
        else:
            current.append(ch)
    tail = "".join(current).strip()
    if tail:
        statements.append(tail)
    return statements


def escape_identifier(name: str) -> str:
    return "`" + name.replace("`", "``") + "`"


def wait_for_neo4j(driver, timeout: int = 90) -> str:
    deadline = time.time() + timeout
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            with driver.session() as session:
                record = session.run("CALL dbms.components() YIELD versions RETURN versions[0] AS version").single()
            return str(record["version"])
        except Exception as exc:  # pragma: no cover - depends on startup timing
            last_error = exc
            time.sleep(2)
    raise RuntimeError(f"Neo4j did not become available within {timeout}s: {last_error}")


def read_store_format(driver, database: str = "neo4j") -> str | None:
    with driver.session(database="system") as session:
        record = session.run(
            "SHOW DATABASES YIELD name, store WHERE name = $database RETURN store",
            database=database,
        ).single()
    return str(record["store"]) if record and record.get("store") is not None else None


def reset_database(driver) -> None:
    # Best-effort cleanup for the simple first pass. Constraint-backed indexes are
    # removed by dropping constraints first.
    try:
        constraints, _, _ = driver.execute_query("SHOW CONSTRAINTS YIELD name RETURN name")
        for record in constraints:
            driver.execute_query(f"DROP CONSTRAINT {escape_identifier(record['name'])} IF EXISTS")
    except Exception:
        pass
    try:
        indexes, _, _ = driver.execute_query("SHOW INDEXES YIELD name RETURN name")
        for record in indexes:
            driver.execute_query(f"DROP INDEX {escape_identifier(record['name'])} IF EXISTS")
    except Exception:
        pass
    driver.execute_query("MATCH (n) DETACH DELETE n")


def run_setup(driver, example: CypherExample) -> Path | None:
    if not example.setup:
        return None
    setup_path = Path(example.file).parent / example.setup
    if not setup_path.exists():
        raise FileNotFoundError(f"setup file does not exist: {setup_path}")
    for statement in split_cypher_statements(setup_path.read_text(encoding="utf-8")):
        driver.execute_query(statement)
    return setup_path


def run_examples(manifests: list[Path], *, expect_store_format: str | None = None) -> int:
    examples: list[CypherExample] = []
    for manifest in manifests:
        examples.extend(extract_from_manifest(manifest))
    if not examples:
        print("ERROR: no Cypher examples found", file=sys.stderr)
        return 1

    container_name: str | None = None
    uri = os.environ.get("NEO4J_TEST_URI")
    user = os.environ.get("NEO4J_TEST_USERNAME", DEFAULT_USER)
    password = os.environ.get("NEO4J_TEST_PASSWORD", DEFAULT_PASSWORD)
    if uri and not env_flag_enabled(DESTRUCTIVE_OPT_IN_ENV):
        print(
            "ERROR: refusing to run destructive Cypher example tests against NEO4J_TEST_URI "
            f"without {DESTRUCTIVE_OPT_IN_ENV}=1. Use a disposable database.",
            file=sys.stderr,
        )
        return 2
    if not uri:
        container_name, uri, user, password = start_neo4j_container()

    GraphDatabase = require_neo4j_driver()
    failures = 0
    skipped = 0
    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        try:
            server_version = wait_for_neo4j(driver)
            print(f"Neo4j version: {server_version}")
            if expect_store_format:
                try:
                    store_format = read_store_format(driver)
                except Exception as exc:
                    print(f"ERROR: could not read Neo4j store format: {exc}", file=sys.stderr)
                    return 1
                if store_format:
                    print(f"Neo4j store format: {store_format}")
                if not (store_format and re.search(expect_store_format, store_format)):
                    print(
                        f"ERROR: expected store format to match {expect_store_format!r}, got {store_format!r}",
                        file=sys.stderr,
                    )
                    return 1
            for example in examples:
                if not meets_min_version(server_version, example.minVersion):
                    skipped += 1
                    print(f"SKIP {example.name}: requires Neo4j >= {example.minVersion}")
                    continue
                try:
                    reset_database(driver)
                    setup_path = run_setup(driver, example)
                    driver.execute_query(example.query, parameters_=example.parameters)
                    setup_display = setup_path if setup_path else "none"
                    print(f"PASS {example.name} ({example.file}:{example.start_line}, setup={setup_display})")
                except Exception as exc:
                    failures += 1
                    print("FAIL", example.name, file=sys.stderr)
                    print(f"  file: {example.file}", file=sys.stderr)
                    print(f"  manifest: {example.manifest}", file=sys.stderr)
                    print(f"  block: {example.block_number}", file=sys.stderr)
                    print(f"  setup: {example.setup or 'none'}", file=sys.stderr)
                    print(f"  neo4j: {server_version}", file=sys.stderr)
                    print(f"  error: {exc}", file=sys.stderr)
                    print("  query:", file=sys.stderr)
                    print(example.query, file=sys.stderr)
            reset_database(driver)
        finally:
            driver.close()
    finally:
        stop_container(container_name)

    passed = len(examples) - skipped - failures
    print(f"Summary: {passed} passed, {skipped} skipped, {failures} failed")
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run manifest-selected Cypher examples against Neo4j")
    parser.add_argument("--manifest", action="append", default=[], help="Cypher example manifest to run")
    parser.add_argument(
        "--expect-store-format",
        help="Regex that the current neo4j database store format must match before examples run.",
    )
    args = parser.parse_args()
    manifests = [Path(p) for p in (args.manifest or [str(DEFAULT_MANIFEST)])]
    return run_examples(manifests, expect_store_format=args.expect_store_format)


if __name__ == "__main__":
    raise SystemExit(main())
