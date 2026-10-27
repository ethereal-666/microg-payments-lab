#!/usr/bin/env python3
"""Prepare the pinned microG checkout without resetting existing work."""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def git(checkout, *args, check=True):
    return subprocess.run(["git", "-C", str(checkout), *args], check=check,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def prepare(checkout, project_root=ROOT, sdk=None):
    config = json.loads((project_root / "project.json").read_text())["upstream"]
    patch = project_root / "patches/0001-wallet-web-protocol-foundation.patch"
    patch_text = patch.read_text()
    checkout = checkout.resolve()
    sdk = sdk.resolve() if sdk else None
    if sdk:
        for required in ["platforms/android-35/android.jar", "build-tools/35.0.0/aidl"]:
            if not (sdk / required).is_file():
                raise ValueError("Android SDK component missing: " + str(sdk / required))

    if checkout.exists():
        top = git(checkout, "rev-parse", "--show-toplevel").stdout.strip()
        if Path(top).resolve() != checkout:
            raise ValueError("Destination is not a standalone upstream checkout")
    else:
        checkout.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "--depth", "1", "--branch", config["ref"],
                        config["url"], str(checkout)], check=True)

    head = git(checkout, "rev-parse", "HEAD").stdout.strip()
    if head != config["commit"]:
        raise ValueError("Unexpected upstream revision; existing checkout left unchanged: " + head)
    status = git(checkout, "status", "--porcelain").stdout
    already_applied = git(checkout, "apply", "--reverse", "--check", str(patch), check=False).returncode == 0
    if already_applied:
        # The patch may apply in reverse even when unrelated user edits exist.
        # Reuse only the exact intended diff, and never reset any edits.
        # Canonical add/delete form also covers sources moved across modules.
        difference = git(checkout, "diff", "--binary", "--no-renames", "HEAD").stdout
        untracked = git(checkout, "ls-files", "--others", "--exclude-standard").stdout
        if difference != patch_text or untracked:
            raise ValueError("Additional checkout changes found; preserving them without modification")
        state = "already_applied"
    else:
        if status:
            raise ValueError("Checkout has existing changes; preserving them without modification")
        git(checkout, "apply", "--check", str(patch))
        git(checkout, "apply", "--intent-to-add", str(patch))
        state = "applied"
    git(checkout, "diff", "--check")

    if sdk:
        properties = checkout / "local.properties"
        lines = properties.read_text().splitlines() if properties.exists() else []
        lines = [line for line in lines if not line.lstrip().startswith("sdk.dir=")]
        # Java properties treats backslashes as escapes; preserve literal paths.
        sdk_path = str(sdk).replace("\\", "\\\\").replace(":", "\\:")
        properties.write_text("\n".join(lines + ["sdk.dir=" + sdk_path]) + "\n")
    return {"checkout": str(checkout), "upstream_commit": head, "patch": state,
            "sdk_configured": sdk is not None, "payment_working": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", type=Path, default=ROOT / "GmsCore")
    parser.add_argument("--sdk", type=Path, help="Existing Android SDK with Platform 35 and Build Tools 35.0.0")
    args = parser.parse_args()
    try:
        print(json.dumps(prepare(args.checkout, sdk=args.sdk), indent=2))
        return 0
    except (OSError, ValueError, subprocess.CalledProcessError) as failure:
        print(str(failure), file=sys.stderr)
        if isinstance(failure, subprocess.CalledProcessError) and failure.stderr:
            print(failure.stderr, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
