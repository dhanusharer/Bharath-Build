# Git Workflow & Source Control Standards

**Document Version**: 1.0.0 (Phase 0 Freeze)  
**Repository Branching Strategy**: Trunk-Based Development with Short-Lived Feature Branches  

---

## 1. Branch Naming Conventions

Direct pushes to `main` are permanently restricted via repository branch protection rules. All contributions must originate from topic branches:

| Branch Prefix | Usage & Trigger | Example |
| :--- | :--- | :--- |
| `feat/` | New functional capability or user-facing feature | `feat/FR-005-bedrock-extraction-service` |
| `fix/` | Bug correction or safety-gate defect patch | `fix/VEC-002-smudged-dosage-fail-closed` |
| `refactor/` | Code restructuring without altering external behavior | `refactor/tts-provider-abstraction-port` |
| `test/` | Adding test fixtures, benchmark images, or unit tests | `test/add-kannada-synthetic-audio-suite` |
| `docs/` | Documentation, PRD updates, or ADR additions | `docs/ADR-010-regional-kannada-tts-vendor` |
| `chore/` | CI/CD pipeline, dependency bumps, tooling configuration | `chore/upgrade-pydantic-v2-5` |

---

## 2. Conventional Commit Standards

Every commit message must strictly follow the Conventional Commits specification:

```
<type>(<optional-scope>): <imperative short summary>

[optional detailed body explaining context, technical rationale, and safety impact]

[optional footer references, e.g., Closes #42]
```

### Allowed Types
* `feat`: A new user-facing or platform capability.
* `fix`: A bug fix or safety-gate regression correction.
* `refactor`: Code change that neither fixes a bug nor adds a feature.
* `test`: Adding missing tests, benchmark fixtures, or correcting existing tests.
* `docs`: Documentation updates only.
* `chore`: Build scripts, CI workflow, or dependency upgrades.

---

## 3. Pull Request (PR) & Quality Gates

### Mandatory PR Verification Checklist
Before any PR can be merged into `main`, the automated CI pipeline must verify:
1. **Linting & Code Formatting**: `uv run ruff check .` and `uv run ruff format --check .` exit with 0 errors.
2. **Static Typing**: `uv run mypy --strict .` passes with zero type warnings.
3. **Unit & Contract Tests**: Complete test suite passes via `uv run pytest --cov=core --cov-fail-under=85`.
4. **Safety Regression Suite**: Tests in `tests/safety/` pass with 100% adherence (zero guessed dosages).
5. **No Merge Conflicts**: Branch is cleanly rebased against latest `main`.
6. **Code Review**: At least one approving review from a code owner / architect.
