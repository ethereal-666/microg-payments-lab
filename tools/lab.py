#!/usr/bin/env python3
"""Reproduce protocol checks and summarize bounded native-loader experiments."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import shutil
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def probe_summary(path):
    lines = path.read_text().splitlines()
    sessions = []
    current = None
    for line in lines:
        if line.startswith("HOST "):
            current = []
            sessions.append(current)
        if current is not None:
            current.append(line)
    if not sessions:
        raise ValueError("No HOST marker: this is not a completed native probe trace")
    lines = sessions[-1]
    joined = "\n".join(lines)
    stage = "unknown"
    if "CONSTRUCT_FAIL " in joined:
        stage = "chimera_module_manager" if "ModuleManager" in joined else "service_construction"
    elif "SERVICE_INIT_FAIL " in joined:
        stage = "service_initialization"
    elif "BIND_RESULT " in joined:
        stage = "broker_binding_only"
    elif "LINK_FAIL " in joined:
        stage = "class_linkage"
    return {
        "source": path.name,
        "sessions": len(sessions),
        "last_probe_finished": any(x.startswith("PROBE_DONE") for x in lines),
        "native_context_initialized": any(x.startswith("BASE_CONTEXT_OK") for x in lines),
        "linked_classes": [x.split()[1] for x in lines if x.startswith("LINK_OK ")],
        "stage": stage,
        "payment_verified": False,
        "interpretation": "Native class/runtime probe only; no wallet payment request was exercised"
    }


def verify(checkout, java_home):
    checkout = checkout.resolve()
    env = dict(os.environ)
    if java_home:
        env["JAVA_HOME"] = str(java_home.resolve())
    command = [str(checkout / "gradlew"), "--no-daemon", "--no-configuration-cache",
               ":play-services-api:testDebugUnitTest", "--tests",
               "org.microg.gms.wallet.WebPaymentWireTest",
               ":wallet-web-core:testDebugUnitTest", ":wallet-auth-probe:testDebugUnitTest",
               ":play-services-base-core:testDebugUnitTest",
               ":wallet-web-harness:assembleDebug", ":wallet-auth-probe:assembleDebug",
               ":wallet-web-harness:assembleDebugAndroidTest", ":wallet-auth-probe:assembleDebugAndroidTest"]
    subprocess.run(command, cwd=checkout, env=env, check=True)
    target = ROOT / "verification"
    target.mkdir(exist_ok=True)
    summaries = {}
    suites = [("protocol", "play-services-api", "org.microg.gms.wallet.WebPaymentWireTest", 5),
              ("native_flow", "wallet-web-core", "org.microg.gms.wallet.web.WebPaymentBridgeTest", 13),
              ("auth_diagnostics", "wallet-auth-probe", "org.microg.wallet.authprobe.AuthProbeReportTest", 8),
              ("buyflow_probe", "wallet-auth-probe", "org.microg.wallet.authprobe.BuyflowSandboxProbeTest", 4),
              ("auth_privacy", "play-services-base/core", "org.microg.gms.auth.AuthPrivacyTest", 2)]
    for name, module, test_class, minimum in suites:
        report = checkout / module / "build/test-results/testDebugUnitTest" / ("TEST-" + test_class + ".xml")
        suite = ET.parse(report).getroot()
        summary = {k: suite.attrib[k] for k in ("name", "tests", "failures", "errors", "skipped", "time")}
        if int(summary["tests"]) < minimum or any(int(summary[k]) for k in ("failures", "errors", "skipped")):
            raise ValueError(name + " suite did not pass every required test")
        (target / report.name).write_bytes(report.read_bytes())
        summaries[name] = summary
    (target / "protocol-test-result.json").write_text(json.dumps(summaries["protocol"], indent=2) + "\n")
    artifact_dir = ROOT / "artifacts"
    artifact_dir.mkdir(exist_ok=True)
    artifacts = []
    for module in ("wallet-web-harness", "wallet-auth-probe"):
        folder = checkout / module / "build/outputs/apk/debug"
        metadata = json.loads((folder / "output-metadata.json").read_text())
        apk = folder / metadata["elements"][0]["outputFile"]
        destination = artifact_dir / apk.name
        shutil.copy2(apk, destination)
        artifacts.append({"path": str(destination.relative_to(ROOT)),
                          "application_id": metadata["applicationId"],
                          "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
                          "bytes": destination.stat().st_size})
    (target / "artifacts.json").write_text(json.dumps(artifacts, indent=2) + "\n")
    result = {"suites": summaries, "total_tests": sum(int(x["tests"]) for x in summaries.values()),
              "payment_verified": False, "scope": "Unit tests and APK builds; device evidence is recorded separately"}
    (target / "native-flow-result.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("status")
    probe = commands.add_parser("probe-summary")
    probe.add_argument("trace", type=Path)
    check = commands.add_parser("verify")
    check.add_argument("--gmscore", type=Path, default=ROOT / "GmsCore")
    check.add_argument("--java-home", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "status":
            result = json.loads((ROOT / "project.json").read_text())
        elif args.command == "probe-summary":
            result = probe_summary(args.trace)
        else:
            result = verify(args.gmscore, args.java_home)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    except (OSError, ValueError, ET.ParseError, subprocess.CalledProcessError) as failure:
        print(str(failure), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
