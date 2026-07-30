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
- Publish coverage XML as a CI artifact for inspection.

Acceptance criteria:

- `mypy src/locallore` passes without blanket module-level ignores.
- The full test suite meets or exceeds the measured baseline.
- New production code cannot reduce coverage below the committed threshold.
- `scripts/check.sh` runs lint, formatting, typing, coverage, and ShellCheck.

## PR 3: Make releases reproducible

Goal: make built releases consistent and independently verifiable.

Scope:

- Add a tested version-bump command for Python, Compose, shell, plugin manifest,
  marketplace, and release metadata.
- Build both wheel and source distribution in CI.
- Install the wheel into a clean environment and verify imports, CLI startup,
  packaged SQL resources, and database creation.
- Document the release procedure.

Acceptance criteria:

- One command validates and updates every committed version location.
- Tests catch every version mismatch.
- Built artifacts work without access to the repository checkout.

## PR 4: Harden the supply chain and release path

Goal: prevent vulnerable dependencies and unvalidated releases from reaching
users.

Scope:

- Configure Dependabot for uv, Docker, and GitHub Actions.
- Add pull-request dependency review.
- Add CodeQL Python analysis.
- Pin third-party GitHub Actions to reviewed full commit SHAs.
- Pin container build inputs by digest where update automation can maintain
  them.
- Require the complete quality, artifact, and offline-image gates before a tag
  can create a GitHub release.
- Add concise contributor, security-reporting, and architecture documentation.

Acceptance criteria:

- Dependency updates arrive as isolated, reviewable pull requests.
- Pull requests that introduce known vulnerable dependencies fail.
- Code scanning covers the Python source tree.
- Release creation cannot bypass the same checks required for pull requests.
- All workflow dependencies are immutable and updateable by automation.

## Delivery order

The pull requests are intentionally dependency-ordered:

1. Quality baseline
2. Typing and coverage
3. Reproducible releases
4. Supply-chain and release hardening

Later pull requests should be rebased on the merged predecessor so each diff
contains only its stated scope.
