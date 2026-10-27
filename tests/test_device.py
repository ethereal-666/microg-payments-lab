import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("device", Path(__file__).resolve().parents[1] / "tools/device.py")
device = importlib.util.module_from_spec(spec)
spec.loader.exec_module(device)


class DeviceResultTest(unittest.TestCase):
    def test_android_zero_exit_is_not_proof_of_passing_tests(self):
        with self.assertRaises(ValueError):
            device.parse_run("FAILURES!!!\nTests run: 3, Failures: 1\nINSTRUMENTATION_CODE: -1\n", 3)

    def test_incomplete_suite_is_not_success(self):
        with self.assertRaises(ValueError):
            device.parse_run("OK (2 tests)\n", 3)

    def test_observation_pass_does_not_mean_authorization_success(self):
        output = 'INSTRUMENTATION_STATUS: diagnostic={"event":"io_error","scope":"oauth2:https://www.googleapis.com/auth/sierra","token_exposed":false,"payment_attempted":false,"auth_error_hint":"INVALID_SCOPE"}\nOK (1 test)\n'
        result = device.parse_run(output, 1, auth=True)
        self.assertTrue(result["observation_completed"])
        self.assertFalse(result["authorization_succeeded"])
        self.assertFalse(result["payment_verified"])

    def test_report_rejects_unexpected_private_data(self):
        value = dict(event="no_token", scope=device.SCOPE, token_exposed=False, payment_attempted=False,
                     account="synthetic@example.invalid")
        with self.assertRaises(ValueError):
            device.checked_observation(value)

    def test_arbitrary_error_hint_is_not_saved(self):
        value = dict(event="io_error", scope=device.SCOPE, token_exposed=False, payment_attempted=False,
                     auth_error_hint="synthetic-private-value")
        with self.assertRaises(ValueError):
            device.checked_observation(value)
