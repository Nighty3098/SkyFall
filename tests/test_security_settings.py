import json
import unittest
from unittest.mock import patch

from cryptography.fernet import Fernet

from src import security


class SensitiveSettingsEncryptionTest(unittest.TestCase):
    def test_all_stored_credentials_are_encrypted_and_reloaded(self):
        credentials = {
            "tg_api_key": "telegram-secret",
            "telegram_api_hash": "telegram-hash",
            "telegram_phone": "+15550000000",
            "intelligent_x_api_key": "intelx-secret",
            "hibp_api_key": "hibp-secret",
            "virustotal_api_key": "vt-secret",
            "google_safe_api_key": "google-secret",
            "ipinfo_api_key": "ipinfo-secret",
            "github_token": "github-secret",
            "numverify_api_key": "numverify-secret",
            "abstractapi_api_key": "abstract-secret",
            "trongrid_api_key": "trongrid-secret",
            "etherscan_api_key": "etherscan-secret",
            "bscscan_api_key": "bscscan-secret",
            "tonapi_api_key": "tonapi-secret",
            "helius_api_key": "helius-secret",
            "abuseipdb_api_key": "abuseipdb-secret",
            "greynoise_api_key": "greynoise-secret",
            "leakcheck_api_key": "leakcheck-secret",
            "dehashed_email": "analyst@example.test",
            "dehashed_api_key": "dehashed-secret",
            "firms_map_key": "firms-secret",
            "reddit_client_id": "reddit-id",
            "reddit_client_secret": "reddit-secret",
        }
        fernet = Fernet(Fernet.generate_key())

        with patch.object(security, "_get_fernet", return_value=fernet):
            encrypted = security.encrypt_settings(credentials)
            restored = security.decrypt_settings(encrypted)

        self.assertEqual(restored, credentials)
        self.assertTrue(all(key in security.SENSITIVE_KEYS for key in credentials))
        serialized = json.dumps(encrypted)
        for value in credentials.values():
            self.assertNotIn(value, serialized)
        for key in credentials:
            self.assertTrue(encrypted[key].startswith(security.ENC_PREFIX))

    def test_encryption_failure_raises_instead_of_returning_plaintext(self):
        with patch.object(
            security,
            "_get_fernet",
            side_effect=security.SettingsEncryptionError("encryption unavailable"),
        ):
            with self.assertRaises(security.SettingsEncryptionError):
                security.encrypt_settings({"github_token": "must-not-leak"})


if __name__ == "__main__":
    unittest.main()
