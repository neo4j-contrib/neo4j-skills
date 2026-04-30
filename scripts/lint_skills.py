#!/usr/bin/env python3
"""Lint SKILL.md frontmatter against the agentskills.io specification."""
from __future__ import annotations

import re
import sys
from pathlib import Path

# agentskills.io spec rules
NAME_RE = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
NAME_MAX = 64
DESC_MAX = 1024
DESC_MIN = 80   # below this is almost certainly too terse to be useful
COMPAT_MAX = 500
KNOWN_EXTRA_FIELDS = {'status', 'version'}  # non-spec but tolerated in this repo

# Cypher uses // for comments; -- is SQL syntax and a parse error in Cypher
# Match -- comment anywhere on a line (inline or leading), but not --> (ASCII arrows)
SQL_COMMENT_RE = re.compile(r'--(?!>)\s')

ERRORS = []
WARNINGS = []


def parse_frontmatter(text: str) -> dict:
    """Return frontmatter key/value dict, or None if no valid frontmatter block."""
    if not text.startswith('---'):
        return None
    end = text.find('\n---', 3)
    if end == -1:
        return None
    block = text[3:end].strip()
    result: dict = {}
    current_key = None
    current_lines: list[str] = []

    for line in block.splitlines():
        if line and not line[0].isspace():
            if current_key is not None:
                result[current_key] = '\n'.join(current_lines).strip()
            m = re.match(r'^([\w-]+):\s*(.*)', line)
            if m:
                current_key = m.group(1)
                current_lines = [m.group(2)]
            else:
                current_key = None
                current_lines = []
        elif current_key is not None:
            current_lines.append(line.strip())

    if current_key is not None:
        result[current_key] = '\n'.join(current_lines).strip()

    return result


def lint_skill(path: Path) -> list[str]:
    errors: list[str] = []
    text = path.read_text(encoding='utf-8')
    fm = parse_frontmatter(text)

    if fm is None:
        return [f"{path}: missing or malformed frontmatter block"]

    # --- name ---
    name = fm.get('name', '').strip()
    if not name:
        errors.append(f"{path}: 'name' is required")
    else:
        if len(name) > NAME_MAX:
            errors.append(f"{path}: 'name' exceeds {NAME_MAX} chars ({len(name)})")
        if not NAME_RE.match(name):
            errors.append(
                f"{path}: 'name' must be lowercase alphanumeric with hyphens, got {name!r}"
            )
        expected = path.parent.name
        if name != expected:
            errors.append(
                f"{path}: 'name' ({name!r}) must match parent directory ({expected!r})"
            )

    # --- description ---
    desc = fm.get('description', '').strip()
    if not desc:
        errors.append(f"{path}: 'description' is required")
    else:
        if len(desc) > DESC_MAX:
            errors.append(
                f"{path}: 'description' exceeds {DESC_MAX} chars ({len(desc)})"
            )
        if len(desc) < DESC_MIN:
            errors.append(
                f"{path}: 'description' is too short ({len(desc)} chars, min {DESC_MIN}) — "
                "should describe what the skill does AND when to use it"
            )

    # --- compatibility (optional) ---
    compat = fm.get('compatibility', '').strip()
    if compat and len(compat) > COMPAT_MAX:
        errors.append(
            f"{path}: 'compatibility' exceeds {COMPAT_MAX} chars ({len(compat)})"
        )

    # --- unknown non-spec fields ---
    spec_fields = {'name', 'description', 'license', 'compatibility', 'metadata', 'allowed-tools'}
    for key in fm:
        if key not in spec_fields and key not in KNOWN_EXTRA_FIELDS:
            errors.append(
                f"{path}: unknown frontmatter field {key!r} (not in agentskills.io spec)"
            )

    # --- SQL-style comments in Cypher blocks ---
    errors.extend(_check_cypher_sql_comments(path, text))

    return errors


def _check_cypher_sql_comments(path: Path, text: str) -> list[str]:
    """Scan ```cypher blocks for SQL-style -- comments (parse errors in Cypher)."""
    errors: list[str] = []
    in_cypher = False
    block_start_line = 0
    for lineno, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not in_cypher:
            if stripped.startswith('```cypher'):
                in_cypher = True
                block_start_line = lineno
        else:
            if stripped.startswith('```'):
                in_cypher = False
            elif SQL_COMMENT_RE.search(line):
                errors.append(
                    f"{path}:{lineno}: SQL-style '--' comment in Cypher block "
                    f"(use '//' instead): {line.rstrip()!r}"
                )
    if in_cypher:
        errors.append(f"{path}:{block_start_line}: unclosed ```cypher block")
    return errors


def git_tracked_paths(root: Path) -> set[Path]:
    """Return set of paths tracked by git, or empty set if git is unavailable."""
    import subprocess
    try:
        result = subprocess.run(
            ['git', 'ls-files'],
            cwd=root, capture_output=True, text=True, check=True
        )
        return {root / line for line in result.stdout.splitlines()}
    except Exception:
        return set()


def main() -> int:
    root = Path(__file__).parent.parent
    tracked = git_tracked_paths(root)

    # Use git-tracked paths when available, fall back to filesystem glob
    if tracked:
        skill_dirs = sorted({p.parent for p in tracked if p.parent.name.endswith('-skill')})
        skill_files = sorted(p for p in tracked if p.name == 'SKILL.md' and p.parent.name.endswith('-skill'))
    else:
        skill_dirs = sorted(root.glob('*-skill'))
        skill_files = sorted(root.glob('*-skill/SKILL.md'))

    all_errors: list[str] = []

    # Flag skill directories with no SKILL.md
    skill_file_dirs = {p.parent for p in skill_files}
    for d in skill_dirs:
        if d.is_dir() and d not in skill_file_dirs:
            all_errors.append(f"{d}/SKILL.md: missing — every skill directory must contain a SKILL.md")

    if not skill_files:
        print("No SKILL.md files found.", file=sys.stderr)
        return 1

    for path in skill_files:
        all_errors.extend(lint_skill(path))

    if all_errors:
        print(f"Found {len(all_errors)} frontmatter violation(s):\n")
        for err in all_errors:
            print(f"  ✗ {err}")
        return 1

    print(f"All {len(skill_files)} SKILL.md file(s) passed frontmatter lint.")
    return 0


if __name__ == '__main__':
    sys.exit(main())
