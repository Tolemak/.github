# .github

Reusable GitHub Actions workflows, composite actions and default community health files for
[Tolemak](https://github.com/Tolemak)'s repositories. A repository replaces its CI with a few lines
that call a workflow from here.

[Polska wersja](README.pl.md)

| What | Path | Purpose |
| --- | --- | --- |
| PHP CI | [`.github/workflows/php-ci.yml`](.github/workflows/php-ci.yml) | Composer, audit, PHP CS Fixer / PHPCS, PHPStan, PHPUnit + pcov, coverage gate, optional PostgreSQL and front-end build |
| Node CI | [`.github/workflows/node-ci.yml`](.github/workflows/node-ci.yml) | npm ci, lint, typecheck, test, build, optional coverage gate and artifact upload |
| Python CI | [`.github/workflows/python-ci.yml`](.github/workflows/python-ci.yml) | ruff check + format, mypy (when configured), tests under coverage, coverage gate |
| Coverage gate | [`actions/coverage-gate`](actions/coverage-gate) | Fails below a line-coverage percentage, reading Clover or Cobertura XML (Python, no PHP needed) |
| Push build branch | [`actions/push-build-branch`](actions/push-build-branch) | Publishes a directory to a branch as one parentless commit |
| Dependabot template | [`templates/dependabot.yml`](templates/dependabot.yml) | Monthly grouped updates; copy to `.github/dependabot.yml` |

## Versioning

Reference a release tag (`@v1`) or, for maximum supply-chain safety, a full commit SHA with the tag in a comment.
`v1` moves forward with backwards-compatible changes; breaking changes get `v2`. Each workflow checks out
this repository at its own commit to run the composite actions, so workflow and actions always match.

## PHP / Symfony

```yaml
jobs:
  ci:
    uses: Tolemak/.github/.github/workflows/php-ci.yml@v1
    with: { php-version: "8.4", extensions: "intl, pdo_pgsql", cs-tool: phpcs }
```

Pipeline: `composer install` → `composer audit` → front-end (optional) → `pre-test-command` → CS check →
`phpstan analyse` → `phpunit --coverage-clover var/coverage/clover.xml` → coverage gate.

| Input | Default | Notes |
| --- | --- | --- |
| `php-version` | `8.4` | Use a caller matrix for several versions (example below). |
| `extensions` | `""` | Passed to `shivammathur/setup-php`; pcov is enabled automatically. |
| `working-directory` | `.` | Directory with `composer.json`. |
| `cs-tool` | `php-cs-fixer` | `php-cs-fixer` (`check --diff`), `phpcs`, or `none`. |
| `phpstan` / `phpstan-level` | `true` / `""` | Level comes from `phpstan.neon[.dist]` unless set. |
| `composer-audit` | `true` | |
| `pre-test-command` | `""` | Runs after installs, before static analysis and tests — e.g. `bin/console lexik:jwt:generate-keypair`. |
| `phpunit-command` | `vendor/bin/phpunit` | Coverage options are appended. |
| `coverage-file` / `coverage-min` | `var/coverage/clover.xml` / `80` | `coverage-min: 0` disables coverage and the gate. |
| `postgres-version` | `""` | Starts `postgres:<version>` and exports `DATABASE_URL=postgresql://app:app@127.0.0.1:5432/app?serverVersion=<version>&charset=utf8`; adds `pdo_pgsql`. Symfony's test env appends `_test`, so create it in `pre-test-command` (`bin/console doctrine:database:create --env=test`). |
| `node-version` | `""` | Also builds a front-end: `npm ci`, then each of `node-scripts` (default `typecheck test build`) in `node-working-directory`. |
| `runs-on` | `ubuntu-latest` | |

Service containers cannot be passed into a reusable workflow, so the database comes from `postgres-version`.

<details><summary>Matrix, PostgreSQL and front-end example</summary>

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

| Input | Default | Notes |
| --- | --- | --- |
| `node-version` | `22` | |
| `working-directory` | `.` | Call the workflow again for a second package (e.g. `server/`). |
| `install-command` | `npm ci --no-audit --no-fund` | |
| `lint-command` | `npm run lint --if-present` | e.g. `npx eslint . --max-warnings 0`. Empty string skips. |
| `typecheck-command` | `npm run typecheck --if-present` | Empty string skips. |
| `test-command` | `npm run test --if-present` | Keep coverage thresholds in `vitest.config`. Empty string skips. |
| `build-command` | `npm run build --if-present` | Empty string skips. |
| `coverage-file` / `coverage-min` | `""` / `80` | Optional extra gate on a Clover/Cobertura report, e.g. `coverage/cobertura-coverage.xml`. |
| `artifact-name` / `artifact-path` | `""` / `dist` | Uploads the build output when a name is given. |

<details><summary>Two packages and a <code>build</code> branch for the server to pull</summary>

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

Installs `requirements.txt` and `requirements-dev.txt` when present (or runs `install-command`), then
`ruff check`, `ruff format --check`, `mypy` when a config exists (`mypy.ini`, `.mypy.ini`, `[tool.mypy]`,
`[mypy]` in `setup.cfg`), and `coverage run -m unittest discover` (from `tests/` when it exists). Use
`test-command: python -m coverage run -m pytest` for pytest. Tool versions are pinned by the
`ruff-version`, `mypy-version` and `coverage-version` inputs.

## Composite actions

```yaml
- uses: Tolemak/.github/actions/coverage-gate@v1
  with: { file: var/coverage/clover.xml, min: 80 }   # format: auto | clover | cobertura
```

Line coverage is `coveredstatements / statements` of Clover's project-level metrics, or
`lines-covered / lines-valid` (else `line-rate`) for Cobertura. The action writes a job summary and exposes
`outputs.percent`. It replaces per-repository `bin/check-coverage.php` scripts.

```yaml
- uses: Tolemak/.github/actions/push-build-branch@v1   # job needs permissions: contents: write
  with: { directory: dist, branch: build, message: "Build ${{ github.sha }}" }
```

The branch is replaced by a single parentless commit authored by the workflow actor (committer
`github-actions[bot]`). Pushing to the repository's default branch is refused.

## Default community health files

`SECURITY.md` and the bug-report issue form in `.github/ISSUE_TEMPLATE/` apply to every repository of the
account that has no file of its own (GitHub only does this while this repository is public).

## While this repository is private

Private reusable workflows are callable only after **Settings → Actions → General → Access** allows
repositories of the account. The workflows also check out this repository to run the coverage gate; a
caller's `GITHUB_TOKEN` cannot read a private repository, so pass a fine-grained token with read access
to this repository's contents:

```yaml
    secrets:
      shared-ci-token: ${{ secrets.SHARED_CI_TOKEN }}
```

Once the repository is public, nothing extra is needed.

## Development

`.github/workflows/self-test.yml` runs [actionlint](https://github.com/rhysd/actionlint) (with shellcheck),
the coverage-gate unit tests, and calls every reusable workflow against the fixture projects in
[`tests/fixtures`](tests/fixtures). It also proves the gate fails below the threshold and that
`push-build-branch` produces a single parentless commit.

```sh
python3 -m unittest discover -s actions/coverage-gate   # gate unit tests
actionlint                                              # workflow lint
```

Third-party actions are pinned to full commit SHAs with the version in a trailing comment; Dependabot
keeps them up to date.

## License

[MIT](LICENSE)
