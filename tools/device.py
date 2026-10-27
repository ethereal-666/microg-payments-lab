#!/usr/bin/env python3
"""Install only isolated lab apps and run reproducible Android instrumentation."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SCOPE = "oauth2:https://www.googleapis.com/auth/sierra"
EVENTS = {"token_acquired", "authenticator_error", "access_denied", "io_error",
          "interactive_authorization_required", "cancelled", "no_token",
          "empty_authenticator_response", "invalid_account_selection", "unexpected_error",
          "no_visible_account", "multiple_visible_accounts"}
IO_HINTS = {"UnknownHostException", "SocketTimeoutException", "ConnectException",
            "SSLHandshakeException", "SSLPeerUnverifiedException", "NotOkayException"}
AUTH_HINTS = {"BadAuthentication", "NeedsBrowser", "NeedsPermission", "ServiceDisabled",
              "SERVICE_DISABLED", "SERVICE_UNAVAILABLE", "ScopeLimitExceeded", "AccessDenied",
              "UNREGISTERED_ON_API_CONSOLE", "INVALID_SCOPE", "InvalidScope", "BadRequest",
              "InvalidValue", "Unknown"}


def checked_observation(result):
    allowed = {"event", "scope", "token_exposed", "payment_attempted", "error_code", "io_hint", "auth_error_hint"}
    if not isinstance(result, dict) or set(result) - allowed:
        raise ValueError("Unexpected fields in diagnostic; refusing to save it")
    if result.get("event") not in EVENTS or result.get("scope") != SCOPE:
        raise ValueError("Unexpected event or scope")
    if result.get("token_exposed") is not False or result.get("payment_attempted") is not False:
        raise ValueError("Diagnostic privacy/payment contract failed")
    if "io_hint" in result and result["io_hint"] not in IO_HINTS:
        raise ValueError("Unexpected transport hint")
    if "auth_error_hint" in result and result["auth_error_hint"] not in AUTH_HINTS:
        raise ValueError("Unexpected authentication hint")
    if "error_code" in result and type(result["error_code"]) is not int:
        raise ValueError("Non-numeric error code")
    return result


def parse_run(output, expected_tests, auth=False):
    # `adb shell am instrument` can exit zero even when tests fail.
    summary = re.search(r"^OK \((\d+) tests?\)\s*$", output, re.M)
    if not summary or int(summary[1]) != expected_tests or re.search(r"FAILURES!!!|INSTRUMENTATION_FAILED|shortMsg=|Process crashed", output):
        raise ValueError("Instrumentation did not complete every expected test; raw output was not published")
    result = {"instrumentation_tests": expected_tests, "observation_completed": True, "payment_verified": False}
    if auth:
        values = re.findall(r"^INSTRUMENTATION_STATUS: diagnostic=(.+)$", output, re.M)
        if len(values) != 1:
            raise ValueError("Missing or ambiguous authentication observation")
        observation = checked_observation(json.loads(values[0]))
        result.update(authorization_succeeded=observation["event"] == "token_acquired", diagnostic=observation)
    return result


def run(serial, adb, mode):
    module, package, tests = (("wallet-web-harness", "org.microg.wallet.lab", 3) if mode == "native"
                              else ("wallet-auth-probe", "org.microg.wallet.authprobe", 1))
    folder = ROOT / "GmsCore" / module / "build/outputs/apk"
    apks = [folder / "debug" / (module + "-debug.apk"),
            folder / "androidTest/debug" / (module + "-debug-androidTest.apk")]
    if not all(path.is_file() for path in apks):
        raise ValueError("Build the lab app and its assembleDebugAndroidTest target first")
    command = [str(adb), "-s", serial]
    subprocess.run(command + ["get-state"], check=True, capture_output=True, text=True, timeout=15)
    for path in apks:
        installed = subprocess.run(command + ["install", "-r", str(path)], check=True,
                                   capture_output=True, text=True, timeout=60)
        if "Success" not in installed.stdout:
            raise ValueError("Lab APK install was not confirmed")
    # Remove only lab-owned activities left by a previously interrupted runner.
    for target in (package, package + ".test"):
        subprocess.run(command + ["shell", "am", "force-stop", target], check=True,
                       capture_output=True, text=True, timeout=15)
    output = subprocess.run(command + ["shell", "am", "instrument", "-w", "-r",
                            package + ".test/androidx.test.runner.AndroidJUnitRunner"],
                            check=True, capture_output=True, text=True, timeout=90).stdout
    result = parse_run(output, tests, auth=mode == "auth")
    result.update(verified_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  app_package=package, installed_app_sha256=hashlib.sha256(apks[0].read_bytes()).hexdigest(),
                  installed_test_sha256=hashlib.sha256(apks[1].read_bytes()).hexdigest())
    if mode == "native":
        result.update(scope="Separate-process OwServiceImpl Binder 17, callback 12 and native error/cancel/back Activity results; no Google backend",
                      cases={"error_return": {"activity_result": 1, "status": 17},
                             "cancel_button": {"activity_result": 0, "status": 16},
                             "system_back": {"activity_result": 0, "status": 16}})
    else:
        result["scope"] = "Only the single account already visible to the probe; no new grant approved and no UI automated"
    destination = ROOT / "verification" / ("device-native-remote.json" if mode == "native" else "device-auth-noninteractive.json")
    destination.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["native", "auth"])
    parser.add_argument("--serial", required=True, help="Explicit authorized ADB serial (not saved in reports)")
    parser.add_argument("--adb", type=Path, default=ROOT / "android-sdk/platform-tools/adb")
    args = parser.parse_args()
    try:
        print(json.dumps(run(args.serial, args.adb, args.mode), ensure_ascii=False, indent=2))
        return 0
    except ValueError as failure:
        print("Device verification failed: " + str(failure), file=sys.stderr)
        return 1
    except (OSError, subprocess.SubprocessError) as failure:
        print("Device verification did not complete (" + type(failure).__name__ + "); no success result was recorded", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
