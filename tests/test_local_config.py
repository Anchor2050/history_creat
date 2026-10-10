import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from narrative.providers import read_local_config


class LocalConfigTests(unittest.TestCase):
    def test_local_values_without_environment_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / '.env'
            path.write_text('# local only\nDEEPSEEK_API_KEY=test-local\nDEEPSEEK_MODEL="test-model"\n', encoding='utf-8-sig')
            with patch.dict(os.environ, {}, clear=True):
                values = read_local_config(path)
                self.assertEqual(values['DEEPSEEK_API_KEY'], 'test-local')
                self.assertEqual(values['DEEPSEEK_MODEL'], 'test-model')
                self.assertNotIn('DEEPSEEK_API_KEY', os.environ)

    def test_missing_file_is_optional(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(read_local_config(Path(directory) / '.env'), {})

    def test_explicit_and_environment_settings_override_local(self):
        from narrative.providers import DeepSeek
        with patch('narrative.providers.read_local_config', return_value={
                'DEEPSEEK_API_KEY': 'local', 'DEEPSEEK_MODEL': 'local-model'}):
            with patch.dict(os.environ, {'DEEPSEEK_API_KEY': 'environment'}, clear=True):
                self.assertEqual(DeepSeek().api_key, 'environment')
                self.assertEqual(DeepSeek('explicit').api_key, 'explicit')
                self.assertEqual(DeepSeek().model, 'local-model')
