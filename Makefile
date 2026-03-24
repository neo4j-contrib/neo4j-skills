# neo4j-skills Makefile
# Usage: make <target>
#
# Harness runs write JSON reports to skill-generation-validation-tools/tests/results/
# and Markdown reports alongside them (same stem, .md extension).
# Pass WORKERS=N for parallel Claude invocations, e.g.: make test-all WORKERS=4

HARNESS   := uv run --project skill-generation-validation-tools python3 skill-generation-validation-tools/tests/harness/runner.py
REPORTER  := uv run --project skill-generation-validation-tools python3 skill-generation-validation-tools/tests/harness/reporter.py
ANALYZER  := uv run --project skill-generation-validation-tools python3 skill-generation-validation-tools/scripts/analyze-results.py
SKILL     := neo4j-cypher-authoring-skill
CASES_DIR := skill-generation-validation-tools/tests/cases
RESULTS   := skill-generation-validation-tools/tests/results
WORKERS   ?= 5
TIMEOUT   ?= 240
# MODEL: short name passed to --model flag. Accepted: sonnet (default), haiku, opus.
# Override at the command line: make test-companies MODEL=haiku
MODEL     ?= sonnet

TIMESTAMP := $(shell date +%Y%m%d-%H%M%S)

# ── Validation (no DB / no Claude) ─────────────────────────────────────────────

.PHONY: dry-run
dry-run:  ## Validate all YAML test cases (no DB, no Claude)
	$(HARNESS) --cases $(CASES_DIR) --skill $(SKILL) --dry-run

.PHONY: test-extract
test-extract:  ## Run the reference extraction unit tests
	cd skill-generation-validation-tools && uv run python3 scripts/test-extract-references.py

.PHONY: smoke
smoke:  ## Smoke-test validator, reporter, analyzer, and question_validator (no DB needed)
	uv run --project skill-generation-validation-tools python3 skill-generation-validation-tools/tests/harness/validator.py
	uv run --project skill-generation-validation-tools python3 skill-generation-validation-tools/tests/harness/reporter.py
	uv run --project skill-generation-validation-tools python3 skill-generation-validation-tools/scripts/analyze-results.py
	uv run --project skill-generation-validation-tools python3 skill-generation-validation-tools/tests/harness/question_validator.py
	uv run --project skill-generation-validation-tools python3 skill-generation-validation-tools/scripts/audit_questions.py --help > /dev/null

# ── Per-domain harness runs ────────────────────────────────────────────────────

.PHONY: test-companies
test-companies:  ## Run companies domain (demo.neo4jlabs.com, read-only)
	$(HARNESS) \
	  --cases $(CASES_DIR)/companies.yml \
	  --skill $(SKILL) \
	  --report $(RESULTS)/companies-run-$(TIMESTAMP).json \
	  --workers $(WORKERS) \
	  --timeout $(TIMEOUT) \
	  --model $(MODEL) \
	  --verbose
	$(REPORTER) \
	  --input $(RESULTS)/companies-run-$(TIMESTAMP).json \
	  --output $(RESULTS)/companies-run-$(TIMESTAMP).md
	@echo "\n→ Report: $(RESULTS)/companies-run-$(TIMESTAMP).md"

.PHONY: test-recommendations
test-recommendations:  ## Run recommendations domain (demo.neo4jlabs.com, read-only)
	$(HARNESS) \
	  --cases $(CASES_DIR)/recommendations.yml \
	  --skill $(SKILL) \
	  --report $(RESULTS)/recommendations-run-$(TIMESTAMP).json \
	  --workers $(WORKERS) \
	  --timeout $(TIMEOUT) \
	  --model $(MODEL) \
	  --verbose
	$(REPORTER) \
	  --input $(RESULTS)/recommendations-run-$(TIMESTAMP).json \
	  --output $(RESULTS)/recommendations-run-$(TIMESTAMP).md
	@echo "\n→ Report: $(RESULTS)/recommendations-run-$(TIMESTAMP).md"

.PHONY: test-ucfraud
test-ucfraud:  ## Run ucfraud domain (bolt://localhost:7687, writeable, Neo4j 2026.02.1)
	$(HARNESS) \
	  --cases $(CASES_DIR)/ucfraud.yml \
	  --skill $(SKILL) \
	  --report $(RESULTS)/ucfraud-run-$(TIMESTAMP).json \
	  --workers $(WORKERS) \
	  --timeout $(TIMEOUT) \
	  --model $(MODEL) \
	  --verbose
	$(REPORTER) \
	  --input $(RESULTS)/ucfraud-run-$(TIMESTAMP).json \
	  --output $(RESULTS)/ucfraud-run-$(TIMESTAMP).md
	@echo "\n→ Report: $(RESULTS)/ucfraud-run-$(TIMESTAMP).md"

