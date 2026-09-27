# .github

Reusable GitHub Actions workflows and default community files for my repositories.

[Polska wersja](README.pl.md)

- `.github/workflows/php-ci.yml`: Composer audit, PHP CS Fixer or PHPCS, PHPStan, PHPUnit with a coverage gate, optional PostgreSQL and front-end build
- `.github/workflows/node-ci.yml`: lint, typecheck, tests with a coverage gate, build
- `.github/workflows/python-ci.yml`: ruff, mypy, tests with a coverage gate
- `actions/coverage-gate` and `actions/push-build-branch`: composite actions used by the workflows

```yaml
jobs:
  ci:
    uses: Tolemak/.github/.github/workflows/node-ci.yml@v1
    with:
      node-version: "24"
      coverage-min: 80
```

Inputs and their defaults are listed at the top of each workflow file. Pin `@v1` or a full commit SHA.
`templates/dependabot.yml` is a starting point for `.github/dependabot.yml`.
