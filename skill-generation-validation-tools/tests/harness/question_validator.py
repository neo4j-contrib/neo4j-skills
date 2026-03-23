#!/usr/bin/env python3
"""
question_validator.py — Business-language question validator.

Checks that test case questions are phrased as casual, business-user questions
(the kind a non-technical analyst or product manager would ask) and do NOT
contain:
  - Graph labels (e.g. :Person, :Movie)
  - Relationship types (e.g. [:ACTED_IN], HAS_SUBSIDIARY)
  - Cypher keywords (MATCH, WHERE, RETURN, WITH, CALL, MERGE, CREATE, etc.)
  - Property dot-access syntax (.name, .rating)
  - GDS/APOC/db.index procedure prefixes
  - Known schema label/rel-type names from the passed schema dict

Usage:
    from question_validator import QuestionValidator
    validator = QuestionValidator(schema=schema_dict)
    ok, reason = validator.validate("Which companies have no subsidiaries?")
    if not ok:
        print(f"INVALID: {reason}")

    # Or using the module-level helper (no schema-awareness):
    from question_validator import validate
    ok, reason = validate("MATCH (n:Org) RETURN n")
"""

from __future__ import annotations

import re
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Static Cypher keyword list (high-signal keywords to reject in questions)
# ---------------------------------------------------------------------------

_CYPHER_KEYWORDS = frozenset(
    [
        # High-signal DML / DDL clauses (rarely appear as English words in questions)
        "MATCH",
        "MERGE",
        "CREATE",
        "DELETE",
        "DETACH",
        "FOREACH",
        "UNWIND",
        "RETURN",
        "UNION",
        "CALL",
        "YIELD",
        # Expression keywords that should not appear in casual business questions
        "COLLECT",
        "DISTINCT",
        "SHORTEST",
        "PROFILE",
        "EXPLAIN",
        "CYPHER",
        # GQL-only (should not appear in valid queries either)
        "FINISH",
        "INSERT",
    ]
)

# Procedure/function prefixes that signal Cypher code
_PROCEDURE_PREFIXES = [
    "gds.",
    "apoc.",
    "db.index.",
    "db.schema.",
    "dbms.",
    "ai.",
    "vector.",
    "algo.",
]

# Pattern: colon followed by an uppercase word — Cypher node label syntax (:Label)
_LABEL_PATTERN = re.compile(r":\s*[A-Z][A-Za-z0-9_]*")

# Pattern: ALL_CAPS_UNDERSCORE word of 3+ chars — likely a relationship type
_REL_TYPE_PATTERN = re.compile(r"\b([A-Z]{2,}(?:_[A-Z]{2,})+)\b")

# Pattern: word.property access (e.g. n.name, movie.released)
# Allow common English abbreviations (U.S., a.m., i.e., etc.) by requiring lowercase after dot
_DOT_ACCESS_PATTERN = re.compile(r"\b\w{2,}\.[a-z][a-zA-Z0-9_]{1,}")


