# .github

Wspólne workflowy GitHub Actions i domyślne pliki społeczności dla moich repozytoriów.

[English version](README.md)

- `.github/workflows/php-ci.yml`: audyt Composera, PHP CS Fixer albo PHPCS, PHPStan, PHPUnit z progiem pokrycia, opcjonalnie serwisy PostgreSQL, MongoDB i Redis oraz build frontu
- `.github/workflows/node-ci.yml`: lint, typecheck, testy z progiem pokrycia, build
- `.github/workflows/python-ci.yml`: ruff, mypy, testy z progiem pokrycia
- `.github/workflows/repo-ci.yml`: skan sekretów gitleaks, actionlint, build Dockera bez push (pomijany bez Dockerfile); shellcheck jest preinstalowany na `ubuntu-24.04`, więc actionlint sprawdza też skrypty `run:`
- `actions/coverage-gate` i `actions/push-build-branch`: akcje złożone używane przez workflowy

```yaml
jobs:
  ci:
    uses: Tolemak/.github/.github/workflows/node-ci.yml@v1
    with:
      node-version: "24"
      coverage-min: 80
```

Dodatkowe kontrole są domyślnie wyłączone, by istniejące repozytoria działały bez zmian: `composer-validate` (php-ci), `pip-audit` (python-ci), `audit-omit-dev` i `audit-level` (node-ci). Wszystkie workflowy domyślnie używają przypiętego runnera `ubuntu-24.04`; nowszy obraz wybierasz świadomie przez `runs-on`.

Wejścia i ich domyślne wartości są na początku każdego pliku workflowu. Przypinaj `@v1` albo pełny SHA commita.
`templates/dependabot.yml` to punkt wyjścia dla `.github/dependabot.yml`.

## Wersjonowanie

Wydania to tagi adnotowane `vMAJOR.MINOR.PATCH` na `main`. Workflow `Move major tag` po wypchnięciu takiego tagu przesuwa ruchomy tag `vMAJOR` na najnowsze wydanie danego majora. Aby go naprawić lub uzupełnić, uruchom workflow ręcznie z tagiem wydania, np. `v1.3.1`.
