# .github

Wspólne workflowy GitHub Actions i domyślne pliki społeczności dla moich repozytoriów.

[English version](README.md)

- `.github/workflows/php-ci.yml`: audyt Composera, PHP CS Fixer albo PHPCS, PHPStan, PHPUnit z progiem pokrycia, opcjonalnie PostgreSQL i build frontu
- `.github/workflows/node-ci.yml`: lint, typecheck, testy z progiem pokrycia, build
- `.github/workflows/python-ci.yml`: ruff, mypy, testy z progiem pokrycia
- `actions/coverage-gate` i `actions/push-build-branch`: akcje złożone używane przez workflowy

```yaml
jobs:
  ci:
    uses: Tolemak/.github/.github/workflows/node-ci.yml@v1
    with:
      node-version: "24"
      coverage-min: 80
```

Wejścia i ich domyślne wartości są na początku każdego pliku workflowu. Przypinaj `@v1` albo pełny SHA commita.
`templates/dependabot.yml` to punkt wyjścia dla `.github/dependabot.yml`.
