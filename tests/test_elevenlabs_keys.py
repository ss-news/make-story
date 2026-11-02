import os
import unittest
from unittest import mock

from storyvid import elevenlabs


class KeyRotationTest(unittest.TestCase):
    def setUp(self):
        elevenlabs._spent.clear()
        env = {"ELEVENLABS_API_KEY": "main", "ELEVENLABS_EXTRA_KEYS": "second, third,main"}
        patcher = mock.patch.dict(os.environ, env)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(elevenlabs._spent.clear)

    def test_keys_are_the_main_one_then_the_extra_ones(self):
        self.assertEqual(elevenlabs.api_keys(), ["main", "second", "third"])

    def test_synthesis_moves_on_when_a_quota_runs_out_and_remembers_it(self):
        used = []

        def send(path, body, key):
            used.append(key)
            if key == "main":
                raise elevenlabs.QuotaError("quota_exceeded")
            return {"ok": key}

        with mock.patch.object(elevenlabs, "_send", side_effect=send):
            self.assertEqual(elevenlabs._request("/tts", {}, rotate=True), {"ok": "second"})
            self.assertEqual(elevenlabs._request("/tts", {}, rotate=True), {"ok": "second"})
        self.assertEqual(used, ["main", "second", "second"])

    def test_every_key_spent_is_a_quota_error_and_listing_uses_the_main_key(self):
        def send(path, body, key):
            raise elevenlabs.QuotaError("quota_exceeded")

        with mock.patch.object(elevenlabs, "_send", side_effect=send):
            with self.assertRaisesRegex(elevenlabs.QuotaError, r"Every ElevenLabs key \(3\)"):
                elevenlabs._request("/tts", {}, rotate=True)
        with mock.patch.object(elevenlabs, "_send", return_value={}) as send:
            elevenlabs._request("/voices")
        self.assertEqual(send.call_args.args[2], "main")


if __name__ == "__main__":
    unittest.main()