.PHONY: test-stackoverflow
test-stackoverflow:  ## Run stackoverflow domain (demo.neo4jlabs.com, read-only)
	$(HARNESS) \
	  --cases $(CASES_DIR)/stackoverflow.yml \
	  --skill $(SKILL) \
	  --report $(RESULTS)/stackoverflow-run-$(TIMESTAMP).json \
	  --workers $(WORKERS) \
	  --timeout $(TIMEOUT) \
	  --model $(MODEL) \
	  --verbose
	$(REPORTER) \
	  --input $(RESULTS)/stackoverflow-run-$(TIMESTAMP).json \
	  --output $(RESULTS)/stackoverflow-run-$(TIMESTAMP).md
	@echo "\n→ Report: $(RESULTS)/stackoverflow-run-$(TIMESTAMP).md"

.PHONY: test-goodreads
test-goodreads:  ## Run goodreads domain (demo.neo4jlabs.com, read-only)
	$(HARNESS) \
	  --cases $(CASES_DIR)/goodreads.yml \
	  --skill $(SKILL) \
	  --report $(RESULTS)/goodreads-run-$(TIMESTAMP).json \
	  --workers $(WORKERS) \
	  --timeout $(TIMEOUT) \
	  --model $(MODEL) \
	  --verbose
	$(REPORTER) \
	  --input $(RESULTS)/goodreads-run-$(TIMESTAMP).json \
	  --output $(RESULTS)/goodreads-run-$(TIMESTAMP).md
	@echo "\n→ Report: $(RESULTS)/goodreads-run-$(TIMESTAMP).md"

.PHONY: test-northwind
test-northwind:  ## Run northwind domain (demo.neo4jlabs.com, read-only)
	$(HARNESS) \
	  --cases $(CASES_DIR)/northwind.yml \
	  --skill $(SKILL) \
	  --report $(RESULTS)/northwind-run-$(TIMESTAMP).json \
	  --workers $(WORKERS) \
	  --timeout $(TIMEOUT) \
	  --model $(MODEL) \
	  --verbose
	$(REPORTER) \
	  --input $(RESULTS)/northwind-run-$(TIMESTAMP).json \
	  --output $(RESULTS)/northwind-run-$(TIMESTAMP).md
	@echo "\n→ Report: $(RESULTS)/northwind-run-$(TIMESTAMP).md"

.PHONY: test-twitter
test-twitter:  ## Run twitter domain (demo.neo4jlabs.com, read-only)
	$(HARNESS) \
	  --cases $(CASES_DIR)/twitter.yml \
	  --skill $(SKILL) \
	  --report $(RESULTS)/twitter-run-$(TIMESTAMP).json \
	  --workers $(WORKERS) \
	  --timeout $(TIMEOUT) \
	  --model $(MODEL) \
	  --verbose
	$(REPORTER) \
	  --input $(RESULTS)/twitter-run-$(TIMESTAMP).json \
	  --output $(RESULTS)/twitter-run-$(TIMESTAMP).md
	@echo "\n→ Report: $(RESULTS)/twitter-run-$(TIMESTAMP).md"

.PHONY: test-legalcontracts
test-legalcontracts:  ## Run legalcontracts domain (demo.neo4jlabs.com, read-only)
	$(HARNESS) \
	  --cases $(CASES_DIR)/legalcontracts.yml \
	  --skill $(SKILL) \
	  --report $(RESULTS)/legalcontracts-run-$(TIMESTAMP).json \
	  --workers $(WORKERS) \
	  --timeout $(TIMEOUT) \
	  --model $(MODEL) \
	  --verbose
	$(REPORTER) \
	  --input $(RESULTS)/legalcontracts-run-$(TIMESTAMP).json \
	  --output $(RESULTS)/legalcontracts-run-$(TIMESTAMP).md
	@echo "\n→ Report: $(RESULTS)/legalcontracts-run-$(TIMESTAMP).md"

.PHONY: test-retail
test-retail:  ## Run retail domain (demo.neo4jlabs.com, read-only)
	$(HARNESS) \
	  --cases $(CASES_DIR)/retail.yml \
	  --skill $(SKILL) \
	  --report $(RESULTS)/retail-run-$(TIMESTAMP).json \
	  --workers $(WORKERS) \
	  --timeout $(TIMEOUT) \
	  --model $(MODEL) \
	  --verbose
	$(REPORTER) \
	  --input $(RESULTS)/retail-run-$(TIMESTAMP).json \
	  --output $(RESULTS)/retail-run-$(TIMESTAMP).md
	@echo "\n→ Report: $(RESULTS)/retail-run-$(TIMESTAMP).md"

