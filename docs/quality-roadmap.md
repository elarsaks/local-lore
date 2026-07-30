# Quality Roadmap

This roadmap raises LocalLore's engineering baseline in four reviewable pull
requests. Each pull request leaves the repository green and provides the
foundation required by the next one.

## PR 1: Establish the quality baseline

Goal: make the repository's existing quality expectations explicit,
reproducible, and required in CI.

Scope:

- Add Ruff as a locked development dependency.
- Configure an explicit Python 3.12 lint ruleset and Ruff formatting.
- Replace selective Python test jobs with one full-suite quality job.
- Treat test warnings as errors and migrate Starlette's test client to HTTPX2.
- Add ShellCheck to CI and resolve or document all current shell findings.
- Add `scripts/check.sh` as the canonical local quality command.

Acceptance criteria:

- `./scripts/check.sh` passes from a locked development environment.
- CI runs all Python tests, not a hand-picked subset.
- CI validates the plugin manifests and Docker Compose configuration.
- The offline image test remains a separate integration boundary.

## PR 2: Add typing and coverage gates

Goal: detect invalid data flow before runtime and make test gaps measurable.

Scope:

- Add mypy and pytest-cov as locked development dependencies.
- Type-check `src/locallore` with a strict, explicit configuration.
- Add missing production annotations and narrow overly broad object types.
- Record the initial coverage baseline and enforce it in CI.
- Add targeted tests for runtime failure/retry, authentication, corrupt JSONL,
  transaction rollback, and embedding failures where the baseline exposes gaps.

Acceptance criteria:

- `mypy src/locallore` passes without blanket module-level ignores.
- The full test suite meets or exceeds the measured baseline.
- New production code cannot reduce coverage below the committed threshold.
- `scripts/check.sh` runs lint, formatting, typing, coverage, and ShellCheck.

## PR 3: Make versioning reproducible

Goal: keep committed release metadata consistent.

Scope:

- Add a tested version-bump command for Python, Compose, shell, plugin manifest,
  marketplace, and release metadata.
- Document the release procedure.

Acceptance criteria:

- One command validates and updates every committed version location.
- Tests catch every version mismatch.

## PR 4: Freeze and validate release inputs

Goal: leave the finished repository reproducible without ongoing maintenance.

Scope:

- Pin direct Python, build, toolchain, workflow, and container inputs.
- Require the quality and offline-image gates before a tag can create a GitHub
  release.
- Document that the repository is a frozen, unmaintained snapshot.

Acceptance criteria:

- Release creation cannot bypass the same checks required for pull requests.
- Direct dependencies and build inputs cannot move without a committed change.
- The maintenance status is clear to prospective users.

## Delivery order

The pull requests are intentionally dependency-ordered:

1. Quality baseline
2. Typing and coverage
3. Reproducible versioning
4. Frozen release inputs

PR 4 completes this roadmap. Any future dependency or release change should be
an explicit decision to resume maintenance.
