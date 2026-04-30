#!/usr/bin/env python3
"""Run optional golden agent-skill evals through an OpenAI-compatible chat API."""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

DEFAULT_MANIFEST = Path("neo4j-vector-index-skill/tests/golden-evals.json")
DEFAULT_API_BASE = "https://api.openai.com/v1"
DEFAULT_CONFIG = Path(".config/skill-evals.env")
FENCE_RE = re.compile(r"```[^\n`]*\n(.*?)```", flags=re.DOTALL)
JUDGE_RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "skill_eval_judge",
        "strict": True,
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "criteria": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "id": {"type": "string"},
                            "passed": {"type": "boolean"},
                            "evidence": {"type": "string"},
                        },
                        "required": ["id", "passed", "evidence"],
                    },
                },
                "overall_passed": {"type": "boolean"},
            },
            "required": ["criteria", "overall_passed"],
        },
    },
}


@dataclass
class GoldenEval:
    id: str
    prompt: str
    checks: list[dict[str, Any]]


@dataclass
class CheckEvaluation:
    check_results: list[dict[str, Any]]
    blocking_errors: list[str]
    advisory_errors: list[str]
    judge_usage: list[dict[str, Any]]


@dataclass
class EvalAttemptResult:
    eval_id: str
    trial: int
    model: str
    judge_model: str
    passed: bool
    latency_ms: int
    check_results: list[dict[str, Any]]
    blocking_errors: list[str]
    advisory_errors: list[str]
    output_path: str | None
    output_chars: int
    usage: dict[str, Any] | None
    judge_usage: list[dict[str, Any]]
    error: str | None


def legacy_checks(raw: dict[str, Any]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    for pattern in raw.get("requiredPatterns", []):
        checks.append({"type": "regex", "pattern": pattern, "expect": "present"})
    for pattern in raw.get("forbiddenPatterns", []):
        checks.append({"type": "regex", "pattern": pattern, "expect": "absent"})
    return checks


def load_manifest(path: Path) -> tuple[Path, list[GoldenEval]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    skill_path = Path(data["skill"])
    evals = []
    seen_ids: set[str] = set()
    for raw in data.get("evals", []):
        eval_id = raw["id"]
        if eval_id in seen_ids:
            raise ValueError(f"duplicate eval id: {eval_id}")
        seen_ids.add(eval_id)
        checks = raw.get("checks")
        if checks is None:
            checks = legacy_checks(raw)
        if not isinstance(checks, list) or not checks:
            raise ValueError(f"eval {eval_id}: checks must be a non-empty list")
        evals.append(GoldenEval(id=eval_id, prompt=raw["prompt"], checks=list(checks)))
    return skill_path, evals


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError(f"{path}:{line_number}: expected KEY=VALUE")
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if not key:
            raise ValueError(f"{path}:{line_number}: missing key")
        if value and key not in os.environ:
            os.environ[key] = value


def resolve_api_config(args: argparse.Namespace) -> tuple[str | None, str | None, str | None, str]:
    api_key = args.api_key or os.environ.get("SKILL_EVAL_API_KEY") or os.environ.get("OPENAI_API_KEY")
    model = args.model or os.environ.get("SKILL_EVAL_MODEL") or os.environ.get("OPENAI_MODEL")
    judge_model = args.judge_model or os.environ.get("SKILL_EVAL_JUDGE_MODEL") or model
    api_base = (args.api_base or os.environ.get("SKILL_EVAL_API_BASE") or DEFAULT_API_BASE).rstrip("/")
    return api_key, model, judge_model, api_base


def chat_completion(
    api_key: str,
    api_base: str,
    model: str,
    messages: list[dict[str, str]],
    *,
    response_format: dict[str, Any] | None = None,
) -> tuple[str, dict[str, Any] | None]:
    request_body: dict[str, Any] = {"model": model, "messages": messages}
    if response_format is not None:
        request_body["response_format"] = response_format
    request = urllib.request.Request(
        f"{api_base}/chat/completions",
        data=json.dumps(request_body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            payload: dict[str, Any] = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"API request failed with HTTP {exc.code}: {body}") from exc
    choices = payload.get("choices") or []
    if not choices:
        raise RuntimeError(f"API response did not include choices: {payload}")
    message = choices[0].get("message") or {}
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError(f"API response did not include message content: {payload}")
    usage = payload.get("usage")
    return content, usage if isinstance(usage, dict) else None


def messages_for_eval(skill_text: str, eval_case: GoldenEval) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "You are evaluating a Neo4j agent skill. Answer the user's task using the supplied "
                "SKILL.md as the authoritative source. Be concise, include runnable code when useful, "
                "and do not invent unsupported syntax."
            ),
        },
        {
            "role": "user",
            "content": f"<SKILL.md>\n{skill_text}\n</SKILL.md>\n\nTask:\n{eval_case.prompt}",
        },
    ]


