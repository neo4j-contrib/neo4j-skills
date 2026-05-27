#!/usr/bin/env python3
"""Validate Neo4j skill Markdown files."""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

ALLOWED_FIELDS = {
    "name",
    "description",
    "license",
    "compatibility",
    "metadata",
    "allowed-tools",
    "version",
    "status",
}
NAME_RE = re.compile(r"^(?!-)(?!.*--)[a-z0-9-]{1,64}(?<!-)$")
LOCAL_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
FENCED_CODE_RE = re.compile(r"(?ms)^```.*?^```")
INLINE_CODE_RE = re.compile(r"`[^`\n]+`")
SQL_COMMENT_RE = re.compile(r"--(?!>)\s")
PASSWORD_ASSIGNMENT_RE = re.compile(
    r"""(?ix)
    \b(?:password|passwd|pwd|neo4j_password|authentication\.password)\b
    \s*[:=]\s*
    (?P<quote>['"]?)
    (?P<value>[A-Za-z0-9_@#%+=.,:/-]{6,})
    (?P=quote)
    """
)
PASSWORD_PLACEHOLDERS = {
    "changeme",
    "change-me",
    "example-password",
    "password",
    "secret",
    "your-password",
}
CONFIG_PASSWORD_SOURCES = (
    "System.getenv",
    "os.getenv",
    "os.environ",
    "process.env",
    "builder.Configuration",
    "Configuration[",
    "NEO4J_PASSWORD",
    "$",
    "<",
)
SECRET_PATTERNS = [
    ("OpenAI API key", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b")),
    ("GitHub token", re.compile(r"\bgh[opsu]_[A-Za-z0-9_]{20,}\b")),
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("private key block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
]


@dataclass
class Frontmatter:
    fields: dict[str, str]
    raw_lines: list[str]
    body_start_line: int


class SkillLintError(Exception):
    pass


def parse_frontmatter(path: Path) -> Frontmatter:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        raise SkillLintError("missing opening frontmatter delimiter")
    end = None
    for idx, line in enumerate(lines[1:], 1):
        if line.strip() == "---":
            end = idx
            break
    if end is None:
        raise SkillLintError("missing closing frontmatter delimiter")

    fields: dict[str, str] = {}
    current_key: str | None = None
    for raw in lines[1:end]:
        if not raw.strip():
            continue
        if raw.startswith((" ", "\t")):
            if current_key is None:
                raise SkillLintError(f"frontmatter continuation without key: {raw!r}")
            fields[current_key] = f"{fields[current_key]} {raw.strip()}".strip()
            continue
        if ":" not in raw:
            raise SkillLintError(f"invalid frontmatter line: {raw!r}")
        key, value = raw.split(":", 1)
        key = key.strip()
        if not key:
            raise SkillLintError(f"empty frontmatter key: {raw!r}")
        current_key = key
        fields[key] = value.strip().strip('"').strip("'")
    return Frontmatter(fields=fields, raw_lines=lines[1:end], body_start_line=end + 2)


def is_external_link(target: str) -> bool:
    return bool(re.match(r"^[a-z][a-z0-9+.-]*:", target, re.I)) or target.startswith("#")


def normalize_link_target(target: str) -> str:
    target = target.strip()
    target = target.split("#", 1)[0]
    target = target.rstrip(".,;:")
    if target.startswith("./"):
        target = target[2:]
    return target


def strip_fenced_code(text: str) -> str:
    """Remove fenced code block content while preserving line numbers."""

    def replace(match: re.Match[str]) -> str:
        return "\n" * match.group(0).count("\n")

    return FENCED_CODE_RE.sub(replace, text)


def strip_inline_code(text: str) -> str:
    return INLINE_CODE_RE.sub("", text)


def check_local_links(path: Path, text: str) -> list[str]:
    errors: list[str] = []
    base = path.parent
    prose_text = strip_fenced_code(text)
    markdown_link_text = strip_inline_code(prose_text)
    for match in LOCAL_LINK_RE.finditer(markdown_link_text):
        raw_target = match.group(1).strip()
        if not raw_target or is_external_link(raw_target):
            continue
        target = normalize_link_target(raw_target)
        if not target:
            continue
        if not (base / target).exists():
            errors.append(f"local Markdown link target does not exist: {raw_target}")
    return errors


def check_cypher_sql_comments(path: Path, text: str) -> list[str]:
    errors: list[str] = []
    in_cypher = False
    block_start_line = 0
    for line_number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not in_cypher:
            if stripped.startswith("```cypher"):
                in_cypher = True
                block_start_line = line_number
        elif stripped.startswith("```"):
            in_cypher = False
        elif SQL_COMMENT_RE.search(line):
            errors.append(
                f"{line_number}: SQL-style '--' comment in Cypher block; use '//' instead: {line.rstrip()!r}"
            )
    if in_cypher:
        errors.append(f"{block_start_line}: unclosed ```cypher block")
    return errors


def check_hardcoded_passwords(text: str) -> list[str]:
    errors: list[str] = []
    for line_number, line in enumerate(text.splitlines(), 1):
        if any(source in line for source in CONFIG_PASSWORD_SOURCES):
            continue
        for match in PASSWORD_ASSIGNMENT_RE.finditer(line):
            value = match.group("value").strip().strip('"').strip("'")
            if value.lower() in PASSWORD_PLACEHOLDERS:
                continue
            errors.append(f"possible secret (hard-coded password) at line {line_number}")
    return errors


def check_secrets(text: str) -> list[str]:
    errors: list[str] = []
    for label, pattern in SECRET_PATTERNS:
        for match in pattern.finditer(text):
            line = text.count("\n", 0, match.start()) + 1
            errors.append(f"possible secret ({label}) at line {line}")
    errors.extend(check_hardcoded_passwords(text))
    return errors


def lint_skill_dir(skill_dir: Path) -> list[str]:
    errors: list[str] = []
    skill_file = skill_dir / "SKILL.md"
    if not skill_file.exists():
        return [f"{skill_dir}/SKILL.md: missing; every skill directory must contain a SKILL.md"]

    text = skill_file.read_text(encoding="utf-8")
    line_count = len(text.splitlines())
    if line_count > 500:
        errors.append(f"{skill_file}: SKILL.md has {line_count} lines; limit is 500")

    try:
        fm = parse_frontmatter(skill_file)
    except SkillLintError as exc:
        return [f"{skill_file}: {exc}"]

    fields = fm.fields
    for required in ("name", "description"):
        if required not in fields or not fields[required].strip():
            errors.append(f"{skill_file}: missing required frontmatter field: {required}")

    unknown = sorted(set(fields) - ALLOWED_FIELDS)
    if unknown:
        errors.append(f"{skill_file}: unknown frontmatter fields: {', '.join(unknown)}")

    name = fields.get("name", "")
    if name and name != skill_dir.name:
        errors.append(f"{skill_file}: name {name!r} does not match directory {skill_dir.name!r}")
    if name and not NAME_RE.match(name):
        errors.append(f"{skill_file}: invalid skill name format: {name!r}")

    description = fields.get("description", "")
    if description and not (80 <= len(description) <= 1024):
        errors.append(f"{skill_file}: description length {len(description)} outside 80-1024 characters")

    compatibility = fields.get("compatibility")
    if compatibility and len(compatibility) > 500:
        errors.append(f"{skill_file}: compatibility length {len(compatibility)} exceeds 500 characters")

    errors.extend(f"{skill_file}: {err}" for err in check_local_links(skill_file, text))
    errors.extend(f"{skill_file}: {err}" for err in check_cypher_sql_comments(skill_file, text))
    errors.extend(f"{skill_file}: {err}" for err in check_secrets(text))
    return errors


def resolve_skill_dirs(paths: Iterable[str]) -> list[Path]:
    dirs: list[Path] = []
    for raw in paths:
        path = Path(raw)
        if path.is_file():
            if path.name != "SKILL.md":
                raise SystemExit(f"ERROR: expected SKILL.md file, got {path}")
            dirs.append(path.parent)
        else:
            dirs.append(path)
    return dirs


def git_tracked_paths(root: Path) -> set[Path]:
    try:
        result = subprocess.run(
            ["git", "ls-files"],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        )
        return {root / line for line in result.stdout.splitlines()}
    except Exception:
        return set()


def discover_skill_dirs(root: Path) -> list[Path]:
    tracked = git_tracked_paths(root)
    if tracked:
        tracked_skill_dirs = {path.parent for path in tracked if path.name == "SKILL.md" and path.parent.name.endswith("-skill")}
        filesystem_skill_dirs = {path for path in root.glob("*-skill") if path.is_dir()}
        return sorted(tracked_skill_dirs | filesystem_skill_dirs)
    return sorted(path for path in root.glob("*-skill") if path.is_dir())


def main() -> int:
    parser = argparse.ArgumentParser(description="Lint Neo4j skill Markdown files")
    parser.add_argument(
        "--skill-dir",
        action="append",
        default=[],
        help="Skill directory or SKILL.md to lint. Defaults to every *-skill/SKILL.md under the repo root.",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    skill_dirs = resolve_skill_dirs(args.skill_dir) if args.skill_dir else discover_skill_dirs(root)
    all_errors: list[str] = []
    seen_names: dict[str, Path] = {}

    if not skill_dirs:
        print("ERROR: no skill directories found", file=sys.stderr)
        return 1

    for skill_dir in skill_dirs:
        errors = lint_skill_dir(skill_dir)
        all_errors.extend(errors)
        skill_file = skill_dir / "SKILL.md"
        if skill_file.exists():
            try:
                name = parse_frontmatter(skill_file).fields.get("name")
            except SkillLintError:
                name = None
            if name:
                if name in seen_names:
                    all_errors.append(f"{skill_file}: duplicate skill name {name!r}; first seen in {seen_names[name]}")
                seen_names[name] = skill_file

    if all_errors:
        for error in all_errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"PASS: linted {len(skill_dirs)} skill(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
