import subprocess
import tempfile
from pathlib import Path


class GitRepository:
    def __enter__(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        self.git("init", "--quiet")
        self.git("config", "user.name", "Gate tests")
        self.git("config", "user.email", "gate@example.invalid")
        self.git("config", "core.autocrlf", "false")
        return self

    def __exit__(self, *args):
        self.temporary.cleanup()

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.root), *args]).decode().strip()

    def write(self, name, content):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def commit(self):
        self.git("add", ".")
        self.git("-c", "commit.gpgsign=false", "commit", "--quiet", "--allow-empty", "-m", "Fixture")
        return self.git("rev-parse", "HEAD")
