import unittest
import tempfile
from pathlib import Path

import file_editor


class TestFileEditor(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.file_path = Path(self.tmp_dir.name) / "sample.txt"

    def tearDown(self):
        self.tmp_dir.cleanup()

    def _read_lines(self):
        return self.file_path.read_text(encoding="utf-8").splitlines()

    def test_insert_after(self):
        self.file_path.write_text("a\nanchor\nc\n", encoding="utf-8")
        mutated = file_editor.insert_after(self.file_path, "anchor", "b")
        self.assertTrue(mutated)
        self.assertEqual(self._read_lines(), ["a", "anchor", "b", "c"])

    def test_replace_block(self):
        content = "start\nKEEP\nEND\n"
        self.file_path.write_text(content, encoding="utf-8")
        mutated = file_editor.replace_block(
            self.file_path,
            "start",
            "END",
            "NEW",
            include_markers=False,
        )
        self.assertTrue(mutated)
        self.assertEqual(self._read_lines(), ["start", "NEW", "END"])

    def test_ensure_line(self):
        self.file_path.write_text("", encoding="utf-8")
        added_first = file_editor.ensure_line(self.file_path, "hello")
        added_second = file_editor.ensure_line(self.file_path, "hello")
        self.assertTrue(added_first)
        self.assertFalse(added_second)
        self.assertEqual(self._read_lines(), ["hello"])
