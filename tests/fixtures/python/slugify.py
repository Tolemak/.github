"""Tiny module used by the python-ci self-test."""

import re
import unicodedata

_NON_WORD = re.compile(r"[^a-z0-9]+")


def slugify(text: str, separator: str = "-") -> str:
    """Turn arbitrary text into a lowercase ASCII slug."""
    if not separator:
        raise ValueError("separator must not be empty")
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return _NON_WORD.sub(separator, ascii_text.lower()).strip(separator)


def main(argv: list[str]) -> int:
    for arg in argv:
        print(slugify(arg))
    return 0
