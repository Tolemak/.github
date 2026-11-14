import argparse
import glob
import shlex
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from gate_common import SOURCE_PATTERNS, changed_files, error, escape, repository, selected


def relative_path(value, root):
    path = Path(value.replace("\\", "/"))
    try:
        return (path if path.is_absolute() else root / path).resolve().relative_to(root).as_posix()
    except ValueError:
        return None


def paths_for(value, root, sources=()):
    paths = {relative_path(value, root)}
    for source in sources:
        paths.add(relative_path(str(Path(source) / value), root))
    return paths - {None}


def report_paths(report, root, src_roots=()):
    if report.suffix.lower() == ".info":
        return {
            path
            for line in report.read_text(encoding="utf-8").splitlines()
            if line.startswith("SF:")
            for path in paths_for(line[3:], root)
        }
    document = ET.parse(report).getroot()
    if document.tag not in {"coverage", "report"}:
        raise ValueError(f"Unsupported coverage XML: {report}")
    sources = [node.text.strip() for node in document.findall("sources/source") if node.text and node.text.strip()]
    paths = set()
    for node in document.findall(".//class[@filename]"):
        paths.update(paths_for(node.attrib["filename"], root, sources))
    for node in document.findall(".//file[@name]"):
        paths.update(paths_for(node.attrib["name"], root))
    for package in document.findall(".//package"):
        for node in package.findall("sourcefile"):
            name = str(Path(package.get("name", "")) / node.attrib["name"])
            paths.update(paths_for(name, root, src_roots))
    return paths


def find_reports(directory):
    return sorted(path for path in directory.rglob("*") if path.is_file() and path.suffix.lower() in {".xml", ".info"})


def source_patterns(value):
    result = tuple(shlex.split(value.replace(",", " ")))
    if not result:
        raise ValueError("coverage-paths must contain at least one source glob")
    return result


def diff_command(reports, base, minimum, changed, src_roots):
    command = [
        "diff-cover",
        *(str(report) for report in reports),
        f"--compare-branch={base}",
        f"--fail-under={minimum}",
        "--diff-range-notation=..",
        "--ignore-staged",
        "--ignore-unstaged",
        "--include",
        *(glob.escape(path) for path in changed),
    ]
    if src_roots:
        command.extend(["--src-roots", *src_roots])
    return command


CONFIG_FILES = "**/*.config.*,**/*rc.js,**/*rc.cjs"


def evaluate(root, base, directory, minimum, includes=SOURCE_PATTERNS, exclude="", src_roots=(), scope_only=False):
    excluded = f"{CONFIG_FILES},{exclude}"
    changed = [new for _, new in changed_files(root, base) if selected(new, includes, excluded)]
    if not changed:
        print("No changed source files require coverage")
        return 0
    reports = find_reports(directory)
    if not reports:
        error("No coverage reports for changed source files")
        return 1
    measured = {report: report_paths(report, root, src_roots) for report in reports}
    missing = sorted(set(changed) - set().union(*measured.values()))
    if len(missing) == len(changed):
        for path in missing:
            error(f"{path}: changed source file is absent from all coverage reports")
        return 1
    for path in missing:
        print(f"::warning::{escape(path)}: absent from all coverage reports, no executable lines or not instrumented")
    if scope_only:
        return 0
    failed = 0
    for group in report_groups(reports):
        files = [path for path in changed if any(path in measured[report] for report in group)]
        if files:
            failed |= subprocess.call(diff_command(group, base, minimum, files, src_roots), cwd=root) != 0
    return int(failed)


def report_groups(reports):
    lcov = [report for report in reports if report.suffix.lower() == ".info"]
    xml = [report for report in reports if report.suffix.lower() != ".info"]
    return [group for group in (xml, lcov) if group]


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", default=".")
    parser.add_argument("--base", required=True)
    parser.add_argument("--coverage-dir", required=True)
    parser.add_argument("--min", type=float, default=80)
    parser.add_argument("--coverage-paths", default=",".join(SOURCE_PATTERNS))
    parser.add_argument("--exclude", default="")
    parser.add_argument("--src-roots", default="")
    parser.add_argument("--scope-only", action="store_true")
    args = parser.parse_args(argv)
    if args.min == 0 or not args.base:
        print("::notice::Diff coverage skipped")
        return 0
    try:
        if not 0 < args.min <= 100:
            raise ValueError("diff-coverage-min must be between 0 and 100")
        return evaluate(
            repository(args.path),
            args.base,
            Path(args.coverage_dir).resolve(),
            args.min,
            source_patterns(args.coverage_paths),
            args.exclude,
            shlex.split(args.src_roots),
            scope_only=args.scope_only,
        )
    except (OSError, ValueError, KeyError, ET.ParseError, subprocess.CalledProcessError) as exc:
        error(str(exc))
        return 1


if __name__ == "__main__":
    sys.exit(main())
