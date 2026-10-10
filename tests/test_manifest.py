import tempfile
import unittest
from pathlib import Path
import json
from narrative.run import run


class ManifestTests(unittest.TestCase):
    def test_run_has_reproducibility_metadata_without_credentials(self):
        with tempfile.TemporaryDirectory() as folder:
            out=Path(folder)
            run(output=out,steps=1)
            manifest=json.loads((out/'manifest.json').read_text(encoding='utf-8'))
            self.assertEqual(manifest['mode'],'scripted')
            self.assertEqual(len(manifest['initial_sha256']),64)
            self.assertIn('core.py',manifest['code_sha256'])
            self.assertNotIn('api_key',json.dumps(manifest).lower())
