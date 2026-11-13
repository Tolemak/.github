import os
import secrets
import string
import subprocess
from pathlib import Path


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args]).decode().strip()


def write(root, name, content):
    target = root / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def commit(root):
    git(root, "add", ".")
    git(root, "-c", "commit.gpgsign=false", "commit", "--quiet", "--allow-empty", "-m", "Fixture")
    return git(root, "rev-parse", "HEAD")


def repository(root):
    root.mkdir(parents=True)
    git(root, "init", "--quiet")
    git(root, "config", "user.name", "Gate self-test")
    git(root, "config", "user.email", "gate@example.invalid")


def clone_source():
    return "\n".join(f"value_{index} = input_value * {index} + {index + 17}" for index in range(40)) + "\n"


def complex_source():
    body = "".join(f"    if value == {index}:\n        return {index}\n" for index in range(20))
    return f"def calculate(value):\n{body}    return -1\n"


def populate(root, case):
    if case == "semgrep":
        write(
            root, "unsafe.py", "import subprocess\n\ndef execute(command):\n    subprocess.call(command, shell=True)\n"
        )
    elif case in {"duplication", "new-clones"}:
        write(root, "first.py", clone_source())
        write(root, "second.py", clone_source())
    elif case == "complexity":
        write(root, "complex.py", complex_source())
    elif case in {"diff-coverage", "coverage-scope"}:
        write(root, "source.py", "value = 1\n")
        name = "source.py" if case == "diff-coverage" else "different.py"
        write(
            root,
            "reports/coverage.xml",
            f'<coverage line-rate="0" lines-covered="0" lines-valid="1"><packages><package name="">'
            f'<classes><class name="source" filename="{name}"><lines><line number="1" hits="0"/>'
            "</lines></class></classes></package></packages></coverage>",
        )
    elif case == "gitleaks":
        token = "ghp_" + "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(36))
        write(root, "credentials.txt", f"github_token={token}\n")
    elif case == "actionlint":
        write(
            root,
            ".github/workflows/invalid.yml",
            "name: Invalid\non: push\njobs:\n  invalid:\n    steps:\n      - run: true\n",
        )


def main():
    destination = Path(os.environ["RUNNER_TEMP"]) / "quality-gate-cases"
    case = os.environ["CASE"]
    negative = os.environ["EXPECTED"] == "failure"
    root = destination / case
    repository(root)
    if case == "new-clones":
        write(root, "first.py", clone_source())
    base = commit(root)
    if negative:
        populate(root, case)
    else:
        populate_positive(root, case)
    commit(root)
    if negative and case == "gitleaks":
        git(root, "rm", "credentials.txt")
        commit(root)
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
        output.write(f"base={base}\npath={root}\n")


def populate_positive(root, case):
    write(root, "source.py", "value = 1\n")
    if case == "actionlint":
        write(
            root,
            ".github/workflows/valid.yml",
            "name: Valid\non: push\njobs:\n  check:\n    runs-on: ubuntu-24.04\n    steps:\n      - run: echo ok\n",
        )
    if case in {"diff-coverage", "coverage-scope"}:
        write(
            root,
            "reports/coverage.xml",
            '<coverage line-rate="1" lines-covered="1" lines-valid="1"><packages><package name="">'
            '<classes><class name="source" filename="source.py"><lines><line number="1" hits="1"/>'
            "</lines></class></classes></package></packages></coverage>",
        )


if __name__ == "__main__":
    main()
