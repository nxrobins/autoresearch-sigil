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
import struct
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
        for workload in module.WORKLOADS:
            self.assertEqual(len(module.load_pin(workload)["dependencies"]), 9)
            names = ["src/tool_search.sigil", "sigil-package.lock.json", "search.py"]
            if workload == "regression":
                names.append("dataset.json")
            for name in names:
                path = module.package_for(workload) / name
                before = path.read_bytes()
                path.write_bytes(before + b"\n")
                with self.assertRaisesRegex(ValueError, "consumer pin mismatch"):
                    module.load_pin(workload)
                path.write_bytes(before)
        self.assertEqual(len(module.load_pin()["consumer_files"]), 17)
        self.assertEqual(len(module.load_pin("regression")["consumer_files"]), 18)

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
        self.assertEqual(module.load_pin()["commit"], "ded373473fadedce69218cd161124ce403ea2db5")

    def test_missing_workload_or_input_pin_refuses(self):
        module = self.module
        original = module.PIN.read_bytes()
        pin = json.loads(original)
        del pin["workloads"]["regression"]
        module.PIN.write_text(json.dumps(pin))
        with self.assertRaisesRegex(ValueError, "both pinned search workloads"):
            module.load_pin()
        pin = json.loads(original)
        del pin["workloads"]["regression"]["consumer_files"]["dataset.json"]
        module.PIN.write_text(json.dumps(pin))
        with self.assertRaisesRegex(ValueError, "input inventory"):
            module.load_pin("regression")
        with self.assertRaisesRegex(ValueError, "unsupported search workload"):
            module.load_pin("other")

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
        for workload in module.WORKLOADS:
            package = module.package_for(workload)
            cache = package / ".sigil"
            cache.mkdir()
            (cache / "sentinel").write_bytes(b"previous state")
            before = fingerprint(package)
            with patch.object(module, "verify", side_effect=ValueError("stale cache")), \
                    patch.object(module, "materialize") as extraction:
                with self.assertRaisesRegex(ValueError, "stale cache"):
                    module.setup("sigil", Path("unused"), workload)
                extraction.assert_not_called()
            self.assertEqual(fingerprint(package), before)

    def test_package_and_storage_overrides_are_rejected_before_execution(self):
        for workload in self.module.WORKLOADS:
            for flag in ("--package", "--pack", "--storage-package", "--kv-store", "--unknown"):
                result = subprocess.run([sys.executable, str(self.module.ROOT / "library_search.py"),
                                         "search", "--workload", workload,
                                         "--sigil", "/not-a-sigil-executable", flag, "x"],
                                        capture_output=True, text=True, timeout=30)
                self.assertEqual(result.returncode, 1)
                self.assertIn("unsupported search option", result.stderr)

    def test_workload_dispatch_and_unknown_selector(self):
        module = self.module
        for options, workload in (([], "quadratic"), (["--workload", "quadratic"], "quadratic"),
                                  (["--workload", "regression"], "regression")):
            with patch.object(sys, "argv", ["library_search.py", "search", *options,
                                           "--out-dir", "new-output"]), \
                    patch.object(module, "verify") as verification, \
                    patch.object(module.subprocess, "run") as execution:
                execution.return_value.returncode = 0
                self.assertEqual(module.main(), 0)
                package = module.package_for(workload)
                verification.assert_called_once_with("sigil", package)
                self.assertEqual(execution.call_args.args[0], [sys.executable, str(package / "search.py"),
                                 "--sigil", "sigil", "--package", str(package), "--out-dir", "new-output"])
        result = subprocess.run([sys.executable, str(module.ROOT / "library_search.py"),
                                 "search", "--workload", "unknown"], capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 2)
        self.assertIn(b"invalid choice", result.stderr)


