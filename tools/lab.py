#!/usr/bin/env python3
"""Reproduce protocol checks and summarize bounded native-loader experiments."""
import argparse
import json
import os
from pathlib import Path
import subprocess
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
               "org.microg.gms.wallet.WebPaymentWireTest"]
    subprocess.run(command, cwd=checkout, env=env, check=True)
    report = checkout / "play-services-api/build/test-results/testDebugUnitTest/TEST-org.microg.gms.wallet.WebPaymentWireTest.xml"
    suite = ET.parse(report).getroot()
    summary = {k: suite.attrib[k] for k in ("name", "tests", "failures", "errors", "skipped", "time")}
    if int(summary["tests"]) < 5 or any(int(summary[k]) for k in ("failures", "errors", "skipped")):
        raise ValueError("Protocol suite did not pass every required test")
    target = ROOT / "verification"
    target.mkdir(exist_ok=True)
    (target / report.name).write_bytes(report.read_bytes())
    (target / "protocol-test-result.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


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
