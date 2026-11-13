import argparse
import json
import sys
from pathlib import Path

from gate_common import error, escape

FAIL_SEVERITIES = {"ERROR", "WARNING", "CRITICAL", "HIGH", "MEDIUM"}


def evaluate(report, exit_code, excluded=""):
    if exit_code not in (0, 1):
        raise ValueError(f"Semgrep failed with exit code {exit_code}")
    if not isinstance(report, dict) or not isinstance(report.get("results"), list):
        raise ValueError("Semgrep JSON must contain results")
    for issue in report.get("errors") or []:
        if not isinstance(issue, dict) or issue.get("level") != "warn":
            raise ValueError(f"Semgrep reported a scan error: {issue}")
        print(f"::warning::{escape(issue.get('message', 'Semgrep warning'))}")
    failed = False
    for finding in report["results"]:
        rule = finding["check_id"]
        if rule.rsplit(".", 1)[-1] in excluded.split():
            continue
        severity = finding["extra"]["severity"].upper()
        if severity not in FAIL_SEVERITIES | {"INFO", "LOW"}:
            raise ValueError(f"Unknown Semgrep severity: {severity}")
        blocking = severity in FAIL_SEVERITIES
        failed |= blocking
        level = "error" if blocking else "notice"
        path = escape(finding["path"], property_value=True)
        line = int(finding["start"]["line"])
        message = escape(f"{rule} ({severity}): {finding['extra']['message']}")
        print(f"::{level} file={path},line={line}::{message}")
    return int(failed)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("report")
    parser.add_argument("--exit-code", type=int, required=True)
    parser.add_argument("--exclude-rules", default="")
    args = parser.parse_args(argv)
    try:
        return evaluate(json.loads(Path(args.report).read_text(encoding="utf-8")), args.exit_code, args.exclude_rules)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        error(str(exc))
        return 1


if __name__ == "__main__":
    sys.exit(main())