def messages_for_judge(eval_case: GoldenEval, output: str, criteria: list[dict[str, Any]]) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "You are a strict evaluator for Neo4j documentation agent-skill golden evals. "
                "Grade only the supplied assistant response against the supplied criteria. "
                "Do not require exact wording. Mark a criterion passed when the response clearly conveys "
                "the required meaning. Mark it failed when the meaning is missing, contradicted, or ambiguous."
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "task_prompt": eval_case.prompt,
                    "assistant_response": output,
                    "criteria": criteria,
                    "required_output": {
                        "criteria": [
                            {"id": "criterion id", "passed": True, "evidence": "short quote or paraphrase"}
                        ],
                        "overall_passed": True,
                    },
                },
                indent=2,
            ),
        },
    ]


def scoped_output(output: str, scope: str) -> str:
    if scope == "any":
        return output
    code_blocks = [match.group(1) for match in FENCE_RE.finditer(output)]
    if scope == "code":
        return "\n\n".join(code_blocks)
    if scope == "prose":
        return FENCE_RE.sub("", output)
    raise ValueError(f"unknown check scope: {scope}")


def check_literal(check: dict[str, Any], output: str) -> tuple[bool, str]:
    value = check.get("value")
    if not isinstance(value, str) or not value:
        raise ValueError("literal check requires non-empty string field: value")
    scope = str(check.get("scope", "any"))
    case_sensitive = bool(check.get("caseSensitive", False))
    expected = scoped_output(output, scope)
    haystack = expected if case_sensitive else expected.lower()
    needle = value if case_sensitive else value.lower()
    matched = needle in haystack
    return matched, value


def check_regex(check: dict[str, Any], output: str) -> tuple[bool, str]:
    pattern = check.get("pattern")
    if not isinstance(pattern, str) or not pattern:
        raise ValueError("regex check requires non-empty string field: pattern")
    scope = str(check.get("scope", "any"))
    flags = re.MULTILINE
    if not bool(check.get("caseSensitive", False)):
        flags |= re.IGNORECASE
    matched = re.search(pattern, scoped_output(output, scope), flags=flags) is not None
    return matched, pattern


def evaluate_presence_check(check: dict[str, Any], output: str) -> dict[str, Any]:
    check_type = check.get("type")
    if check_type == "literal":
        matched, label = check_literal(check, output)
    elif check_type == "regex":
        matched, label = check_regex(check, output)
    else:
        raise ValueError(f"unsupported deterministic check type: {check_type}")
    expect = str(check.get("expect", "present"))
    if expect not in {"present", "absent"}:
        raise ValueError(f"check expect must be 'present' or 'absent', got {expect!r}")
    passed = matched if expect == "present" else not matched
    return {
        "type": check_type,
        "scope": check.get("scope", "any"),
        "expect": expect,
        "label": label,
        "blocking": bool(check.get("blocking", True)),
        "passed": passed,
        "matched": matched,
    }


