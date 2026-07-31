from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "autopoietic_forms", ROOT / "domains" / "autopoiesis" / "forms.py"
)
forms = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(forms)


class FormCalculusTests(unittest.TestCase):
    def test_calling_collapses_repeated_mark(self):
        self.assertEqual(forms.normalize([forms.mark(), forms.mark()]), [forms.mark()])

    def test_crossing_cancels_double_mark(self):
        self.assertEqual(forms.normalize([forms.mark([forms.mark()])]), [])
        self.assertEqual(forms.indication([forms.mark([forms.mark()])]), "unmarked")

    def test_distinction_indicates_one_side(self):
        value = forms.distinction("system", "environment", "marked")
        self.assertEqual(value["value"], "marked")
        self.assertNotEqual(value["marked"], value["unmarked"])

    def test_reentry_preserves_source_and_entry_side(self):
        source = {"id": "form-1", **forms.distinction("self", "other", "marked")}
        value = forms.reentry(source, "marked")
        self.assertEqual(value["reentry"], {"source": "form-1", "side": "marked"})


if __name__ == "__main__":
    unittest.main()
