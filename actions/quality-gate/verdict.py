import os
import sys

CHECKS = {
    "tools": "TOOLS",
    "gitleaks": "GITLEAKS",
    "actionlint": "ACTIONLINT",
    "semgrep": "SEMGREP",
    "duplication": "DUPLICATION",
    "duplication-new-clones": "NEW_CLONES",
    "complexity": "COMPLEXITY",
    "coverage-scope": "COVERAGE_SCOPE",
    "diff-coverage": "DIFF_COVERAGE",
    "needs": "NEEDS",
}


def main():
    failed = False
    rows = ["| Check | Result | Detail |", "| --- | --- | --- |"]
    for check, key in CHECKS.items():
        result = os.environ.get(key, "")
        detail = "Completed"
        if result == "skipped":
            detail = "Disabled or base unavailable"
        elif result != "success":
            failed = True
            detail = "Check failed or did not complete; see step log"
        rows.append(f"| {check} | {result or 'missing'} | {detail} |")
    if not os.environ.get("BASE"):
        print("::notice::Base unavailable; new-code checks skipped")
    with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as summary:
        summary.write("\n".join(rows) + "\n")
    return int(failed)


if __name__ == "__main__":
    sys.exit(main())
