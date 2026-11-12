import argparse
import subprocess
import sys
from pathlib import Path

from gate_common import BUILTIN_EXCLUDES, TEST_EXCLUDES, error, patterns

CODE_FORMATS = "javascript,typescript,jsx,tsx,vue,python,php,kotlin,java,bash"


def command(path, exclude, maximum, base, formats=CODE_FORMATS):
    executable = Path(__file__).parent / "node_modules" / ".bin" / "jscpd"
    args = [
        str(executable),
        "--format",
        formats,
        "--ignore",
        ",".join(BUILTIN_EXCLUDES + TEST_EXCLUDES + patterns(exclude)),
    ]
    if base:
        args.extend(["--baseline-from-ref", base, "--fail-on-new-clones", "0"])
    else:
        if not 0 <= maximum <= 100:
            raise ValueError("duplication-max must be between 0 and 100")
        args.extend(["--threshold", str(maximum)])
    return [*args, path]


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", default=".")
    parser.add_argument("--exclude", default="")
    parser.add_argument("--max", type=float, default=3)
    parser.add_argument("--base", default="")
    parser.add_argument("--formats", default=CODE_FORMATS)
    args = parser.parse_args(argv)
    try:
        return subprocess.call(command(args.path, args.exclude, args.max, args.base, args.formats or CODE_FORMATS))
    except (OSError, ValueError) as exc:
        error(str(exc))
        return 1


if __name__ == "__main__":
    sys.exit(main())
