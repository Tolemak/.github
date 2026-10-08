# .github

Reusable GitHub Actions workflows and default community files for my repositories.

[Polska wersja](README.pl.md)

- `.github/workflows/php-ci.yml`: Composer audit, PHP CS Fixer or PHPCS, PHPStan, PHPUnit with a coverage gate, optional PostgreSQL, MongoDB and Redis services and front-end build
- `.github/workflows/node-ci.yml`: lint, typecheck, tests with a coverage gate, build
- `.github/workflows/python-ci.yml`: ruff, mypy, tests with a coverage gate
- `.github/workflows/repo-ci.yml`: gitleaks secret scan, actionlint, Docker build without push (skipped when there is no Dockerfile); shellcheck is preinstalled on `ubuntu-24.04`, so actionlint also checks `run:` scripts
- `actions/coverage-gate` and `actions/push-build-branch`: composite actions used by the workflows

```yaml
jobs:
  ci:
    uses: Tolemak/.github/.github/workflows/node-ci.yml@v1
    with:
      node-version: "24"
      coverage-min: 80
```

Optional checks are off by default so existing callers keep working: `composer-validate` (php-ci), `pip-audit` (python-ci), `audit-omit-dev` and `audit-level` (node-ci). All workflows default to the pinned `ubuntu-24.04` runner; override `runs-on` to move to a newer image deliberately.

Inputs and their defaults are listed at the top of each workflow file. Pin `@v1` or a full commit SHA.
`templates/dependabot.yml` is a starting point for `.github/dependabot.yml`.

## Versioning

Releases are annotated tags `vMAJOR.MINOR.PATCH` on `main`. The `Move major tag` workflow points the moving `vMAJOR` tag at the newest release of that major when such a tag is pushed. To repair or backfill it, run the workflow manually with the release tag, for example `v1.3.1`.
