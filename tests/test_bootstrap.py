import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("bootstrap", Path(__file__).resolve().parents[1] / "tools/bootstrap.py")
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True)


class BootstrapTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.upstream = self.root / "upstream"
        self.upstream.mkdir()
        git(self.upstream, "init", "-q")
        git(self.upstream, "config", "user.name", "Bootstrap Test")
        git(self.upstream, "config", "user.email", "bootstrap@example.invalid")
        (self.upstream / "source.txt").write_text("baseline\n")
        git(self.upstream, "add", "source.txt")
        git(self.upstream, "commit", "-qm", "test baseline")
        git(self.upstream, "tag", "test-ref")
        self.project = self.root / "project"
        (self.project / "patches").mkdir(parents=True)
        (self.project / "project.json").write_text(json.dumps({"upstream": {
            "url": str(self.upstream), "ref": "test-ref", "commit": git(self.upstream, "rev-parse", "HEAD").strip()}}))
        (self.upstream / "source.txt").write_text("protocol change\n")
        (self.upstream / "added.txt").write_text("new model\n")
        git(self.upstream, "add", "-N", "added.txt")
        patch = git(self.upstream, "diff", "--binary")
        (self.project / "patches/0001-wallet-web-protocol-foundation.patch").write_text(patch)
        # Restore only this disposable test fixture, never a developer checkout.
        git(self.upstream, "reset", "--hard", "HEAD")
        self.destination = self.root / "checkout"

    def test_fresh_checkout_and_repeat_are_idempotent(self):
        first = bootstrap.prepare(self.destination, self.project)
        self.assertEqual("applied", first["patch"])
        self.assertEqual("protocol change\n", (self.destination / "source.txt").read_text())
        self.assertEqual("new model\n", (self.destination / "added.txt").read_text())
        before = git(self.destination, "diff", "--binary", "HEAD")
        second = bootstrap.prepare(self.destination, self.project)
        self.assertEqual("already_applied", second["patch"])
        self.assertEqual(before, git(self.destination, "diff", "--binary", "HEAD"))

    def test_unrelated_work_is_preserved(self):
        bootstrap.prepare(self.destination, self.project)
        path = self.destination / "source.txt"
        path.write_text("developer change\n")
        with self.assertRaisesRegex(ValueError, "preserving"):
            bootstrap.prepare(self.destination, self.project)
        self.assertEqual("developer change\n", path.read_text())

    def test_incorrect_revision_is_not_reset(self):
        bootstrap.prepare(self.destination, self.project)
        git(self.destination, "config", "user.name", "Bootstrap Test")
        git(self.destination, "config", "user.email", "bootstrap@example.invalid")
        git(self.destination, "add", ".")
        git(self.destination, "commit", "-qm", "different revision")
        head = git(self.destination, "rev-parse", "HEAD")
        with self.assertRaisesRegex(ValueError, "Unexpected upstream revision"):
            bootstrap.prepare(self.destination, self.project)
        self.assertEqual(head, git(self.destination, "rev-parse", "HEAD"))

    def test_source_moved_between_modules_remains_idempotent(self):
        old = self.upstream / "source.txt"
        new = self.upstream / "new-module/source.txt"
        new.parent.mkdir()
        old.rename(new)
        git(self.upstream, "add", "-N", "new-module/source.txt")
        patch = git(self.upstream, "diff", "--binary", "--no-renames", "HEAD")
        (self.project / "patches/0001-wallet-web-protocol-foundation.patch").write_text(patch)
        git(self.upstream, "reset", "--hard", "HEAD")
        first = bootstrap.prepare(self.destination, self.project)
        self.assertEqual("applied", first["patch"])
        self.assertFalse((self.destination / "source.txt").exists())
        self.assertEqual("baseline\n", (self.destination / "new-module/source.txt").read_text())
        self.assertEqual("already_applied", bootstrap.prepare(self.destination, self.project)["patch"])


if __name__ == "__main__":
    unittest.main()
