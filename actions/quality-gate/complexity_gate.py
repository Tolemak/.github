import argparse
import subprocess
import sys
from collections import defaultdict

import lizard
from gate_common import changed_files, error, git, repository, selected


def functions(filename, content):
    grouped = defaultdict(list)
    for function in lizard.analyze_file.analyze_source_code(filename, content).function_list:
        grouped[function.name].append(function)
    return grouped


def regressions(filename, before, after, maximum):
    previous = functions(filename, before)
    for name, current in functions(filename, after).items():
        for index, function in enumerate(current):
            prior = previous[name][index] if index < len(previous[name]) else None
            if function.cyclomatic_complexity > maximum and (
                prior is None or function.cyclomatic_complexity > prior.cyclomatic_complexity
            ):
                yield function


def evaluate(root, base, maximum, exclude=""):
    failed = False
    for old, new in changed_files(root, base):
        if not selected(new, exclude=exclude):
            continue
        before = git(root, "show", f"{base}:{old}").decode("utf-8", errors="replace") if old else ""
        after = git(root, "show", f"HEAD:{new}").decode("utf-8", errors="replace")
        for function in regressions(new, before, after, maximum):
            error(f"{new}:{function.start_line}: {function.long_name} CCN={function.cyclomatic_complexity} > {maximum}")
            failed = True
    return int(failed)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", default=".")
    parser.add_argument("--base", required=True)
    parser.add_argument("--max", type=int, default=15)
    parser.add_argument("--exclude", default="")
    args = parser.parse_args(argv)
    if args.max == 0 or not args.base:
        print("::notice::New-code complexity skipped")
        return 0
    try:
        if args.max < 0:
            raise ValueError("complexity-max must be nonnegative")
        return evaluate(repository(args.path), args.base, args.max, args.exclude)
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        error(str(exc))
        return 1


if __name__ == "__main__":
    sys.exit(main())
