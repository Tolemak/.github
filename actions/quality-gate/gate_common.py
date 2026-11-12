import fnmatch
import subprocess
from pathlib import Path

SOURCE_PATTERNS = tuple(f"**/*.{ext}" for ext in ("py", "ts", "tsx", "js", "jsx", "mjs", "cjs", "php", "kt"))
DIRECTORIES = ("node_modules", "vendor", "dist", "build", "coverage", ".venv", ".github-shared-ci", ".git")
BUILTIN_EXCLUDES = tuple(f"**/{name}/**" for name in DIRECTORIES)
TEST_EXCLUDES = (
    "**/test/**",
    "**/tests/**",
    "**/__tests__/**",
    "**/*.test.*",
    "**/*.spec.*",
    "**/test_*.py",
    "**/*_test.py",
    "**/src/test/**",
    "**/androidTest/**",
)


def patterns(value):
    return tuple(part.strip() for part in value.split(",") if part.strip())


def matches(path, pattern):
    parts = path.replace("\\", "/").split("/")
    rules = pattern.replace("\\", "/").split("/")
    return match_parts(parts, rules)


def match_parts(parts, rules):
    if not rules:
        return not parts
    if rules[0] == "**":
        return any(match_parts(parts[index:], rules[1:]) for index in range(len(parts) + 1))
    return bool(parts) and fnmatch.fnmatchcase(parts[0], rules[0]) and match_parts(parts[1:], rules[1:])


def selected(path, includes=SOURCE_PATTERNS, exclude="", tests=True):
    excluded = BUILTIN_EXCLUDES + (TEST_EXCLUDES if tests else ()) + patterns(exclude)
    return any(matches(path, item) for item in includes) and not any(matches(path, item) for item in excluded)


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args])


def changed_files(root, base):
    entries = git(root, "diff", "--name-status", "-z", "-M", "--diff-filter=AMR", base, "HEAD", "--").split(b"\0")
    result = []
    index = 0
    while index < len(entries) and entries[index]:
        status = entries[index].decode()
        old = entries[index + 1].decode("utf-8", errors="surrogateescape")
        index += 2
        new = old
        if status.startswith("R"):
            new = entries[index].decode("utf-8", errors="surrogateescape")
            index += 1
        result.append((None if status == "A" else old, new))
    return result


def repository(path):
    return Path(path).resolve()


def escape(value, property_value=False):
    value = str(value).replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    return value.replace(":", "%3A").replace(",", "%2C") if property_value else value


def error(message):
    print(f"::error::{escape(message)}")