class NativeHarness(unittest.TestCase):
    workload = "quadratic"

    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory(prefix="autoresearch-clone-native-")
        self.addCleanup(self.scratch.cleanup)
        self.module = copied(self.scratch.name)
        self.root = Path(self.scratch.name)

    def run_command(self, action, extra=(), success=True, workload=None):
        workload = self.workload if workload is None else workload
        result = subprocess.run([sys.executable, str(self.module.ROOT / "library_search.py"),
                                 action, "--workload", workload, "--sigil", CLI, *extra],
                                capture_output=True, text=True, timeout=300)
        if success:
            self.assertEqual(result.returncode, 0, result.stderr)
            return json.loads(result.stdout)
        self.assertNotEqual(result.returncode, 0, result)
        return result

    def setup_package(self):
        package = self.module.package_for(self.workload)
        before = package.joinpath("sigil-package.lock.json").read_bytes()
        result = self.run_command("setup", ["--sigil-checkout", SOURCE])
        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["workload"], self.workload)
        self.assertEqual(result["source_commit"], self.module.load_pin(self.workload)["commit"])
        self.assertEqual(package.joinpath("sigil-package.lock.json").read_bytes(), before)


@unittest.skipUnless(CLI and SOURCE, "set SIGIL_INTEGRATION_CLI and SIGIL_SOURCE_CHECKOUT to execute native tests")
class NativeTests(NativeHarness):

    def test_fresh_setup_pins_source_and_preserves_lock_on_recheck_and_drift(self):
        self.setup_package()
        package = self.module.package_for(self.workload)
        pin = self.module.load_pin(self.workload)
        for name in ["search.py", "API.md", "api-card.json",
                     "dataset.json" if self.workload == "regression" else "SEARCH_API.md",
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
        pin = self.module.load_pin(self.workload)
        pin["commit"] = "0" * 40
        self.module.PIN.write_text(json.dumps(pin))
        package = self.module.package_for(self.workload)
        before = fingerprint(package)
        self.run_command("setup", ["--sigil-checkout", SOURCE], success=False)
        self.assertFalse((package / ".sigil").exists())
        self.assertEqual(fingerprint(package), before)

    def test_both_arms_and_exchange_resume_match_and_failures_preserve_history(self):
        self.setup_package()
        for arm in ("discrete", "hybrid"):
            steps = "12" if self.workload == "regression" else "2"
            base = ["--generations", "1", "--steps", steps, "--arm", arm]
            full = self.run_command("search", [*base, "--out-dir", str(self.root / f"{arm}-full")])
            self.assertTrue(full["complete"])
            self.assertEqual(full["candidates_evaluated"], 16)
            self.assertEqual(full["transitions"], 17)
            if self.workload == "regression":
                self.assertEqual(full["task"], "fixed-regression-v1")
                dataset = json.loads((self.module.package_for(self.workload) / "dataset.json").read_bytes())
                self.assertEqual(full["dataset_sha256"], dataset["identity_sha256"])
                self.assertEqual(len(full["candidate_gradients"]), 8)
                for split, field in (("train", "training_loss"), ("validation", "validation_loss")):
                    rows = dataset[split]
                    expected_loss = sum((full["slope"] * x + full["bias"] - y) ** 2 for x, y in rows) / len(rows)
                    self.assertAlmostEqual(full[field], expected_loss, delta=1e-10)
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
                if self.workload == "regression":
                    for field in ("training_loss", "validation_loss", "slope", "bias", "candidate_gradients"):
                        self.assertEqual(finished[field], full[field])
                self.assertEqual(fingerprint(checkpoint.parent), history)
                self.run_command("search", [*base, "--evaluation", "exchange", "--job-id", "18" * 32,
                                            "--resume", str(checkpoint), "--out-dir", str(refused_dir)], success=False)
                self.assertFalse(refused_dir.exists())


@unittest.skipUnless(CLI and SOURCE, "set SIGIL_INTEGRATION_CLI and SIGIL_SOURCE_CHECKOUT to execute native tests")
class RegressionNativeTests(NativeTests):
    workload = "regression"

    def test_corrupt_checkpoint_with_valid_program_identity_refuses(self):
        self.setup_package()
        result = self.run_command("search", ["--transitions", "0", "--out-dir", str(self.root / "valid")])
        valid = Path(result["checkpoint"])
        prior = fingerprint(valid.parent)
        corrupt = self.root / "corrupt"
        corrupt.mkdir()
        shutil.copy2(valid.parent / "program-identity.hex", corrupt / "program-identity.hex")
        checkpoint = corrupt / "checkpoint.json"
        checkpoint.write_bytes(b"not a checkpoint")
        malformed = fingerprint(corrupt)
        output = self.root / "refused-output"
        refused = self.run_command("search", ["--resume", str(checkpoint),
                                             "--out-dir", str(output)], success=False)
        self.assertIn("native search refused", refused.stderr)
        self.assertFalse(output.exists())
        self.assertEqual(fingerprint(valid.parent), prior)
        self.assertEqual(fingerprint(corrupt), malformed)

    def test_cross_workload_and_dataset_resume_refuse_without_writing(self):
        self.setup_package()
        self.run_command("setup", ["--sigil-checkout", SOURCE], workload="quadratic")
        base = ["--generations", "1", "--steps", "2", "--transitions", "2"]
        runs = {workload: self.run_command("search", [*base, "--out-dir", str(self.root / workload)],
                                          workload=workload) for workload in self.module.WORKLOADS}
        before = {name: fingerprint(self.root / name) for name in runs}
        for selected, prior in (("quadratic", "regression"), ("regression", "quadratic")):
            output = self.root / f"wrong-{selected}"
            self.run_command("search", [*base, "--resume", runs[prior]["checkpoint"],
                                        "--out-dir", str(output)], workload=selected, success=False)
            self.assertFalse(output.exists())
        # Even with a current regression marker, native task/profile validation
        # must reject the quadratic checkpoint rather than relying on a sidecar.
        spoof = self.root / "foreign-checkpoint"
        spoof.mkdir()
        shutil.copy2(runs["quadratic"]["checkpoint"], spoof / "checkpoint.json")
        shutil.copy2(self.root / "regression/program-identity.hex", spoof / "program-identity.hex")
        output = self.root / "foreign-output"
        self.run_command("search", [*base, "--resume", str(spoof / "checkpoint.json"),
                                    "--out-dir", str(output)], success=False)
        self.assertFalse(output.exists())
        checkpoint = runs["regression"]["checkpoint"]
        for options in (["--dataset-sha256", "00" * 32], ["--steps", "13"],
                        ["--evaluation", "exchange", "--job-id", "17" * 32]):
            self.run_command("search", [*base, *options, "--resume", checkpoint,
                                        "--out-dir", str(output)], success=False)
            self.assertFalse(output.exists())
        for name in runs:
            self.assertEqual(fingerprint(self.root / name), before[name])

    def test_default_configuration_and_native_dataset_validation(self):
        self.setup_package()
        package = self.module.package_for(self.workload)
        result = self.run_command("search", ["--transitions", "0", "--out-dir", str(self.root / "defaults")])
        self.assertFalse(result["complete"])
        self.assertEqual(result["candidate_budget"], 24)  # two generations plus initial population
        spec = importlib.util.spec_from_file_location("regression_driver", package / "search.py")
        driver = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(driver)
        initial = driver.initial_request(42, 54, 2, 12, True)
        state = driver.invoke(CLI, package, driver.command(b"ASOP", initial + Path(result["checkpoint"]).read_bytes()))
        self.assertEqual(driver.header(state)[2], 2)
        self.assertEqual(len(state), 1736)
        self.assertEqual(state[160:192].hex(), result["dataset_sha256"])
        # Exercise the real RGDS comparison with changed rows and a consistent
        # file hash; the native dataset remains unchanged and must reject it.
        dataset = package / "dataset.json"
        original = dataset.read_bytes()
        record = json.loads(original)
        record["validation"][0][1] += 1
        wire = b"RGRD" + bytes((1, 4, 2, 0)) + struct.pack(
            "<12d", *(v for row in record["train"] + record["validation"] for v in row))
        record["identity_sha256"] = hashlib.sha256(wire).hexdigest()
        dataset.write_text(json.dumps(record))
        with self.assertRaisesRegex(ValueError, "compiled regression rows"):
            driver.verify_dataset(CLI, package)
        dataset.write_bytes(original)


if __name__ == "__main__":
    unittest.main()
