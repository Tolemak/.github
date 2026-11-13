import argparse
import json
import sys

from gate_common import error


def evaluate(needs, allowed=""):
    if not isinstance(needs, dict):
        raise ValueError("needs must be a JSON object")
    failed = False
    for job, data in needs.items():
        result = data.get("result") if isinstance(data, dict) else None
        passed = result == "success" or (result == "skipped" and job in allowed.split())
        if not passed:
            error(f"Required job {job}: {result}")
            failed = True
    return int(failed)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--needs", default="{}")
    parser.add_argument("--allow-skipped", default="")
    args = parser.parse_args(argv)
    try:
        return evaluate(json.loads(args.needs), args.allow_skipped)
    except (ValueError, TypeError) as exc:
        error(str(exc))
        return 1


if __name__ == "__main__":
    sys.exit(main())
