from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import unittest
from unittest.mock import patch
from pathlib import Path

import scripts.run_cypher_examples as cypher_runner

ROOT = Path(__file__).resolve().parents[1]
SKILL_FILE = ROOT / "neo4j-vector-index-skill" / "SKILL.md"
MANIFEST_FILE = ROOT / "neo4j-vector-index-skill" / "tests" / "cypher-examples.json"


def run_cmd(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args],
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


class VectorSkillStaticTests(unittest.TestCase):
    def test_skill_has_no_test_metadata(self) -> None:
        skill_text = SKILL_FILE.read_text(encoding="utf-8")
        self.assertNotIn("```cypher test", skill_text)
        self.assertNotIn("cypherBlock", skill_text)
        self.assertNotIn("dropCypherVersionPragma", skill_text)

    def test_cypher_examples_are_discoverable_from_manifest(self) -> None:
        result = run_cmd("scripts/extract_cypher_examples.py", "--manifest", str(MANIFEST_FILE))
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        examples = json.loads(result.stdout)
        names = {example["name"] for example in examples}
        self.assertEqual(names, {"detect-neo4j-version", "query-vector-index-procedure"})

        version_example = next(example for example in examples if example["name"] == "detect-neo4j-version")
        self.assertEqual(version_example["heading"], "Pre-flight — Determine Version")
        self.assertIn("CALL dbms.components()", version_example["query"])

        vector_example = next(example for example in examples if example["name"] == "query-vector-index-procedure")
        self.assertEqual(vector_example["heading"], "Post-filter pattern (2025.x or arbitrary predicates)")
        self.assertEqual(vector_example["setup"], "examples/vector-query.setup.cypher")
        setup_path = SKILL_FILE.parent / vector_example["setup"]
        self.assertTrue(setup_path.exists(), f"missing setup file: {setup_path}")
        self.assertEqual(vector_example["parameters"]["source"], "docs")
        self.assertEqual(vector_example["parameters"]["queryEmbedding"], [0.1, 0.2, 0.3])
        self.assertNotIn("CYPHER 25", vector_example["query"])
        self.assertIn("CALL db.index.vector.queryNodes", vector_example["query"])
        self.assertIn("$queryEmbedding", vector_example["query"])
        self.assertIn("LIMIT 10", vector_example["query"])

    def test_skill_stays_within_line_budget(self) -> None:
        line_count = len(SKILL_FILE.read_text(encoding="utf-8").splitlines())
        self.assertLessEqual(line_count, 500)


class VectorSkillCypherExecutionTests(unittest.TestCase):
    def test_runner_rejects_configured_neo4j_without_destructive_opt_in(self) -> None:
        env = {
            key: value
            for key, value in os.environ.items()
            if key not in {"NEO4J_TEST_ALLOW_DESTRUCTIVE", "NEO4J_TEST_USERNAME", "NEO4J_TEST_PASSWORD"}
        }
        env["NEO4J_TEST_URI"] = "bolt://127.0.0.1:1"
        result = run_cmd("scripts/run_cypher_examples.py", "--manifest", str(MANIFEST_FILE), env=env)
        self.assertEqual(result.returncode, 2, result.stderr + result.stdout)
        self.assertIn("NEO4J_TEST_ALLOW_DESTRUCTIVE=1", result.stderr)

    def test_store_format_is_not_checked_without_expect_store_format(self) -> None:
        class FakeDriver:
            def execute_query(self, *args, **kwargs):
                return [], None, None

            def close(self) -> None:
                return None

        class FakeGraphDatabase:
            @staticmethod
            def driver(*args, **kwargs):
                return FakeDriver()

        example = cypher_runner.CypherExample(
            manifest="manifest.json",
            file="SKILL.md",
            block_number=1,
            cypher_block_number=1,
            start_line=1,
            end_line=3,
            heading="Heading",
            name="probe-free-example",
            setup=None,
            minVersion=None,
            parameters={},
            query="RETURN 1 AS ok",
        )
        env = {**os.environ, "NEO4J_TEST_URI": "bolt://example.invalid:7687", "NEO4J_TEST_ALLOW_DESTRUCTIVE": "1"}
        with patch.dict(os.environ, env, clear=True), patch.object(
            cypher_runner, "require_neo4j_driver", return_value=FakeGraphDatabase
        ), patch.object(cypher_runner, "extract_from_manifest", return_value=[example]), patch.object(
            cypher_runner, "wait_for_neo4j", return_value="5.26.0"
        ), patch.object(
            cypher_runner, "reset_database"
        ), patch.object(
            cypher_runner, "run_setup", return_value=None
        ), patch.object(
            cypher_runner, "read_store_format", side_effect=AssertionError("store format should not be read")
        ):
            self.assertEqual(cypher_runner.run_examples([Path("manifest.json")]), 0)


    @unittest.skipUnless(
        os.environ.get("NEO4J_TEST_URI") and os.environ.get("NEO4J_TEST_ALLOW_DESTRUCTIVE") == "1",
        "requires NEO4J_TEST_URI and NEO4J_TEST_ALLOW_DESTRUCTIVE=1",
    )
    def test_manifest_selected_cypher_examples_execute_against_configured_neo4j(self) -> None:
        try:
            import neo4j  # noqa: F401
        except ImportError:
            self.skipTest("neo4j Python package not installed")

        result = run_cmd("scripts/run_cypher_examples.py", "--manifest", str(MANIFEST_FILE))
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)

    @unittest.skipUnless(shutil.which("docker"), "requires docker")
    def test_manifest_selected_cypher_examples_execute_on_neo4j_5_26_community_aligned_store(self) -> None:
        try:
            import neo4j  # noqa: F401
        except ImportError:
            self.skipTest("neo4j Python package not installed")

        env = {
            key: value
            for key, value in os.environ.items()
            if key not in {"NEO4J_TEST_URI", "NEO4J_TEST_USERNAME", "NEO4J_TEST_PASSWORD"}
        }
        env["NEO4J_TEST_IMAGE"] = "docker.io/library/neo4j:5.26-community"
        result = run_cmd(
            "scripts/run_cypher_examples.py",
            "--manifest",
            str(MANIFEST_FILE),
            "--expect-store-format",
            "record-aligned",
            env=env,
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn("Neo4j store format: record-aligned", result.stdout)


if __name__ == "__main__":
    unittest.main()
