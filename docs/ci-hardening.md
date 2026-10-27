# CI hardening

Review of the reusable workflows and composite actions in this change. Every change is meant to be safe for existing `@v1` callers: no input, default, job id, job name, step output or action output was added, removed or renamed.

## Inventory

| File | Kind | Callers depend on |
| --- | --- | --- |
| `.github/workflows/python-ci.yml` | reusable (`workflow_call`) | job `python` named `Python <python-version>`; 13 inputs; secret `shared-ci-token` |
| `.github/workflows/node-ci.yml` | reusable | job `node` named `Node <node-version> (<working-directory>)`; 17 inputs; secret `shared-ci-token` |
| `.github/workflows/php-ci.yml` | reusable | job `php` named `PHP <php-version>`; 20 inputs; secret `shared-ci-token` |
| `.github/workflows/repo-ci.yml` | reusable | jobs `secrets` (`gitleaks`), `actionlint`, `docker` (`Docker build`); 6 inputs |
| `.github/workflows/self-test.yml` | this repository only | runs actionlint, coverage-gate tests and every reusable workflow against `tests/fixtures` on push, pull request and dispatch |
| `.github/workflows/move-major-tag.yml` | this repository only | moves `vMAJOR` to the newest `vMAJOR.MINOR.PATCH` tag on `main` |
| `actions/coverage-gate` | composite | inputs `file`, `min`, `format`; output `percent` |
| `actions/push-build-branch` | composite | inputs `directory`, `branch`, `message`, `repository`, `token`; output `sha` |

None of the reusable workflows declares `outputs:`, so callers can only depend on job results and names.

## Already in place before this branch

- Every third-party action is pinned to a full commit SHA with a trailing version marker. All nine pins were checked with `git ls-remote` against their tags and match.
- `actionlint` and `gitleaks` binaries are downloaded with a pinned version and SHA-256; both checksums were re-verified.
- Top-level and job-level `permissions: contents: read` everywhere, except `move-major-tag` (`contents: write`, needed to push the tag) and the self-test `push-build-branch` job (`contents: write`, needed for the branch it creates and deletes).
- `persist-credentials: false` on every checkout except `move-major-tag`, which pushes with the persisted credentials.
- `timeout-minutes` on every job.
- `concurrency` with `cancel-in-progress` for pull requests in `self-test.yml`; a non-cancelling group in `move-major-tag.yml`.
- Composer (keyed on `composer.lock`), npm (keyed on `package-lock.json` through `setup-node`), pip and Docker layer (`type=gha`) caches.
- A self-test workflow that runs actionlint, with shellcheck on `run:` blocks, on every push and pull request.

## Changes

### 1. Command inputs are passed through `env` instead of being expanded into `run:`

`node-ci.yml`: `install-command`, `lint-command`, `typecheck-command`, `test-command`, `build-command`.
`php-ci.yml`: `pre-test-command`.

Before, each step was `run: ${{ inputs.X }}`, so the text was pasted into the generated script before the shell saw it. A caller that built such an input from untrusted data (for example a pull request title or branch name) handed that data straight to the runner as code. Now each step sets `X_COMMAND: ${{ inputs.X }}` in `env` and runs `eval "$X_COMMAND"`, which matches what `python-ci.yml` and the PHPUnit step already did and removes all template-injection findings from zizmor.

Why it is backward compatible: these inputs are shell commands by contract, so they still run as shell code. `eval` runs them in the same step shell (`bash -e`, no `pipefail`, same working directory, same environment, same `$GITHUB_ENV` / `$GITHUB_OUTPUT`), so failures, exit codes, pipes, multi-line commands, here-documents and `cd` behave exactly as before. This was checked by running the same commands both ways and comparing output and exit status. Expressions inside a caller's `with:` are evaluated by the caller before the value reaches the workflow, so they are unaffected.

### 2. Wider pip cache key in `python-ci.yml`

The key now also hashes `requirements/*.txt`, `constraints*.txt`, `setup.cfg`, `setup.py`, `uv.lock`, `poetry.lock`, `pdm.lock` and `Pipfile.lock` in `working-directory`, next to the existing `requirements*.txt` and `pyproject.toml`.

