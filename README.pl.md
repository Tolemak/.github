# .github

Wspólne workflowy GitHub Actions, akcje złożone (composite) i domyślne pliki społeczności dla repozytoriów
konta [Tolemak](https://github.com/Tolemak). Repozytorium zastępuje swoje CI kilkoma linijkami, które
wywołują workflow z tego repozytorium.

[English version](README.md)

| Co | Ścieżka | Do czego |
| --- | --- | --- |
| PHP CI | [`.github/workflows/php-ci.yml`](.github/workflows/php-ci.yml) | Composer, audit, PHP CS Fixer / PHPCS, PHPStan, PHPUnit + pcov, próg pokrycia, opcjonalnie PostgreSQL i build front-endu |
| Node CI | [`.github/workflows/node-ci.yml`](.github/workflows/node-ci.yml) | npm ci, lint, typecheck, testy, build, opcjonalnie próg pokrycia i upload artefaktu |
| Python CI | [`.github/workflows/python-ci.yml`](.github/workflows/python-ci.yml) | ruff check + format, mypy (jeśli skonfigurowany), testy z coverage, próg pokrycia |
| Coverage gate | [`actions/coverage-gate`](actions/coverage-gate) | Kończy się błędem poniżej progu pokrycia linii; czyta Clover lub Cobertura XML (Python, bez PHP) |
| Push build branch | [`actions/push-build-branch`](actions/push-build-branch) | Publikuje katalog na gałąź jako jeden commit bez rodzica |
| Szablon Dependabota | [`templates/dependabot.yml`](templates/dependabot.yml) | Comiesięczne, grupowane aktualizacje; skopiuj do `.github/dependabot.yml` |

## Wersjonowanie

Odwołuj się do tagu (`@v1`) albo — najbezpieczniej — do pełnego SHA commita z tagiem w komentarzu.
`v1` przesuwa się przy zmianach zgodnych wstecz; zmiany łamiące dostają `v2`. Każdy workflow pobiera to
repozytorium dokładnie w swoim commicie, żeby uruchomić akcje złożone, więc workflow i akcje zawsze do siebie pasują.

## PHP / Symfony

```yaml
jobs:
  ci:
    uses: Tolemak/.github/.github/workflows/php-ci.yml@v1
    with: { php-version: "8.4", extensions: "intl, pdo_pgsql", cs-tool: phpcs }
```

Kolejność: `composer install` → `composer audit` → front-end (opcjonalnie) → `pre-test-command` → kontrola
stylu → `phpstan analyse` → `phpunit --coverage-clover var/coverage/clover.xml` → próg pokrycia.

| Input | Domyślnie | Uwagi |
| --- | --- | --- |
| `php-version` | `8.4` | Kilka wersji — macierz po stronie wywołującego (przykład niżej). |
| `extensions` | `""` | Przekazywane do `shivammathur/setup-php`; pcov włączany automatycznie. |
| `working-directory` | `.` | Katalog z `composer.json`. |
| `cs-tool` | `php-cs-fixer` | `php-cs-fixer` (`check --diff`), `phpcs` albo `none`. |
| `phpstan` / `phpstan-level` | `true` / `""` | Poziom z `phpstan.neon[.dist]`, chyba że podany. |
| `composer-audit` | `true` | |
| `pre-test-command` | `""` | Po instalacji zależności, przed analizą i testami — np. `bin/console lexik:jwt:generate-keypair`. |
| `phpunit-command` | `vendor/bin/phpunit` | Opcje pokrycia są doklejane. |
| `coverage-file` / `coverage-min` | `var/coverage/clover.xml` / `80` | `coverage-min: 0` wyłącza pokrycie i próg. |
| `postgres-version` | `""` | Uruchamia `postgres:<wersja>` i eksportuje `DATABASE_URL=postgresql://app:app@127.0.0.1:5432/app?serverVersion=<wersja>&charset=utf8`; dodaje `pdo_pgsql`. Środowisko testowe Symfony dokleja `_test`, więc utwórz bazę w `pre-test-command` (`bin/console doctrine:database:create --env=test`). |
| `node-version` | `""` | Buduje też front-end: `npm ci`, potem każdy skrypt z `node-scripts` (domyślnie `typecheck test build`) w `node-working-directory`. |
| `runs-on` | `ubuntu-latest` | |

Kontenerów usług nie da się przekazać do reusable workflow, dlatego baza pochodzi z `postgres-version`.

<details><summary>Przykład z macierzą, PostgreSQL i front-endem</summary>

```yaml
name: CI
on: [push, pull_request]
jobs:
  php:
    strategy:
      matrix:
        php: ["8.3", "8.4"]
    uses: Tolemak/.github/.github/workflows/php-ci.yml@v1
    with:
      php-version: ${{ matrix.php }}
      extensions: intl, sodium
      cs-tool: php-cs-fixer
      postgres-version: "17"
      pre-test-command: |
        bin/console doctrine:database:create --env=test --if-not-exists
        bin/console doctrine:migrations:migrate --env=test --no-interaction
      node-version: "22"
```

</details>

## Node / TypeScript

```yaml
jobs:
  ci:
    uses: Tolemak/.github/.github/workflows/node-ci.yml@v1
    with: { node-version: "24", lint-command: "npx oxlint --deny-warnings" }
```

| Input | Domyślnie | Uwagi |
| --- | --- | --- |
| `node-version` | `22` | |
| `working-directory` | `.` | Dla drugiego pakietu (np. `server/`) wywołaj workflow jeszcze raz. |
| `install-command` | `npm ci --no-audit --no-fund` | |
| `lint-command` | `npm run lint --if-present` | np. `npx eslint . --max-warnings 0`. Pusty napis pomija krok. |
| `typecheck-command` | `npm run typecheck --if-present` | Pusty napis pomija krok. |
| `test-command` | `npm run test --if-present` | Progi pokrycia trzymaj w `vitest.config`. Pusty napis pomija krok. |
| `build-command` | `npm run build --if-present` | Pusty napis pomija krok. |
| `coverage-file` / `coverage-min` | `""` / `80` | Opcjonalny dodatkowy próg na raporcie Clover/Cobertura, np. `coverage/cobertura-coverage.xml`. |
| `artifact-name` / `artifact-path` | `""` / `dist` | Wysyła wynik builda jako artefakt, gdy podano nazwę. |

<details><summary>Dwa pakiety i gałąź <code>build</code>, którą pobiera serwer</summary>

```yaml
name: CI
on: [push, pull_request]
jobs:
  web:
    uses: Tolemak/.github/.github/workflows/node-ci.yml@v1
    with: { artifact-name: dist }
  server:
    uses: Tolemak/.github/.github/workflows/node-ci.yml@v1
    with: { working-directory: server }
  publish:
    needs: [web, server]
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/download-artifact@3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c # v8.0.1
        with: { name: dist, path: dist }
      - uses: Tolemak/.github/actions/push-build-branch@v1
        with: { directory: dist, branch: build }
```

</details>

## Python

```yaml
jobs:
  ci:
    uses: Tolemak/.github/.github/workflows/python-ci.yml@v1
    with: { python-version: "3.11", coverage-min: 80 }
```

Instaluje `requirements.txt` i `requirements-dev.txt`, jeśli istnieją (albo uruchamia `install-command`),
potem `ruff check`, `ruff format --check`, `mypy`, gdy istnieje konfiguracja (`mypy.ini`, `.mypy.ini`,
`[tool.mypy]`, `[mypy]` w `setup.cfg`), oraz `coverage run -m unittest discover` (z `tests/`, jeśli jest).
Dla pytesta: `test-command: python -m coverage run -m pytest`. Wersje narzędzi przypinają inputy
`ruff-version`, `mypy-version` i `coverage-version`.

## Akcje złożone

```yaml
- uses: Tolemak/.github/actions/coverage-gate@v1
  with: { file: var/coverage/clover.xml, min: 80 }   # format: auto | clover | cobertura
```

Pokrycie linii to `coveredstatements / statements` z metryk projektu w Cloverze albo
`lines-covered / lines-valid` (w razie braku `line-rate`) w Coberturze. Akcja zapisuje podsumowanie joba
i wystawia `outputs.percent`. Zastępuje skrypty `bin/check-coverage.php` w poszczególnych repozytoriach.

```yaml
- uses: Tolemak/.github/actions/push-build-branch@v1   # job potrzebuje permissions: contents: write
  with: { directory: dist, branch: build, message: "Build ${{ github.sha }}" }
```

Gałąź zostaje zastąpiona jednym commitem bez rodzica, którego autorem jest aktor workflow (committer
`github-actions[bot]`). Wypchnięcie na domyślną gałąź repozytorium jest odrzucane.

## Domyślne pliki społeczności

`SECURITY.md` i formularz zgłoszenia błędu w `.github/ISSUE_TEMPLATE/` obowiązują w każdym repozytorium
konta, które nie ma własnego pliku tego typu (GitHub robi to tylko, gdy to repozytorium jest publiczne).

## Dopóki repozytorium jest prywatne

Prywatne reusable workflows można wywoływać dopiero, gdy **Settings → Actions → General → Access**
zezwala repozytoriom konta. Workflowy pobierają też to repozytorium, żeby uruchomić próg pokrycia;
`GITHUB_TOKEN` wywołującego nie odczyta prywatnego repozytorium, więc przekaż fine-grained token z
prawem odczytu zawartości tego repozytorium:

```yaml
    secrets:
      shared-ci-token: ${{ secrets.SHARED_CI_TOKEN }}
```

Po upublicznieniu repozytorium nic więcej nie jest potrzebne.

## Rozwój

`.github/workflows/self-test.yml` uruchamia [actionlint](https://github.com/rhysd/actionlint) (z shellcheckiem),
testy jednostkowe coverage-gate i wywołuje każdy reusable workflow na projektach testowych w
[`tests/fixtures`](tests/fixtures). Sprawdza też, że próg zawodzi poniżej wartości minimalnej i że
`push-build-branch` tworzy pojedynczy commit bez rodzica.

```sh
python3 -m unittest discover -s actions/coverage-gate   # testy progu pokrycia
actionlint                                              # lint workflowów
```

Akcje zewnętrzne są przypięte do pełnych SHA commitów z wersją w komentarzu; Dependabot je aktualizuje.

## Licencja

[MIT](LICENSE)