def evaluate_judge_check(
    check: dict[str, Any],
    eval_case: GoldenEval,
    output: str,
    *,
    api_key: str,
    api_base: str,
    judge_model: str,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    criteria = check.get("criteria")
    if not isinstance(criteria, list) or not criteria:
        raise ValueError("llm_judge check requires non-empty list field: criteria")
    for criterion in criteria:
        if not isinstance(criterion, dict) or not isinstance(criterion.get("id"), str):
            raise ValueError("llm_judge criteria must be objects with string id fields")
        if not isinstance(criterion.get("description"), str) or not criterion["description"]:
            raise ValueError(f"llm_judge criterion {criterion.get('id')}: missing description")

    judge_output, usage = chat_completion(
        api_key,
        api_base,
        judge_model,
        messages_for_judge(eval_case, output, criteria),
        response_format=JUDGE_RESPONSE_FORMAT,
    )
    payload = json.loads(judge_output)
    criterion_results = payload.get("criteria", [])
    expected_ids = {criterion["id"] for criterion in criteria}
    returned_ids = {result.get("id") for result in criterion_results if isinstance(result, dict)}
    missing_ids = sorted(expected_ids - returned_ids)
    unexpected_ids = sorted(str(value) for value in returned_ids - expected_ids)
    failed = [result for result in criterion_results if isinstance(result, dict) and result.get("passed") is not True]
    passed = bool(payload.get("overall_passed")) and not missing_ids and not unexpected_ids and not failed
    return {
        "type": "llm_judge",
        "blocking": bool(check.get("blocking", False)),
        "model": judge_model,
        "passed": passed,
        "criteria": criterion_results,
        "missing_criteria": missing_ids,
        "unexpected_criteria": unexpected_ids,
    }, usage


def check_failure_message(result: dict[str, Any]) -> str:
    check_type = result.get("type")
    if result.get("error"):
        return f"{check_type} check error: {result['error']}"
    if check_type in {"literal", "regex"}:
        if result.get("expect") == "present":
            return f"missing {check_type}: {result.get('label')}"
        return f"matched forbidden {check_type}: {result.get('label')}"
    if check_type == "llm_judge":
        failed_parts = []
        for criterion in result.get("criteria", []):
            if isinstance(criterion, dict) and criterion.get("passed") is not True:
                failed_parts.append(f"{criterion.get('id')}: {criterion.get('evidence', '')}")
        for missing in result.get("missing_criteria", []):
            failed_parts.append(f"missing judge result: {missing}")
        for unexpected in result.get("unexpected_criteria", []):
            failed_parts.append(f"unexpected judge result: {unexpected}")
        return "judge criteria failed: " + "; ".join(failed_parts)
    return f"check failed: {result}"


def evaluate_checks(
    eval_case: GoldenEval,
    output: str,
    *,
    api_key: str,
    api_base: str,
    judge_model: str,
) -> CheckEvaluation:
    check_results: list[dict[str, Any]] = []
    blocking_errors: list[str] = []
    advisory_errors: list[str] = []
    judge_usage: list[dict[str, Any]] = []

    for check in eval_case.checks:
        if not isinstance(check, dict):
            raise ValueError(f"eval {eval_case.id}: checks must be objects")
        check_type = check.get("type")
        try:
            if check_type in {"literal", "regex"}:
                result = evaluate_presence_check(check, output)
                usage = None
            elif check_type == "llm_judge":
                result, usage = evaluate_judge_check(
                    check,
                    eval_case,
                    output,
                    api_key=api_key,
                    api_base=api_base,
                    judge_model=judge_model,
                )
            else:
                raise ValueError(f"unsupported check type: {check_type}")
        except Exception as exc:
            result = {
                "type": check_type,
                "blocking": bool(check.get("blocking", check_type != "llm_judge")),
                "passed": False,
                "error": str(exc),
            }
            usage = None

        check_results.append(result)
        if usage is not None:
            judge_usage.append(usage)
        if not result["passed"]:
            message = check_failure_message(result)
            if result.get("blocking", True):
                blocking_errors.append(message)
            else:
                advisory_errors.append(message)

    return CheckEvaluation(
        check_results=check_results,
        blocking_errors=blocking_errors,
        advisory_errors=advisory_errors,
        judge_usage=judge_usage,
    )


def safe_filename(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-") or "eval"


def write_output(output_dir: Path | None, eval_id: str, trial: int, output: str) -> str | None:
    if output_dir is None or not output:
        return None
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{safe_filename(eval_id)}-trial-{trial}.txt"
    output_path.write_text(output, encoding="utf-8")
    return str(output_path)


def append_jsonl(path: Path | None, result: EvalAttemptResult) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(asdict(result), sort_keys=True) + "\n")


def rate(passed: int, total: int) -> float:
    return passed / total if total else 0.0


def build_summary(
    *,
    manifest: Path,
    skill_path: Path,
    model: str,
    judge_model: str,
    repeat: int,
    started_at: str,
    duration_ms: int,
    results: list[EvalAttemptResult],
) -> dict[str, Any]:
    eval_ids = list(dict.fromkeys(result.eval_id for result in results))
    by_eval = {eval_id: [result for result in results if result.eval_id == eval_id] for eval_id in eval_ids}
    passed_attempts = sum(1 for result in results if result.passed)
    advisory_failed_attempts = sum(1 for result in results if result.advisory_errors)
    pass_at_1 = sum(1 for attempts in by_eval.values() if attempts and attempts[0].passed)
    pass_at_n = sum(1 for attempts in by_eval.values() if any(result.passed for result in attempts))
    pass_all_trials = sum(1 for attempts in by_eval.values() if attempts and all(result.passed for result in attempts))
    return {
        "manifest": str(manifest),
        "skill": str(skill_path),
        "model": model,
        "judge_model": judge_model,
        "repeat": repeat,
        "started_at": started_at,
        "duration_ms": duration_ms,
        "eval_count": len(eval_ids),
        "attempt_count": len(results),
        "passed_attempts": passed_attempts,
        "failed_attempts": len(results) - passed_attempts,
        "advisory_failed_attempts": advisory_failed_attempts,
        "pass_at_1": {"passed": pass_at_1, "total": len(eval_ids), "rate": rate(pass_at_1, len(eval_ids))},
        "pass_at_n": {"passed": pass_at_n, "total": len(eval_ids), "rate": rate(pass_at_n, len(eval_ids))},
        "pass_all_trials": {
            "passed": pass_all_trials,
            "total": len(eval_ids),
            "rate": rate(pass_all_trials, len(eval_ids)),
        },
        "results": [asdict(result) for result in results],
    }


def run_manifest(
    manifest: Path,
    *,
    api_key: str,
    api_base: str,
    model: str,
    judge_model: str,
    repeat: int,
    fail_on_advisory: bool,
    json_output: Path | None,
    jsonl_output: Path | None,
    output_dir: Path | None,
) -> int:
    skill_path, evals = load_manifest(manifest)
    skill_text = skill_path.read_text(encoding="utf-8")
    if not evals:
        print(f"ERROR: no evals in {manifest}", file=sys.stderr)
        return 1

    if jsonl_output is not None:
        jsonl_output.parent.mkdir(parents=True, exist_ok=True)
        jsonl_output.write_text("", encoding="utf-8")

    started_at = datetime.now(UTC).isoformat()
    suite_start = time.monotonic()
    results: list[EvalAttemptResult] = []
    for eval_case in evals:
        for trial in range(1, repeat + 1):
            print(f"RUN {eval_case.id} trial {trial}/{repeat}")
            output = ""
            usage: dict[str, Any] | None = None
            error: str | None = None
            attempt_start = time.monotonic()
            try:
                output, usage = chat_completion(api_key, api_base, model, messages_for_eval(skill_text, eval_case))
                evaluation = evaluate_checks(
                    eval_case,
                    output,
                    api_key=api_key,
                    api_base=api_base,
                    judge_model=judge_model,
                )
            except Exception as exc:
                evaluation = CheckEvaluation([], [str(exc)], [], [])
                error = str(exc)
            latency_ms = int((time.monotonic() - attempt_start) * 1000)
            output_path = write_output(output_dir, eval_case.id, trial, output)
            passed = not evaluation.blocking_errors and (not fail_on_advisory or not evaluation.advisory_errors)
            result = EvalAttemptResult(
                eval_id=eval_case.id,
                trial=trial,
                model=model,
                judge_model=judge_model,
                passed=passed,
                latency_ms=latency_ms,
                check_results=evaluation.check_results,
                blocking_errors=evaluation.blocking_errors,
                advisory_errors=evaluation.advisory_errors,
                output_path=output_path,
                output_chars=len(output),
                usage=usage,
                judge_usage=evaluation.judge_usage,
                error=error,
            )
            results.append(result)
            append_jsonl(jsonl_output, result)

            if result.blocking_errors or (fail_on_advisory and result.advisory_errors):
                print(f"FAIL {eval_case.id} trial {trial}/{repeat}", file=sys.stderr)
                for failure in result.blocking_errors:
                    print(f"  {failure}", file=sys.stderr)
                for failure in result.advisory_errors:
                    print(f"  advisory: {failure}", file=sys.stderr)
                if output:
                    print("  output:", file=sys.stderr)
                    print(output, file=sys.stderr)
            elif result.advisory_errors:
                print(f"PASS {eval_case.id} trial {trial}/{repeat} (advisory findings)")
                for finding in result.advisory_errors:
                    print(f"  advisory: {finding}")
            else:
                print(f"PASS {eval_case.id} trial {trial}/{repeat}")

    summary = build_summary(
        manifest=manifest,
        skill_path=skill_path,
        model=model,
        judge_model=judge_model,
        repeat=repeat,
        started_at=started_at,
        duration_ms=int((time.monotonic() - suite_start) * 1000),
        results=results,
    )
    if json_output is not None:
        json_output.parent.mkdir(parents=True, exist_ok=True)
        json_output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(f"Attempt summary: {summary['passed_attempts']} passed, {summary['failed_attempts']} failed")
    if summary["advisory_failed_attempts"]:
        print(f"Advisory findings: {summary['advisory_failed_attempts']} attempt(s)")
    if repeat > 1:
        print(
            "Eval summary: "
            f"pass@1 {summary['pass_at_1']['passed']}/{summary['pass_at_1']['total']}, "
            f"pass@{repeat} {summary['pass_at_n']['passed']}/{summary['pass_at_n']['total']}, "
            f"pass^{repeat} {summary['pass_all_trials']['passed']}/{summary['pass_all_trials']['total']}"
        )
    return 1 if summary["failed_attempts"] else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run golden skill evals through an OpenAI-compatible chat API")
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST), help="Golden eval manifest to run")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="Local KEY=VALUE config file to load before env vars")
    parser.add_argument("--api-base", help=f"API base URL. Defaults to {DEFAULT_API_BASE} or SKILL_EVAL_API_BASE.")
    parser.add_argument("--api-key", help="API key. Defaults to SKILL_EVAL_API_KEY or OPENAI_API_KEY.")
    parser.add_argument("--model", help="Model name. Defaults to SKILL_EVAL_MODEL or OPENAI_MODEL.")
    parser.add_argument("--judge-model", help="Judge model. Defaults to SKILL_EVAL_JUDGE_MODEL or the evaluated model.")
    parser.add_argument("--repeat", type=int, default=1, help="Number of trials to run per eval. Defaults to 1.")
    parser.add_argument("--fail-on-advisory", action="store_true", help="Return non-zero when advisory checks fail.")
    parser.add_argument("--json-output", help="Write aggregate eval summary as JSON.")
    parser.add_argument("--jsonl-output", help="Write one JSON result object per eval trial.")
    parser.add_argument("--output-dir", help="Directory for model output transcripts.")
    parser.add_argument("--require-api", action="store_true", help="Return non-zero instead of skipping when API config is missing.")
    args = parser.parse_args()

    if args.repeat < 1:
        print("ERROR: --repeat must be greater than zero", file=sys.stderr)
        return 1

    load_env_file(Path(args.config))
    api_key, model, judge_model, api_base = resolve_api_config(args)
    if not api_key or not model or not judge_model:
        message = (
            "SKIP: set SKILL_EVAL_MODEL and either SKILL_EVAL_API_KEY or OPENAI_API_KEY "
            "to run golden evals. Set SKILL_EVAL_JUDGE_MODEL to use a separate judge model."
        )
        print(message)
        return 2 if args.require_api else 0
    return run_manifest(
        Path(args.manifest),
        api_key=api_key,
        api_base=api_base,
        model=model,
        judge_model=judge_model,
        repeat=args.repeat,
        fail_on_advisory=args.fail_on_advisory,
        json_output=Path(args.json_output) if args.json_output else None,
        jsonl_output=Path(args.jsonl_output) if args.jsonl_output else None,
        output_dir=Path(args.output_dir) if args.output_dir else None,
    )


if __name__ == "__main__":
    raise SystemExit(main())