.PHONY: test-ucnetwork
test-ucnetwork:  ## Run ucnetwork domain (demo.neo4jlabs.com, read-only)
	$(HARNESS) \
	  --cases $(CASES_DIR)/ucnetwork.yml \
	  --skill $(SKILL) \
	  --report $(RESULTS)/ucnetwork-run-$(TIMESTAMP).json \
	  --workers $(WORKERS) \
	  --timeout $(TIMEOUT) \
	  --model $(MODEL) \
	  --verbose
	$(REPORTER) \
	  --input $(RESULTS)/ucnetwork-run-$(TIMESTAMP).json \
	  --output $(RESULTS)/ucnetwork-run-$(TIMESTAMP).md
	@echo "\n→ Report: $(RESULTS)/ucnetwork-run-$(TIMESTAMP).md"

.PHONY: test-all
test-all:  ## Run all domains sequentially (companies → recommendations → ucfraud)
	@echo "=== companies ==="
	$(HARNESS) \
	  --cases $(CASES_DIR)/companies.yml \
	  --skill $(SKILL) \
	  --report $(RESULTS)/companies-run-$(TIMESTAMP).json \
	  --workers $(WORKERS) \
	  --timeout $(TIMEOUT) \
	  --model $(MODEL) \
	  --verbose
	@echo "=== recommendations ==="
	$(HARNESS) \
	  --cases $(CASES_DIR)/recommendations.yml \
	  --skill $(SKILL) \
	  --report $(RESULTS)/recommendations-run-$(TIMESTAMP).json \
	  --workers $(WORKERS) \
	  --timeout $(TIMEOUT) \
	  --model $(MODEL) \
	  --verbose
	@echo "=== ucfraud ==="
	$(HARNESS) \
	  --cases $(CASES_DIR)/ucfraud.yml \
	  --skill $(SKILL) \
	  --report $(RESULTS)/ucfraud-run-$(TIMESTAMP).json \
	  --workers $(WORKERS) \
	  --timeout $(TIMEOUT) \
	  --model $(MODEL) \
	  --verbose
	@echo "=== generating reports ==="
	$(REPORTER) \
	  --input $(RESULTS)/companies-run-$(TIMESTAMP).json \
	  --output $(RESULTS)/companies-run-$(TIMESTAMP).md
	$(REPORTER) \
	  --input $(RESULTS)/recommendations-run-$(TIMESTAMP).json \
	  --output $(RESULTS)/recommendations-run-$(TIMESTAMP).md
	$(REPORTER) \
	  --input $(RESULTS)/ucfraud-run-$(TIMESTAMP).json \
	  --output $(RESULTS)/ucfraud-run-$(TIMESTAMP).md
	@echo "\n→ All reports written to $(RESULTS)/"

# ── Difficulty-filtered runs ───────────────────────────────────────────────────

.PHONY: test-basic
test-basic:  ## Run only basic-difficulty cases across all domains
	$(HARNESS) \
	  --cases $(CASES_DIR) \
	  --skill $(SKILL) \
	  --difficulty basic \
	  --report $(RESULTS)/basic-run-$(TIMESTAMP).json \
	  --workers $(WORKERS) \
	  --timeout $(TIMEOUT) \
	  --model $(MODEL) \
	  --verbose

.PHONY: test-expert
test-expert:  ## Run only expert-difficulty cases across all domains
	$(HARNESS) \
	  --cases $(CASES_DIR) \
	  --skill $(SKILL) \
	  --difficulty expert \
	  --report $(RESULTS)/expert-run-$(TIMESTAMP).json \
	  --workers $(WORKERS) \
	  --timeout $(TIMEOUT) \
	  --model $(MODEL) \
	  --verbose

# ── Run individual case IDs ────────────────────────────────────────────────────
# Usage: make run-ids IDS=companies-basic-001,companies-expert-003
# Optional: DOMAIN=companies to scope to a specific domain YAML
# Optional: REPORT=path/to/output.json (default: results/ids-run-<timestamp>.json)

IDS    ?=
REPORT ?= $(RESULTS)/ids-run-$(TIMESTAMP).json

