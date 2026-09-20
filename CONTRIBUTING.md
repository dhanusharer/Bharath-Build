# Contributing Guidelines

Thank you for contributing to the Multimodal Medication Accessibility System for Bharat Builds / First Commit in collaboration with AWS. 

We maintain strict safety, quality, and architectural standards because this software operates in a healthcare accessibility domain where errors can impact human well-being.

---

## Code of Conduct & Safety Philosophy
All contributors must strictly adhere to [ENGINEERING_PRINCIPLES.md](ENGINEERING_PRINCIPLES.md). In particular:
* **The system never guesses**: Do not introduce heuristic fallback mechanisms that invent, fill in, or approximate medical data.
* **Fail closed**: When uncertainty occurs, code must safely refuse and return an explicit structured uncertainty state.
* **Separation of concerns**: Never place business logic or provider SDK invocations inside HTTP route handlers.

---

## Git Workflow & Branching Strategy

### Branch Naming Conventions
Work must occur on feature branches branched from `main`. Direct pushes to `main` are strictly blocked.

* `feat/<issue-id>-<short-description>`: New features conforming to product specifications
* `fix/<issue-id>-<short-description>`: Bug fixes or security patch corrections
* `refactor/<short-description>`: Architectural refactoring without changing behavior
* `test/<short-description>`: Additional test fixtures, benchmark datasets, or unit tests
* `docs/<short-description>`: Documentation, ADRs, or specification updates

### Conventional Commits
All commit messages must follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>(<scope>): <short summary>

[optional body describing technical context, rationale, and safety implications]

[optional footer(s) such as Closes #123]
```

Valid `<type>` values:
* `feat`: A new user-facing or platform capability
* `fix`: A bug or safety defect fix
* `refactor`: Code change that neither fixes a bug nor adds a feature
* `test`: Adding missing tests or correcting existing tests
* `docs`: Documentation only changes
* `chore`: Build tasks, dependency bumps, package configurations

---

## Pull Request Requirements

Before opening a Pull Request (PR), ensure:
1. **Branch is up to date**: Rebased on the latest `main`.
2. **Deterministic Quality Gates Pass**:
   - Ruff linting and formatting pass without warnings: `uv run ruff check . && uv run ruff format --check .`
   - Strict static type checking passes: `uv run mypy --strict .`
   - Complete unit and integration test suite passes: `uv run pytest --cov`
   - For web/frontend: ESLint and TypeScript checks pass: `npm run lint && npm run typecheck`
3. **Safety Checklist Completed**: If your PR touches extraction, normalization, validation, or voice intent interpretation, you must provide regression tests verifying failure-case and uncertainty handling.
4. **Documentation**: Any API contract changes, domain model updates, or configuration additions must be documented in `docs/`. Major architectural decisions require an ADR.

---

## Local Development Setup Standards (Phase 1 Preview)

* **Python Runtime**: Python 3.12 managed via `uv`
* **Node.js Runtime**: Node.js 20+ LTS
* **Formatting & Linting**: Ruff for Python; Prettier & ESLint for TypeScript
* **Environment Variables**: Copy `.env.example` to `.env`. Never commit real secrets or API keys.

---

## Reporting Vulnerabilities or Safety Risks
If you identify a safety-critical flaw (e.g., a regex pattern that incorrectly normalizes an ambiguous medication schedule, or a prompt vulnerability permitting model hallucinations), immediately open a high-priority issue tagged with `safety-critical` and follow the escalation protocol defined in `docs/04-safety/safety-specification.md`.
