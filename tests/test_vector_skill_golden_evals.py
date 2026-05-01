from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_FILE = ROOT / "neo4j-vector-index-skill" / "tests" / "golden-evals.json"
SKILL_FILE = ROOT / "neo4j-vector-index-skill" / "SKILL.md"
CONFIG_FILE = ROOT / ".config" / "skill-evals.env"


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


def config_has_live_eval_settings() -> bool:
    values = {
        "SKILL_EVAL_API_KEY": os.environ.get("SKILL_EVAL_API_KEY", ""),
        "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY", ""),
        "SKILL_EVAL_MODEL": os.environ.get("SKILL_EVAL_MODEL", ""),
        "SKILL_EVAL_JUDGE_MODEL": os.environ.get("SKILL_EVAL_JUDGE_MODEL", ""),
        "OPENAI_MODEL": os.environ.get("OPENAI_MODEL", ""),
    }
    if CONFIG_FILE.exists():
        for raw_line in CONFIG_FILE.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            if key in values and value.strip() and not values[key]:
                values[key] = value.strip().strip('"').strip("'")
    return bool((values["SKILL_EVAL_API_KEY"] or values["OPENAI_API_KEY"]) and (values["SKILL_EVAL_MODEL"] or values["OPENAI_MODEL"]))


class VectorSkillGoldenEvalTests(unittest.TestCase):
    def test_golden_eval_manifest_is_valid(self) -> None:
        data = json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
        self.assertEqual(ROOT / data["skill"], SKILL_FILE)
        test_plan = data.get("testPlan")
        self.assertIsInstance(test_plan, dict)
        self.assertIsInstance(test_plan.get("purpose"), str)
        self.assertGreater(len(test_plan["purpose"]), 40)
        self.assertIsInstance(test_plan.get("principles"), list)
        self.assertGreater(len(test_plan["principles"]), 0)
        self.assertIsInstance(test_plan.get("outOfScope"), list)

        tasks = test_plan.get("tasks")
        self.assertIsInstance(tasks, list)
        self.assertGreaterEqual(len(tasks), 3)
        planned_eval_ids: set[str] = set()
        for task in tasks:
            self.assertIsInstance(task, dict)
            self.assertIsInstance(task.get("id"), str)
            self.assertIsInstance(task.get("evalId"), str)
            self.assertIsInstance(task.get("description"), str)
            self.assertGreater(len(task["description"]), 20)
            self.assertNotIn(task["evalId"], planned_eval_ids)
            planned_eval_ids.add(task["evalId"])

        evals = data.get("evals")
        self.assertIsInstance(evals, list)
        self.assertGreaterEqual(len(evals), 3)

        seen_ids: set[str] = set()
        for eval_case in evals:
            self.assertNotIn(eval_case["id"], seen_ids)
            seen_ids.add(eval_case["id"])
            self.assertIsInstance(eval_case.get("task"), str)
            self.assertGreater(len(eval_case["task"]), 10)
            covers = eval_case.get("covers")
            self.assertIsInstance(covers, list)
            self.assertGreater(len(covers), 0)
            for covered_behavior in covers:
                self.assertIsInstance(covered_behavior, str)
                self.assertGreater(len(covered_behavior), 5)
            self.assertGreater(len(eval_case["prompt"]), 40)
            checks = eval_case.get("checks")
            self.assertIsInstance(checks, list)
            self.assertGreater(len(checks), 0)
            for check in checks:
                self.assertIsInstance(check, dict)
                self.assertIn(check["type"], {"literal", "regex", "llm_judge"})
                if check["type"] == "literal":
                    self.assertIsInstance(check.get("value"), str)
                    self.assertIn(check.get("expect", "present"), {"present", "absent"})
                elif check["type"] == "regex":
                    self.assertIsInstance(check.get("pattern"), str)
                    re.compile(check["pattern"])
                    self.assertIn(check.get("expect", "present"), {"present", "absent"})
                elif check["type"] == "llm_judge":
                    criteria = check.get("criteria")
                    self.assertIsInstance(criteria, list)
                    self.assertGreater(len(criteria), 0)
                    for criterion in criteria:
                        self.assertIsInstance(criterion.get("id"), str)
                        self.assertIsInstance(criterion.get("description"), str)
        self.assertEqual(planned_eval_ids, seen_ids)

    def test_runner_skips_cleanly_without_api_config(self) -> None:
        env = {
            key: value
            for key, value in os.environ.items()
            if key
            not in {"SKILL_EVAL_API_KEY", "OPENAI_API_KEY", "SKILL_EVAL_MODEL", "SKILL_EVAL_JUDGE_MODEL", "OPENAI_MODEL"}
        }
        result = run_cmd(
            "scripts/run_golden_evals.py",
            "--manifest",
            str(MANIFEST_FILE),
            "--config",
            "/tmp/nonexistent-skill-evals.env",
            env=env,
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn("SKIP:", result.stdout)

    def test_runner_writes_jsonl_summary_and_outputs(self) -> None:
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:  # noqa: N802
                length = int(self.headers.get("Content-Length", "0"))
                request_body = json.loads(self.rfile.read(length).decode("utf-8"))
                if "response_format" in request_body:
                    content = json.dumps(
                        {
                            "criteria": [
                                {
                                    "id": "mentions_hello",
                                    "passed": True,
                                    "evidence": "response says hello",
                                }
                            ],
                            "overall_passed": True,
                        }
                    )
                else:
                    content = "```cypher\nRETURN 'hello' AS greeting\n```\nhello from mock eval"
                body = {
                    "choices": [{"message": {"content": content}}],
                    "usage": {"prompt_tokens": 10, "completion_tokens": 4, "total_tokens": 14},
                }
                encoded = json.dumps(body).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)

            def log_message(self, format: str, *args: object) -> None:
                return

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                tmp = Path(tmpdir)
                skill_file = tmp / "SKILL.md"
                manifest_file = tmp / "golden-evals.json"
                summary_file = tmp / "summary.json"
                jsonl_file = tmp / "results.jsonl"
                output_dir = tmp / "outputs"
                skill_file.write_text("Use hello in every answer.\n", encoding="utf-8")
                manifest_file.write_text(
                    json.dumps(
                        {
                            "skill": str(skill_file),
                            "evals": [
                                {
                                    "id": "mock-eval",
                                    "prompt": "Return the required greeting from the skill.",
                                    "checks": [
                                        {"type": "literal", "scope": "code", "value": "RETURN 'hello'"},
                                        {"type": "literal", "expect": "absent", "value": "goodbye"},
                                        {
                                            "type": "llm_judge",
                                            "blocking": False,
                                            "criteria": [
                                                {
                                                    "id": "mentions_hello",
                                                    "description": "The answer says hello.",
                                                }
                                            ],
                                        },
                                    ],
                                }
                            ],
                        }
                    ),
                    encoding="utf-8",
                )

                result = run_cmd(
                    "scripts/run_golden_evals.py",
                    "--manifest",
                    str(manifest_file),
                    "--config",
                    "/tmp/nonexistent-skill-evals.env",
                    "--api-base",
                    f"http://127.0.0.1:{server.server_port}/v1",
                    "--api-key",
                    "test-key",
                    "--model",
                    "test-model",
                    "--judge-model",
                    "test-judge-model",
                    "--repeat",
                    "2",
                    "--json-output",
                    str(summary_file),
                    "--jsonl-output",
                    str(jsonl_file),
                    "--output-dir",
                    str(output_dir),
                )
                self.assertEqual(result.returncode, 0, result.stderr + result.stdout)

                lines = jsonl_file.read_text(encoding="utf-8").splitlines()
                self.assertEqual(len(lines), 2)
                records = [json.loads(line) for line in lines]
                self.assertTrue(all(record["passed"] for record in records))
                self.assertEqual([record["trial"] for record in records], [1, 2])
                self.assertEqual(records[0]["model"], "test-model")
                self.assertEqual(records[0]["judge_model"], "test-judge-model")
                self.assertEqual(records[0]["usage"]["total_tokens"], 14)
                self.assertEqual(records[0]["judge_usage"][0]["total_tokens"], 14)
                self.assertEqual(records[0]["advisory_errors"], [])
                self.assertTrue(Path(records[0]["output_path"]).exists())

                summary = json.loads(summary_file.read_text(encoding="utf-8"))
                self.assertEqual(summary["attempt_count"], 2)
                self.assertEqual(summary["failed_attempts"], 0)
                self.assertEqual(summary["advisory_failed_attempts"], 0)
                self.assertEqual(summary["judge_model"], "test-judge-model")
                self.assertEqual(summary["pass_at_1"]["passed"], 1)
                self.assertEqual(summary["pass_at_n"]["passed"], 1)
                self.assertEqual(summary["pass_all_trials"]["passed"], 1)
                self.assertIn("pass@2 1/1", result.stdout)
        finally:
            server.shutdown()
            server.server_close()

    def test_fail_on_advisory_returns_non_zero_for_failed_judge(self) -> None:
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:  # noqa: N802
                length = int(self.headers.get("Content-Length", "0"))
                request_body = json.loads(self.rfile.read(length).decode("utf-8"))
                if "response_format" in request_body:
                    content = json.dumps(
                        {
                            "criteria": [
                                {
                                    "id": "mentions_hello",
                                    "passed": False,
                                    "evidence": "response does not explain hello",
                                }
                            ],
                            "overall_passed": False,
                        }
                    )
                else:
                    content = "```cypher\nRETURN 'hello' AS greeting\n```"
                body = {
                    "choices": [{"message": {"content": content}}],
                    "usage": {"prompt_tokens": 10, "completion_tokens": 4, "total_tokens": 14},
                }
                encoded = json.dumps(body).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)

            def log_message(self, format: str, *args: object) -> None:
                return

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                tmp = Path(tmpdir)
                skill_file = tmp / "SKILL.md"
                manifest_file = tmp / "golden-evals.json"
                skill_file.write_text("Use hello in every answer.\n", encoding="utf-8")
                manifest_file.write_text(
                    json.dumps(
                        {
                            "skill": str(skill_file),
                            "evals": [
                                {
                                    "id": "mock-advisory-failure",
                                    "prompt": "Return the required greeting from the skill.",
                                    "checks": [
                                        {"type": "literal", "scope": "code", "value": "RETURN 'hello'"},
                                        {
                                            "type": "llm_judge",
                                            "blocking": False,
                                            "criteria": [
                                                {
                                                    "id": "mentions_hello",
                                                    "description": "The answer explains hello.",
                                                }
                                            ],
                                        },
                                    ],
                                }
                            ],
                        }
                    ),
                    encoding="utf-8",
                )

                result = run_cmd(
                    "scripts/run_golden_evals.py",
                    "--manifest",
                    str(manifest_file),
                    "--config",
                    "/tmp/nonexistent-skill-evals.env",
                    "--api-base",
                    f"http://127.0.0.1:{server.server_port}/v1",
                    "--api-key",
                    "test-key",
                    "--model",
                    "test-model",
                    "--judge-model",
                    "test-judge-model",
                    "--fail-on-advisory",
                )
                self.assertEqual(result.returncode, 1, result.stderr + result.stdout)
                self.assertIn("advisory:", result.stderr)
                self.assertIn("mentions_hello", result.stderr)
        finally:
            server.shutdown()
            server.server_close()

    @unittest.skipUnless(config_has_live_eval_settings(), "requires local golden-eval API config")
    def test_golden_evals_pass_when_api_is_available(self) -> None:
        result = run_cmd(
            "scripts/run_golden_evals.py",
            "--manifest",
            str(MANIFEST_FILE),
            "--require-api",
            "--fail-on-advisory",
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)


if __name__ == "__main__":
    unittest.main()
