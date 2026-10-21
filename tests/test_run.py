import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import reviewer
import run

ROOT = Path(__file__).parent.parent


class ReproducibilityTest(unittest.TestCase):
    def test_committed_report_reproduces_from_cache_without_api_key(self):
        out = Path(tempfile.mkdtemp())
        env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}

        # Solo cache: si faltara una respuesta, el test falla en vez de llamar al modelo.
        with mock.patch.dict(os.environ, env, clear=True), \
                mock.patch.object(reviewer, "call_model", side_effect=reviewer.Unavailable("not cached")):
            run.main(ROOT / "data" / "transactions.json", out)

        report = (out / "report.md").read_text()
        self.assertIn("Chunks not reviewed: 0.", report.splitlines()[3])
        self.assertEqual(report, (ROOT / "output" / "report.md").read_text())
