#!/usr/bin/env python3
"""Fail when line coverage in a Clover or Cobertura XML report is below a minimum.

Standard library only, so it runs on any runner that has Python 3.10+.

Line coverage is computed as:
  * Clover (PHPUnit, Istanbul/Vitest): coveredstatements / statements of the
    project-level <metrics> element.
  * Cobertura (coverage.py, Vitest, Jest): lines-covered / lines-valid on the
    root <coverage> element, falling back to line-rate when the counters are absent.
"""

from __future__ import annotations

import argparse
import os
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass


class CoverageError(Exception):
    """The report is missing, unreadable or has no measurable lines."""


@dataclass(frozen=True)
class Coverage:
    format: str
    covered: int | None
    total: int | None
    percent: float


def detect_format(root: ET.Element) -> str:
    if root.tag != "coverage":
        raise CoverageError(f"unsupported root element <{root.tag}>, expected <coverage>")
    if root.find("project") is not None:
        return "clover"
    if "line-rate" in root.attrib or "lines-valid" in root.attrib:
        return "cobertura"
    raise CoverageError("cannot tell whether the report is Clover or Cobertura")


def _int_attr(element: ET.Element, name: str) -> int | None:
    value = element.get(name)
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except ValueError as exc:
        raise CoverageError(f"attribute {name}={value!r} is not a number") from exc


def parse_clover(root: ET.Element) -> Coverage:
    project = root.find("project")
    if project is None:
        raise CoverageError("Clover report has no <project> element")
    # The project-level totals are the <metrics> element directly under <project>;
    # nested <file>/<package> elements carry their own partial metrics.
    metrics = project.find("metrics")
    if metrics is None:
        raise CoverageError("Clover report has no project-level <metrics> element")
    total = _int_attr(metrics, "statements")
    covered = _int_attr(metrics, "coveredstatements")
    if total is None or covered is None:
        raise CoverageError("Clover <metrics> lacks statements/coveredstatements")
    if total <= 0:
        raise CoverageError("Clover report contains no executable statements")
    return Coverage("clover", covered, total, covered * 100.0 / total)


def parse_cobertura(root: ET.Element) -> Coverage:
    total = _int_attr(root, "lines-valid")
    covered = _int_attr(root, "lines-covered")
    if total is not None and covered is not None:
        if total <= 0:
            raise CoverageError("Cobertura report contains no executable lines")
        return Coverage("cobertura", covered, total, covered * 100.0 / total)
    rate = root.get("line-rate")
    if rate is None:
        raise CoverageError("Cobertura report lacks lines-valid/lines-covered and line-rate")
    try:
        percent = float(rate) * 100.0
    except ValueError as exc:
        raise CoverageError(f"line-rate={rate!r} is not a number") from exc
    return Coverage("cobertura", None, None, percent)


def read_coverage(path: str, fmt: str = "auto") -> Coverage:
    try:
        root = ET.parse(path).getroot()
    except FileNotFoundError as exc:
        raise CoverageError(f"coverage report not found: {path}") from exc
    except ET.ParseError as exc:
        raise CoverageError(f"coverage report is not valid XML: {exc}") from exc
    if fmt == "auto":
        fmt = detect_format(root)
    if fmt == "clover":
        return parse_clover(root)
    if fmt == "cobertura":
        return parse_cobertura(root)
    raise CoverageError(f"unknown format {fmt!r}, expected auto, clover or cobertura")


def _append(path_var: str, text: str) -> None:
    target = os.environ.get(path_var)
    if target:
        with open(target, "a", encoding="utf-8") as handle:
            handle.write(text)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("file", help="path to the Clover or Cobertura XML report")
    parser.add_argument("--min", type=float, default=80.0, help="minimum line coverage in percent")
    parser.add_argument("--format", default="auto", choices=["auto", "clover", "cobertura"])
    args = parser.parse_args(argv)

    try:
        result = read_coverage(args.file, args.format)
    except CoverageError as exc:
        print(f"::error title=Coverage gate::{exc}")
        return 2

    percent = round(result.percent, 2)
    detail = f" ({result.covered}/{result.total} lines)" if result.total is not None else ""
    passed = percent >= args.min
    verdict = "passed" if passed else "failed"
    message = f"Line coverage {percent:.2f}%{detail} {verdict}: minimum is {args.min:g}% ({result.format})"

    _append("GITHUB_OUTPUT", f"percent={percent:.2f}\n")
    _append("GITHUB_STEP_SUMMARY", f"### Coverage gate\n\n{'✅' if passed else '❌'} {message}\n")
    if passed:
        print(message)
        return 0
    print(f"::error title=Coverage gate::{message}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
