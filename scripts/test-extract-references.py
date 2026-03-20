#!/usr/bin/env python3
"""
Tests for extract-references.py
Run from the repo root: python3 scripts/test-extract-references.py
"""
import importlib.util
import os
import sys
import tempfile
from pathlib import Path

# Load module under test
spec = importlib.util.spec_from_file_location("extract", "scripts/extract-references.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

REPO_ROOT = Path(".")
CYPHER_SRC = REPO_ROOT / "docs-cypher/modules/ROOT/pages"
CHEAT_SRC = REPO_ROOT / "docs-cheat-sheet/modules/ROOT/pages"
GQL_EXCLUDE = ["LET", "FINISH", "FILTER", "NEXT", "INSERT"]

failures = []


def check(name: str, condition: bool, msg: str = ""):
    if condition:
        print(f"  PASS  {name}")
    else:
        print(f"  FAIL  {name}" + (f": {msg}" if msg else ""))
        failures.append(name)


# ---------------------------------------------------------------------------
# Test 1: dry-run prints planned files without writing
# ---------------------------------------------------------------------------
print("\n--- Test 1: dry-run mode ---")
with tempfile.TemporaryDirectory() as tmpdir:
    out_dir = Path(tmpdir) / "refs"
    rc = os.system(
        f"python3 scripts/extract-references.py --dry-run --out {out_dir} > /dev/null 2>&1"
    )
    check("dry-run exits 0", rc == 0)
    check("dry-run does not create output dir", not out_dir.exists())


# ---------------------------------------------------------------------------
# Test 2: Source header format
# ---------------------------------------------------------------------------
print("\n--- Test 2: Source header ---")
with tempfile.TemporaryDirectory() as tmpdir:
    out_dir = Path(tmpdir) / "refs"
    os.system(
        f"python3 scripts/extract-references.py --only read/cypher25-patterns.md --out {out_dir} > /dev/null 2>&1"
    )
    out_file = out_dir / "read" / "cypher25-patterns.md"
    check("output file created", out_file.exists())
    if out_file.exists():
        content = out_file.read_text()
        check("header contains '> Source:'", "> Source:" in content)
        check("header contains '> Generated:'", "> Generated:" in content)
        check("header contains SHA", "238ab12a" in content or "e11fe2f2" in content)


# ---------------------------------------------------------------------------
# Test 3: GQL exclusion — headings
# ---------------------------------------------------------------------------
print("\n--- Test 3: GQL exclusion (headings) ---")
sample_adoc = """\
= Test doc

== LET

Some text about LET.

== Normal section

Normal content here.

== FINISH

Some FINISH content.
"""
result = mod.adoc_to_markdown(sample_adoc, GQL_EXCLUDE)
check("LET heading excluded", "# LET" not in result and "## LET" not in result)
check("FINISH heading excluded", "# FINISH" not in result and "## FINISH" not in result)
check("Normal section preserved", "Normal section" in result)
check("Normal content preserved", "Normal content here" in result)


# ---------------------------------------------------------------------------
# Test 4: Section-not-found WARNING
# ---------------------------------------------------------------------------
print("\n--- Test 4: Missing section WARNING ---")
import io
import contextlib

styleguide = CYPHER_SRC / "styleguide.adoc"
if styleguide.exists():
    stderr_capture = io.StringIO()
    with contextlib.redirect_stderr(stderr_capture):
        _, warnings = mod.extract_file(
            styleguide,
            gql_exclude=GQL_EXCLUDE,
            max_tokens=4000,
            expected_sections=["NONEXISTENT SECTION XYZ"],
        )
    stderr_out = stderr_capture.getvalue()
    check("WARNING in warnings list", any("WARNING: section not found" in w for w in warnings))
    check("WARNING written to stderr", "WARNING: section not found" in stderr_out)
else:
    print("  SKIP  styleguide.adoc not found")


# ---------------------------------------------------------------------------
# Test 5: Token budget enforcement
# ---------------------------------------------------------------------------
print("\n--- Test 5: Token budget ---")
with tempfile.TemporaryDirectory() as tmpdir:
    out_dir = Path(tmpdir) / "refs"
    os.system(
        f"python3 scripts/extract-references.py --max-tokens 2000 --out {out_dir} > /dev/null 2>&1"
    )
    over_budget = []
    for md_file in out_dir.rglob("*.md"):  # rglob to find files in subdirectories
        size = md_file.stat().st_size
        approx_tokens = size // 4
        if approx_tokens > 2000:
            over_budget.append(f"{md_file.name}: ~{approx_tokens} tokens")
    check(
        "all output files ≤ 2000 tokens",
        len(over_budget) == 0,
        "; ".join(over_budget),
    )


# ---------------------------------------------------------------------------
# Test 6: Code fence language tags
# ---------------------------------------------------------------------------
print("\n--- Test 6: Code fence language tags ---")
sample_adoc = """\
= Test

[source, cypher]
----
MATCH (n) RETURN n
----

[source, role=noheader]
----
something
----
"""
result = mod.adoc_to_markdown(sample_adoc, GQL_EXCLUDE)
check("cypher fence has language tag", "```cypher" in result)
check("noheader fence has no 'role' tag", "```role" not in result)


# ---------------------------------------------------------------------------
# Test 7: flags accepted (CLI help)
# ---------------------------------------------------------------------------
print("\n--- Test 7: CLI flags accepted ---")
rc = os.system("python3 scripts/extract-references.py --help > /dev/null 2>&1")
check("--help exits 0", rc == 0)


# ---------------------------------------------------------------------------
# Test 8: //// comment block stripping
# ---------------------------------------------------------------------------
print("\n--- Test 8: Comment block stripping (////) ---")
sample_adoc = """\
= Test

////
[source, cypher, role=test-setup]
----
CREATE (n:Person {name: 'Alice'})
----
////

== Real Section

Real content here.
"""
result = mod.adoc_to_markdown(sample_adoc, GQL_EXCLUDE)
check("CREATE inside //// is stripped", "CREATE" not in result)
check("Real section preserved after comment block", "Real Section" in result)
check("Real content preserved", "Real content here" in result)


# ---------------------------------------------------------------------------
# Test 9: role=test-setup source block stripping
# ---------------------------------------------------------------------------
print("\n--- Test 9: test-setup block stripping ---")
sample_adoc = """\
= Test

[source, cypher, role=test-setup]
----
CREATE (:Person {name: 'Setup'})
----

== Usage

[source, cypher]
----
MATCH (n:Person) RETURN n
----
"""
result = mod.adoc_to_markdown(sample_adoc, GQL_EXCLUDE)
check("test-setup CREATE block stripped", "Setup" not in result)
check("regular code block preserved", "MATCH (n:Person) RETURN n" in result)


# ---------------------------------------------------------------------------
# Test 10: [.description] annotation stripping
# ---------------------------------------------------------------------------
print("\n--- Test 10: dot-notation annotation stripping ---")
sample_adoc = """\
= Test

[source, cypher, role=noheader]
----
MATCH (n) RETURN n
----

[.description]
This describes the example above.

[.label--new-2025-06]
Some new feature text.
"""
result = mod.adoc_to_markdown(sample_adoc, GQL_EXCLUDE)
check("[.description] annotation line stripped", "[.description]" not in result)
check("[.label--new-2025-06] annotation line stripped", "[.label--new-2025-06]" not in result)
check("description text preserved", "This describes the example above." in result)


# ---------------------------------------------------------------------------
# Test 11: queryresult table skipping
# ---------------------------------------------------------------------------
print("\n--- Test 11: queryresult table skipping ---")
sample_adoc = """\
= Test

== Results

[role="queryresult",options="header,footer",cols="1*<m"]
|===
| name
| "Alice"
1+d|Rows: 1
|===

== Other

Some other content.
"""
result = mod.adoc_to_markdown(sample_adoc, GQL_EXCLUDE)
check("queryresult table stripped", '"Alice"' not in result)
check("other content preserved", "Other" in result)


# ---------------------------------------------------------------------------
# Test 12: skip_preamble flag
# ---------------------------------------------------------------------------
print("\n--- Test 12: skip_preamble ---")
sample_adoc = """\
= Title

This is preamble text that should be skipped.
More preamble content here.

== First Real Section

Real content.
"""
result_with = mod.adoc_to_markdown(sample_adoc, GQL_EXCLUDE, skip_preamble=True)
result_without = mod.adoc_to_markdown(sample_adoc, GQL_EXCLUDE, skip_preamble=False)
check("preamble stripped when skip_preamble=True", "preamble text" not in result_with)
check("preamble present when skip_preamble=False", "preamble text" in result_without)
check("heading preserved with skip_preamble=True", "First Real Section" in result_with)
check("real content preserved with skip_preamble=True", "Real content" in result_with)


# ---------------------------------------------------------------------------
# Test 13: max_code_blocks limit
# ---------------------------------------------------------------------------
print("\n--- Test 13: max_code_blocks ---")
sample_adoc = """\
= Test

[source, cypher]
----
MATCH (a) RETURN a
----

[source, cypher]
----
MATCH (b) RETURN b
----

[source, cypher]
----
MATCH (c) RETURN c
----
"""
result_limit1 = mod.adoc_to_markdown(sample_adoc, GQL_EXCLUDE, max_code_blocks=1)
result_limit2 = mod.adoc_to_markdown(sample_adoc, GQL_EXCLUDE, max_code_blocks=2)
result_nolimit = mod.adoc_to_markdown(sample_adoc, GQL_EXCLUDE, max_code_blocks=0)
check("max_code_blocks=1 keeps only first block", "RETURN a" in result_limit1 and "RETURN b" not in result_limit1)
check("max_code_blocks=2 keeps first two blocks", "RETURN b" in result_limit2 and "RETURN c" not in result_limit2)
check("max_code_blocks=0 keeps all blocks", all(x in result_nolimit for x in ["RETURN a", "RETURN b", "RETURN c"]))


# ---------------------------------------------------------------------------
# Test 14: include:: resolution with tag extraction
# ---------------------------------------------------------------------------
print("\n--- Test 14: include:: resolution ---")
import tempfile, textwrap

with tempfile.TemporaryDirectory() as tmpdir:
    tmppath = Path(tmpdir)

    # Create a "source" file with tagged sections
    source_file = tmppath / "source.adoc"
    source_file.write_text(textwrap.dedent("""\
        = Source Doc

        // tag::good_example[]
        [source, cypher]
        ----
        MATCH (n:Good) RETURN n
        ----
        // end::good_example[]

        // tag::other_example[]
        [source, cypher]
        ----
        MATCH (n:Other) RETURN n
        ----
        // end::other_example[]
    """))

    # Create a "main" file that includes from the source
    main_file = tmppath / "main.adoc"
    main_file.write_text(textwrap.dedent("""\
        = Main Doc

        == Example

        include::source.adoc[tag=good_example]

        Some description text.
    """))

    # Resolve includes
    raw = main_file.read_text()
    # Use a dummy cypher_src that won't match
    dummy_src = tmppath / "nonexistent"
    resolved = mod.resolve_includes(raw, main_file, dummy_src, dummy_src)
    md = mod.adoc_to_markdown(resolved, GQL_EXCLUDE)

    check("included tagged content present", "MATCH (n:Good) RETURN n" in md)
    check("excluded tag not included", "MATCH (n:Other) RETURN n" not in md)
    check("surrounding content preserved", "Example" in md and "Some description text" in md)


# ---------------------------------------------------------------------------
# Test 15a: tag marker stripping
# ---------------------------------------------------------------------------
print("\n--- Test 15a: tag marker stripping ---")
sample_adoc = """\
= Test

// tag::my_example[]
[source, cypher]
----
MATCH (n) RETURN n
----
// end::my_example[]

Some text after.
"""
result = mod.adoc_to_markdown(sample_adoc, GQL_EXCLUDE)
check("// tag:: line stripped", "// tag::" not in result)
check("// end:: line stripped", "// end::" not in result)
check("cypher block within tags preserved", "MATCH (n) RETURN n" in result)
check("text after tags preserved", "Some text after" in result)


# ---------------------------------------------------------------------------
# Test 15: new CLI flags accepted
# ---------------------------------------------------------------------------
print("\n--- Test 15: new CLI flags ---")
rc = os.system("python3 scripts/extract-references.py --skip-preamble --max-code-blocks 3 --dry-run > /dev/null 2>&1")
check("--skip-preamble --max-code-blocks accepted", rc == 0)


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print()
if failures:
    print(f"FAILED: {len(failures)} test(s): {', '.join(failures)}")
    sys.exit(1)
else:
    print(f"ALL TESTS PASSED")
    sys.exit(0)