class QuestionValidator:
    """
    Validates that a question string is phrased in casual business language.

    Args:
        schema: Optional dict (from dataset.schema) used for schema-aware
                rejection of known label names and relationship type names.
    """

    def __init__(self, schema: Optional[dict[str, Any]] = None) -> None:
        self._schema_labels: frozenset[str] = frozenset()
        self._schema_rel_types: frozenset[str] = frozenset()

        if schema and isinstance(schema, dict):
            # Collect known label names from schema.nodes
            nodes = schema.get("nodes", {})
            if isinstance(nodes, dict):
                self._schema_labels = frozenset(nodes.keys())

            # Collect known relationship type names from schema.relationships
            rels = schema.get("relationships", [])
            if isinstance(rels, list):
                types: list[str] = []
                for r in rels:
                    if isinstance(r, dict) and r.get("type"):
                        types.append(str(r["type"]))
                self._schema_rel_types = frozenset(types)

    def validate(self, question: str) -> tuple[bool, str]:
        """
        Check whether the question is valid business language.

        Returns:
            (True, "")             — valid question
            (False, reason_str)    — invalid, with a description of why
        """
        if not question or not question.strip():
            return False, "Empty question"

        q = question.strip()

        # ── Cypher label syntax (:Label) ─────────────────────────────────────
        label_m = _LABEL_PATTERN.search(q)
        if label_m:
            return False, f"Contains Cypher label syntax: '{label_m.group(0)}'"

        # ── Cypher keywords (whole-word, case-insensitive) ────────────────────
        words = re.findall(r"\b[A-Za-z]{2,}\b", q)
        for word in words:
            if word.upper() in _CYPHER_KEYWORDS:
                return False, f"Contains Cypher keyword: '{word}'"

        # ── Procedure/function prefixes ───────────────────────────────────────
        q_lower = q.lower()
        for prefix in _PROCEDURE_PREFIXES:
            if prefix in q_lower:
                return False, f"Contains procedure prefix: '{prefix}'"

        # ── Dot-access property syntax ────────────────────────────────────────
        dot_m = _DOT_ACCESS_PATTERN.search(q)
        if dot_m:
            return False, f"Contains dot-access property syntax: '{dot_m.group(0)}'"

        # ── Relationship-type pattern (ALL_CAPS_WITH_UNDERSCORES) ─────────────
        rel_m = _REL_TYPE_PATTERN.search(q)
        if rel_m:
            return False, f"Contains relationship-type pattern: '{rel_m.group(0)}'"

        # ── Schema-aware: known label names ───────────────────────────────────
        for label in self._schema_labels:
            # Use word-boundary matching to avoid false positives on substrings
            if re.search(r"\b" + re.escape(label) + r"\b", q):
                return False, f"Contains schema label name: '{label}'"

        # ── Schema-aware: known relationship type names ───────────────────────
        for rel_type in self._schema_rel_types:
            if re.search(r"\b" + re.escape(rel_type) + r"\b", q):
                return False, f"Contains schema relationship type: '{rel_type}'"

        return True, ""


# ---------------------------------------------------------------------------
# Module-level convenience function (no schema awareness)
# ---------------------------------------------------------------------------


def validate(question: str, schema: Optional[dict[str, Any]] = None) -> tuple[bool, str]:
    """
    Validate a question string.

    Args:
        question: The question text to validate.
        schema:   Optional dataset schema dict for schema-aware validation.

    Returns:
        (True, "")          — valid business-language question
        (False, reason)     — invalid, with explanation
    """
    v = QuestionValidator(schema=schema)
    return v.validate(question)


# ---------------------------------------------------------------------------
# Self-test when run directly
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    _TESTS = [
        # (question, expected_valid)
        ("Which companies have more than 5 subsidiaries?", True),
        ("Show me the top 10 movies by average rating", True),
        ("What are the most popular tags in the last year?", True),
        ("Find all (:Organization)-[:HAS_SUBSIDIARY]->() with depth > 2", False),
        ("MATCH (n:Movie) RETURN n.title LIMIT 10", False),
        ("Use COLLECT subquery to aggregate results", False),
        ("Where gds.pageRank is highest", False),
        ("Use apoc.text.split to tokenize names", False),
        ("Get the movie.title for films after 2000", False),
        ("List HAS_SUBSIDIARY chains longer than 3 hops", False),
    ]

    schema_for_test = {
        "nodes": {"Organization": {}, "Article": {}},
        "relationships": [{"type": "HAS_SUBSIDIARY"}, {"type": "MENTIONS"}],
    }

    validator = QuestionValidator(schema=schema_for_test)
    passed = 0
    failed = 0
    for question, expected in _TESTS:
        ok, reason = validator.validate(question)
        status = "PASS" if ok == expected else "FAIL"
        if ok == expected:
            passed += 1
        else:
            failed += 1
        print(f"[{status}] {ok!s:5} expected={expected!s:5}  {question[:60]}")
        if not ok:
            print(f"         Reason: {reason}")

    print(f"\n{passed}/{passed + failed} tests passed")
    if failed:
        raise SystemExit(1)