.PHONY: run-ids
run-ids:  ## Re-run specific case IDs (IDS=id1,id2,...); DOMAIN= to scope to one domain
	$(HARNESS) \
	  --cases $(if $(DOMAIN),$(CASES_DIR)/$(DOMAIN).yml,$(CASES_DIR)) \
	  --skill $(SKILL) \
	  --ids $(IDS) \
	  --report $(REPORT) \
	  --workers $(WORKERS) \
	  --timeout $(TIMEOUT) \
	  --model $(MODEL) \
	  --verbose

# ── Analysis ───────────────────────────────────────────────────────────────────

.PHONY: analyze
analyze:  ## Analyze latest results in tests/results/ and write combined report
	$(ANALYZER) \
	  --input $(RESULTS) \
	  --output $(RESULTS)/analysis-$(TIMESTAMP).md
	@echo "\n→ $(RESULTS)/analysis-$(TIMESTAMP).md"

.PHONY: report-latest
report-latest:  ## Re-render Markdown reports from the 3 most recent JSON files
	@for f in $$(ls -t $(RESULTS)/*.json | head -3); do \
	  md="$${f%.json}.md"; \
	  echo "Rendering $$md ..."; \
	  $(REPORTER) --input $$f --output $$md; \
	done

# ── Dataset registration ───────────────────────────────────────────────────────
# Usage: make register-dataset DB_URI=neo4j+s://... DB_USER=companies DB_PASS=companies DB_NAME=companies
# Optional: DOMAIN=companies (default: DB_NAME)  READ_ONLY=--read-only  NO_CLAUDE=--no-claude

DB_URI    ?= bolt://localhost:7687
DB_USER   ?= neo4j
DB_PASS   ?= neo4j
DB_NAME   ?=
DOMAIN    ?= $(DB_NAME)
READ_ONLY ?=
NO_CLAUDE ?=

REGISTER  := uv run --project skill-generation-validation-tools python3 \
               skill-generation-validation-tools/scripts/register_dataset.py

.PHONY: register-dataset
register-dataset:  ## Register a Neo4j DB as a dataset: block in tests/cases/<domain>.yml
	$(REGISTER) \
	  --uri $(DB_URI) \
	  --username $(DB_USER) \
	  --password $(DB_PASS) \
	  --database $(DB_NAME) \
	  --domain $(DOMAIN) \
	  --model $(MODEL) \
	  --output-dir $(CASES_DIR) \
	  $(READ_ONLY) $(NO_CLAUDE)

# ── Question generation ────────────────────────────────────────────────────────
# Usage: make generate-questions DOMAIN=companies COUNT=25 MODEL=haiku
# Optional: DIFFICULTIES=basic,intermediate (default: all five tiers)
# Optional: SKILL=neo4j-cypher-authoring-skill (default)

COUNT         ?= 25
DIFFICULTIES  ?= basic,intermediate,advanced,complex,expert
GENERATE_SKILL ?= $(SKILL)

GENERATE  := uv run --project skill-generation-validation-tools python3 \
               skill-generation-validation-tools/scripts/generate_questions.py

.PHONY: generate-questions
generate-questions:  ## Generate questions for a domain (requires DOMAIN=<name>)
	$(GENERATE) \
	  --domain $(DOMAIN) \
	  --count $(COUNT) \
	  --model $(MODEL) \
	  --difficulties $(DIFFICULTIES) \
	  --cases-dir $(CASES_DIR) \
	  --skill $(GENERATE_SKILL)

.PHONY: onboard-dataset
onboard-dataset: register-dataset generate-questions  ## Register DB schema and generate initial questions (requires DB_URI, DB_USER, DB_PASS, DB_NAME)

# ── Question language audit ────────────────────────────────────────────────────
# Usage: make audit-questions [AUDIT_OUTPUT=path/to/report.md] [CASES_DIR=...]
# Set FAIL_ON_VIOLATIONS=--fail-on-violations to exit non-zero when violations found

AUDIT        := uv run --project skill-generation-validation-tools python3 \
                  skill-generation-validation-tools/scripts/audit_questions.py
AUDIT_OUTPUT ?=
FAIL_ON_VIOLATIONS ?=

.PHONY: audit-questions
audit-questions:  ## Audit all domain YAML questions for business-language compliance
	$(AUDIT) \
	  --cases $(CASES_DIR) \
	  $(if $(AUDIT_OUTPUT),--output $(AUDIT_OUTPUT),) \
	  $(FAIL_ON_VIOLATIONS) \
	  --verbose

# ── Help ───────────────────────────────────────────────────────────────────────

.PHONY: help
help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	  | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-24s %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
