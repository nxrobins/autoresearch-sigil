"""Exercise pin refusal and real clone search/resume without host-side numerics.

Native tests require both explicit executable/source variables. The smaller
unit suite alone is not evidence that search ran. All state lives in fresh
temporary directories; the original SIGIL implementation is never edited.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
CLI = os.environ.get("SIGIL_INTEGRATION_CLI")
SOURCE = os.environ.get("SIGIL_SOURCE_CHECKOUT")


def copied(directory):
    target = Path(directory) / "sigil"
    shutil.copytree(HERE, target, ignore=shutil.ignore_patterns(".sigil", "__pycache__"))
    spec = importlib.util.spec_from_file_location("clone_search", target / "library_search.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fingerprint(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob("*") if p.is_file() and "__pycache__" not in p.parts}


class PinTests(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory(prefix="autoresearch-pin-test-")
        self.addCleanup(self.scratch.cleanup)
        self.module = copied(self.scratch.name)

    def test_valid_pin_then_source_and_lock_drift_are_detected(self):
        module = self.module
        self.assertEqual(len(module.load_pin()["dependencies"]), 9)
        for name in ("src/tool_search.sigil", "sigil-package.lock.json", "search.py"):
            path = module.PACKAGE / name
            before = path.read_bytes()
            path.write_bytes(before + b"\n")
            with self.assertRaisesRegex(ValueError, "consumer pin mismatch"):
                module.load_pin()
            path.write_bytes(before)
        self.assertEqual(len(module.load_pin()["consumer_files"]), 17)

    def test_dependency_version_and_commit_are_not_floating(self):
        module = self.module
        original = module.PIN.read_bytes()
        pin = json.loads(original)
        pin["dependencies"]["sigil/rng"]["version"] = "0.1.0-public.99"
        module.PIN.write_text(json.dumps(pin))
        with self.assertRaisesRegex(ValueError, "dependency version"):
            module.load_pin()
        pin = json.loads(original)
        pin["commit"] = "main"
        module.PIN.write_text(json.dumps(pin))
        with self.assertRaisesRegex(ValueError, "complete commit"):
            module.load_pin()
        module.PIN.write_bytes(original)
        self.assertEqual(module.load_pin()["commit"], "976fd697ae2251207fc8e2a4479b45f9954638bf")

    def test_symlink_and_noncanonical_pinned_paths_refuse(self):
        module = self.module
        path = module.PACKAGE / "src/tool_search.sigil"
        target = module.ROOT / "saved-source"
        path.rename(target)
        path.symlink_to(target)
        with self.assertRaisesRegex(ValueError, "symlink"):
            module.load_pin()
        for name in ("../x", "/tmp/x", "x/../y", "x//y", "x\\y", "./x"):
            with self.assertRaises(ValueError):
                module.relative(name)
        self.assertEqual(module.relative("src/tool.sigil"), Path("src/tool.sigil"))

    def test_solver_witness_is_required_even_with_override_environment(self):
        module = self.module
        with patch.object(module, "checked", return_value={"data": {"certificate": {
                "solver_verified": False}}}):
            with self.assertRaisesRegex(ValueError, "fresh solver"):
                module.verify("sigil")
        with patch.object(module, "checked", return_value={"data": {"certificate": {
                "solver_verified": True}}}):
            self.assertTrue(module.verify("sigil")["solver_verified"])
        with patch.dict(os.environ, {"SIGIL_ALLOW_UNVERIFIED_CERT": "1"}):
            self.assertNotIn("SIGIL_ALLOW_UNVERIFIED_CERT", module.cli_environment())
            self.assertEqual(os.environ["SIGIL_ALLOW_UNVERIFIED_CERT"], "1")

    def test_existing_cache_is_verified_not_repaired(self):
        module = self.module
        cache = module.PACKAGE / ".sigil"
        cache.mkdir()
        (cache / "sentinel").write_bytes(b"previous state")
        before = fingerprint(module.PACKAGE)
        with patch.object(module, "verify", side_effect=ValueError("stale cache")), \
                patch.object(module, "materialize") as extraction:
            with self.assertRaisesRegex(ValueError, "stale cache"):
                module.setup("sigil", Path("unused"))
            extraction.assert_not_called()
        self.assertEqual(fingerprint(module.PACKAGE), before)

    def test_package_and_storage_overrides_are_rejected_before_execution(self):
        for flag in ("--package", "--pack", "--storage-package", "--kv-store", "--unknown"):
            result = subprocess.run([sys.executable, str(self.module.ROOT / "library_search.py"),
                                     "search", "--sigil", "/not-a-sigil-executable", flag, "x"],
                                    capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 1)
            self.assertIn("unsupported search option", result.stderr)


@unittest.skipUnless(CLI and SOURCE, "set SIGIL_INTEGRATION_CLI and SIGIL_SOURCE_CHECKOUT to execute native tests")
class NativeTests(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory(prefix="autoresearch-clone-native-")
        self.addCleanup(self.scratch.cleanup)
        self.module = copied(self.scratch.name)
        self.root = Path(self.scratch.name)

    def run_command(self, action, extra=(), success=True):
        result = subprocess.run([sys.executable, str(self.module.ROOT / "library_search.py"),
                                 action, "--sigil", CLI, *extra], capture_output=True,
                                text=True, timeout=300)
        if success:
            self.assertEqual(result.returncode, 0, result.stderr)
            return json.loads(result.stdout)
        self.assertNotEqual(result.returncode, 0, result)
        return result

    def setup_package(self):
        before = self.module.PACKAGE.joinpath("sigil-package.lock.json").read_bytes()
        result = self.run_command("setup", ["--sigil-checkout", SOURCE])
        self.assertEqual(result["status"], "ready")
        self.assertEqual(self.module.PACKAGE.joinpath("sigil-package.lock.json").read_bytes(), before)

    def test_fresh_setup_pins_source_and_preserves_lock_on_recheck_and_drift(self):
        self.setup_package()
        package = self.module.PACKAGE
        pin = self.module.load_pin()
        for name in ["search.py", "API.md", "SEARCH_API.md", "api-card.json",
                     *[f"src/{entry}.sigil" for entry in json.loads((package / "sigil-package.json").read_text())["modules"]]]:
            original = self.module.git(SOURCE, "show", f"{pin['commit']}:{pin['source']}/{name}")
            self.assertEqual((package / name).read_bytes(), original)
        before = fingerprint(package)
        self.run_command("setup", ["--sigil-checkout", SOURCE])
        self.assertEqual(fingerprint(package), before)
        dependency = next((package / ".sigil/deps/sigil/rng").glob("*/src/rng.sigil"))
        original = dependency.read_bytes()
        dependency.write_bytes(original + b"\n")
        changed = fingerprint(package)
        self.run_command("setup", ["--sigil-checkout", SOURCE], success=False)
        self.assertEqual(fingerprint(package), changed)
        dependency.write_bytes(original)
        self.run_command("setup", ["--sigil-checkout", SOURCE])

    def test_missing_revision_refuses_before_cache_or_lock_changes(self):
        pin = self.module.load_pin()
        pin["commit"] = "0" * 40
        self.module.PIN.write_text(json.dumps(pin))
        before = fingerprint(self.module.PACKAGE)
        self.run_command("setup", ["--sigil-checkout", SOURCE], success=False)
        self.assertFalse((self.module.PACKAGE / ".sigil").exists())
        self.assertEqual(fingerprint(self.module.PACKAGE), before)

    def test_both_arms_and_exchange_resume_match_and_failures_preserve_history(self):
        self.setup_package()
        for arm in ("discrete", "hybrid"):
            base = ["--generations", "1", "--steps", "2", "--arm", arm]
            full = self.run_command("search", [*base, "--out-dir", str(self.root / f"{arm}-full")])
            self.assertTrue(full["complete"])
            self.assertEqual(full["candidates_evaluated"], 16)
            self.assertEqual(full["transitions"], 17)
            expected = Path(full["checkpoint"]).read_bytes()
            part = self.run_command("search", [*base, "--transitions", "5", "--out-dir", str(self.root / f"{arm}-part")])
            self.assertFalse(part["complete"])
            checkpoint = Path(part["checkpoint"])
            history = fingerprint(checkpoint.parent)
            resumed = self.run_command("search", [*base, "--resume", str(checkpoint), "--out-dir", str(self.root / f"{arm}-resumed")])
            self.assertTrue(resumed["complete"])
            self.assertEqual(Path(resumed["checkpoint"]).read_bytes(), expected)
            self.assertEqual(fingerprint(checkpoint.parent), history)
            refused_dir = self.root / f"{arm}-wrong"
            self.run_command("search", [*base, "--seed", "43", "--resume", str(checkpoint), "--out-dir", str(refused_dir)], success=False)
            self.assertFalse(refused_dir.exists())
            self.run_command("search", [*base, "--out-dir", str(checkpoint.parent)], success=False)
            self.assertEqual(fingerprint(checkpoint.parent), history)
            corrupt = self.root / f"{arm}-corrupt.json"
            corrupt.write_bytes(b"not a checkpoint")
            self.run_command("search", [*base, "--resume", str(corrupt), "--out-dir", str(refused_dir)], success=False)
            self.assertFalse(refused_dir.exists())
            if arm == "hybrid":
                exchange = [*base, "--evaluation", "exchange", "--job-id", "17" * 32]
                part = self.run_command("search", [*exchange, "--transitions", "5", "--out-dir", str(self.root / "exchange-part")])
                checkpoint = Path(part["checkpoint"])
                history = fingerprint(checkpoint.parent)
                finished = self.run_command("search", [*exchange, "--resume", str(checkpoint), "--out-dir", str(self.root / "exchange-resumed")])
                self.assertEqual(Path(finished["checkpoint"]).read_bytes(), expected)
                self.assertEqual(fingerprint(checkpoint.parent), history)
                self.run_command("search", [*base, "--evaluation", "exchange", "--job-id", "18" * 32,
                                            "--resume", str(checkpoint), "--out-dir", str(refused_dir)], success=False)
                self.assertFalse(refused_dir.exists())


if __name__ == "__main__":
    unittest.main()