Why: projects that pin through a lockfile or a `requirements/` directory reused a stale cache after dependency bumps and downloaded the difference on every run.

Why it is backward compatible: only the cache key changes. The `restore-keys` prefix is unchanged, so the first run after the change restores the previous cache by prefix and then saves a new one. No input or behaviour changes.

### 3. Dependabot cooldown

`.github/dependabot.yml` and `templates/dependabot.yml` set `cooldown: default-days: 7` for the `github-actions` ecosystem.

Why: a freshly published action release is the usual window for a compromised tag; waiting a week before Dependabot proposes it lets the ecosystem notice first. Security updates are not delayed by cooldown.

Why it is backward compatible: it only affects when Dependabot opens update pull requests, in this repository and in repositories that copy the template.

### 4. This document

`docs/ci-hardening.md`.

## Checked and intentionally left as is

- `concurrency` inside the reusable workflows. A called workflow cannot see the caller's matrix, and the same workflow is often called several times in one run (for example `node-ci` for `.` and `server`), so any group defined inside it either cancels sibling jobs or duplicates the caller's own group, which GitHub treats as a deadlock and cancels. Callers should keep setting `concurrency` in their own workflow, for example:

  ```yaml
  concurrency:
    group: ${{ github.workflow }}-${{ github.ref }}
    cancel-in-progress: ${{ github.event_name == 'pull_request' }}
  ```

- `move-major-tag.yml` keeps the persisted checkout credentials (zizmor `artipacked`). The job uploads no artifacts and needs the credentials for `git push --force origin refs/tags/vN`. Switching it to the header-based push used by `push-build-branch` is possible, but it is the release path and was left untouched in this round.
- `shivammathur/setup-php` is marked `# 2.37.2` rather than `# v2.37.2` because that project's tags have no `v` prefix; the marker must match the tag for Dependabot to keep it in sync.
- `actions/setup-node` `cache: npm` still requires `package-lock.json` in `working-directory`; callers rely on it today, so it was not made conditional.
- The `job.workflow_repository` / `job.workflow_sha` ignore rule in `.github/actionlint.yaml` is still needed with actionlint 1.7.12.
- zizmor `self-repository` hints (`$/...` instead of `./...`) only concern `self-test.yml` and are style suggestions.

## Deferred to v2 (breaking or behaviour-changing)

1. Digest-pinned service images in `php-ci.yml`. `postgres-version`, `mongodb-version` and `redis-version` are free-form tags today; pinning by digest needs a new input contract (for example an `image@sha256:` value or a maintained version-to-digest map).
2. `defaults.run.shell: bash` (adds `pipefail`) in the reusable workflows. Caller commands with pipes whose left side fails would start failing.
3. `npm ci --ignore-scripts` by default in `node-ci.yml` and in the `php-ci.yml` front-end step. Safer against malicious lifecycle scripts, but packages that build native code on install would break.
4. Per-workflow `concurrency` driven by an opt-in input such as `concurrency-group`, once there is a clear naming scheme that cannot collide with callers.
5. uv cache support (`~/.cache/uv`, `uv cache prune --ci`) and a `package-manager` input for pnpm and Yarn caching in `node-ci.yml`.
6. A `timeout-minutes` input on each reusable workflow instead of the fixed 30 minutes.
7. Docker layer cache `scope` derived from `docker-context` and `dockerfile` in `repo-ci.yml`, so several images built from one repository stop evicting each other.
8. Declared `outputs:` on the reusable workflows (for example the measured coverage percent) so callers stop scraping logs.

## Validation

- `actionlint` 1.7.12 with shellcheck on all workflows: no findings.
- `shellcheck` on the `run:` blocks of both composite actions: no findings.
- `zizmor --offline`: template-injection and Dependabot-cooldown findings resolved; remaining findings are listed above.
- `python -m unittest discover --start-directory actions/coverage-gate`: 12 tests pass.
- `ruff check actions` and `ruff format --check actions`: clean.
- `gitleaks` over the full history: no leaks.
