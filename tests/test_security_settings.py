import json
import os
import stat
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
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
            "shodan_api_key": "shodan-secret",
            "numverify_api_key": "numverify-secret",
            "abstractapi_api_key": "abstract-secret",
            "trongrid_api_key": "trongrid-secret",
            "etherscan_api_key": "etherscan-secret",
            "bscscan_api_key": "bscscan-secret",
            "tonapi_api_key": "tonapi-secret",
            "helius_api_key": "helius-secret",
            "abuseipdb_api_key": "abuseipdb-secret",
            "greynoise_api_key": "greynoise-secret",
            "whoisfreaks_api_key": "whoisfreaks-secret",
            "ipgeolocation_api_key": "ipgeolocation-secret",
            "ip2locationio_api_key": "ip2locationio-secret",
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

    def test_concurrent_token_creation_returns_one_private_token(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            with patch.object(security, "CONFIG_DIR", config_dir):
                with ThreadPoolExecutor(max_workers=12) as executor:
                    tokens = list(
                        executor.map(
                            lambda _: security.get_or_create_token(), range(48)
                        )
                    )

            self.assertEqual(len(set(tokens)), 1)
            token_file = config_dir / "mcp_token"
            self.assertEqual(token_file.read_text(encoding="utf-8"), tokens[0])
            self.assertEqual(stat.S_IMODE(token_file.stat().st_mode), 0o600)

    def test_concurrent_key_creation_returns_one_fernet_key(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            key_file = config_dir / "secret.key"
            original_fernet, original_ready = security._fernet, security._fernet_ready
            security._fernet = None
            security._fernet_ready = False
            try:
                with (
                    patch.object(security, "CONFIG_DIR", config_dir),
                    patch.object(security, "KEY_FILE", key_file),
                ):
                    with ThreadPoolExecutor(max_workers=12) as executor:
                        futures = [
                            executor.submit(security._get_fernet) for _ in range(48)
                        ]
                        fernets = [future.result() for future in futures]

                self.assertEqual(len({id(fernet) for fernet in fernets}), 1)
                self.assertEqual(stat.S_IMODE(key_file.stat().st_mode), 0o600)
            finally:
                security._fernet = original_fernet
                security._fernet_ready = original_ready

    def test_existing_token_permissions_are_repaired(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            token_file = config_dir / "mcp_token"
            token_file.write_text("existing-token", encoding="utf-8")
            os.chmod(token_file, 0o644)

            with patch.object(security, "CONFIG_DIR", config_dir):
                token = security.get_or_create_token()

            self.assertEqual(token, "existing-token")
            self.assertEqual(stat.S_IMODE(token_file.stat().st_mode), 0o600)


if __name__ == "__main__":
    unittest.main()
