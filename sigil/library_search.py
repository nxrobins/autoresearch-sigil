"""Run the pinned SIGIL search from this clone; refuse drift instead of upgrading.

Setup reads immutable objects from an explicit local SIGIL Git checkout. It
never fetches or copies that checkout's working files. Libraries are generated
cache, not a second maintained source tree. This is a local single-user tool,
not a hostile-filesystem or authenticated-distribution boundary.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT / "library-search"
PIN = ROOT / "sigil-source.json"


def relative(value):
    if (not isinstance(value, str) or not value or "\\" in value
            or PurePosixPath(value).is_absolute()
            or any(part in ("", ".", "..") for part in value.split("/"))):
        raise ValueError("source pin must use a canonical relative path")
    return Path(*PurePosixPath(value).parts)


def read_regular(root, name):
    path = root
    for component in relative(name).parts:
        path = path / component
        if path.is_symlink():
            raise ValueError(f"pinned input must not be a symlink: {name}")
    if not path.is_file():
        raise ValueError(f"pinned input is missing or not regular: {name}")
    return path.read_bytes()


def load_pin():
    pin = json.loads(read_regular(ROOT, PIN.name))
    if pin.get("format") != "autoresearch-sigil-source-v1":
        raise ValueError("unsupported SIGIL source pin")
    if re.fullmatch(r"[0-9a-f]{40}", pin["commit"]) is None:
        raise ValueError("SIGIL source must be pinned to a complete commit")
    if len(pin["dependencies"]) != 9:
        raise ValueError("expected the nine pinned search libraries")
    for name, expected in pin["consumer_files"].items():
        actual = hashlib.sha256(read_regular(PACKAGE, name)).hexdigest()
        if actual != expected:
            raise ValueError(f"consumer pin mismatch: {name}; use an explicit upgrade")
    manifest = json.loads(read_regular(PACKAGE, "sigil-package.json"))
    declared = {entry["package"]: entry for entry in manifest["dependencies"]}
    if set(declared) != set(pin["dependencies"]):
        raise ValueError("consumer dependencies differ from the source pin")
    for identity, entry in pin["dependencies"].items():
        relative(entry["path"])
        if (declared[identity]["content_hash"] != entry["content_hash"]
                or declared[identity]["requirement"] != "=" + entry["version"]
                or re.fullmatch(r"[0-9a-f]{40}", entry["tree"]) is None):
            raise ValueError("dependency version, content or tree pin differs")
    return pin


def git(checkout, *arguments):
    return subprocess.run(["git", "-C", str(checkout), *arguments], check=True,
                          capture_output=True, timeout=60).stdout


def materialize(checkout, pin, destination):
    revision = pin["commit"]
    if git(checkout, "cat-file", "-t", revision).strip() != b"commit":
        raise ValueError("pinned object is not a commit")
    paths = {}
    for identity, entry in pin["dependencies"].items():
        source = entry["path"]
        if git(checkout, "rev-parse", f"{revision}:{source}").decode().strip() != entry["tree"]:
            raise ValueError(f"dependency tree pin mismatch: {identity}")
        target = destination / relative(identity)
        for row in git(checkout, "ls-tree", "-rz", revision, "--", source).split(b"\0"):
            if not row:
                continue
            metadata, raw_name = row.split(b"\t", 1)
            mode, kind, oid = metadata.split()
            if kind != b"blob" or mode not in (b"100644", b"100755"):
                raise ValueError("dependency tree contains a non-regular file")
            name = raw_name.decode()
            prefix = source + "/"
            if not name.startswith(prefix):
                raise ValueError("dependency object escaped its pinned tree")
            output = target / relative(name[len(prefix):])
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open("xb") as stream:
                stream.write(git(checkout, "cat-file", "blob", oid.decode()))
        paths[identity] = target
    return paths


def cli_environment():
    environment = dict(os.environ)
    environment.pop("SIGIL_ALLOW_UNVERIFIED_CERT", None)
    return environment


def checked(cli, *arguments):
    result = subprocess.run([cli, *arguments, "--json"], capture_output=True,
                            timeout=120, env=cli_environment())
    if result.returncode:
        raise ValueError("SIGIL refused pinned package operation: "
                         + (result.stderr or result.stdout).decode(errors="replace")[:2000])
    envelope = json.loads(result.stdout)
    if envelope.get("status") != "ok":
        raise ValueError("SIGIL package operation did not succeed")
    return envelope


def verify(cli, package=PACKAGE):
    result = checked(cli, "check", "--package", str(package))
    certificate = result["data"]["certificate"]
    if certificate.get("solver_verified") is not True:
        raise ValueError("a fresh solver-verified SIGIL CLI is required; no override is accepted")
    return certificate


def setup(cli, checkout):
    pin = load_pin()
    cache = PACKAGE / ".sigil"
    if cache.is_symlink():
        raise ValueError("dependency cache must not be a symlink")
    if cache.exists():
        # Existing state is checked, never re-locked or repaired in place.
        return verify(cli)
    with tempfile.TemporaryDirectory(prefix="autoresearch-pinned-") as directory:
        staging = Path(directory)
        providers = materialize(checkout, pin, staging / "providers")
        consumer = staging / "consumer"
        for name in pin["consumer_files"]:
            if name == "sigil-package.lock.json":
                continue
            output = consumer / relative(name)
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open("xb") as stream:
                stream.write(read_regular(PACKAGE, name))
        arguments = ["package-lock", "--root", str(consumer)]
        for identity, provider in sorted(providers.items()):
            arguments += ["--dependency", f"{identity}={provider}"]
        checked(cli, *arguments)
        if (json.loads(read_regular(consumer, "sigil-package.lock.json"))
                != json.loads(read_regular(PACKAGE, "sigil-package.lock.json"))):
            raise ValueError("derived lock differs from the committed pin; no automatic refresh")
        verify(cli, consumer)
        # copytree refuses an existing destination. A partial failed copy is
        # retained and will fail later validation, never silently replaced.
        shutil.copytree(consumer / ".sigil", cache)
    return verify(cli)


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("action", choices=("setup", "search"))
    parser.add_argument("--sigil", default="sigil", help="solver-enabled SIGIL executable")
    parser.add_argument("--sigil-checkout", type=Path, help="local checkout containing the pinned commit")
    args, forwarded = parser.parse_known_args()
    try:
        if args.action == "setup":
            if args.sigil_checkout is None or forwarded:
                raise ValueError("setup requires --sigil-checkout and accepts no search options")
            certificate = setup(args.sigil, args.sigil_checkout)
            print(json.dumps({"status": "ready", "source_commit": load_pin()["commit"],
                              "artifact_identity_hash": certificate["artifact_identity_hash"]}, indent=2))
            return 0
        if args.sigil_checkout is not None:
            raise ValueError("--sigil-checkout is only used for setup")
        allowed = {"--seed", "--stream", "--generations", "--steps", "--arm", "--budget",
                   "--transitions", "--evaluation", "--job-id", "--resume", "--out-dir", "--help"}
        for value in forwarded:
            if value.startswith("--") and value.split("=", 1)[0] not in allowed:
                raise ValueError("unsupported search option; package and storage overrides are disabled")
        load_pin()
        verify(args.sigil)
        return subprocess.run([sys.executable, str(PACKAGE / "search.py"), "--sigil", args.sigil,
                               "--package", str(PACKAGE), *forwarded], env=cli_environment()).returncode
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        print(f"library search refused: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
