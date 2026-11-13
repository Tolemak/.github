import shutil
import sys
from pathlib import Path


def prepare(source, target, manifest):
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)
    for name in manifest.read_text(encoding="utf-8").splitlines():
        relative = Path(name)
        if relative.is_absolute() or ".." in relative.parts or relative.suffix not in {".yaml", ".yml"}:
            raise ValueError(f"Invalid rule path: {name}")
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / relative, destination)


if __name__ == "__main__":
    prepare(*(Path(value) for value in sys.argv[1:]))
