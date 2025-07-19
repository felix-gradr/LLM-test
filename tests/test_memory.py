import unittest
import tempfile
from pathlib import Path

import memory

# Store the original path
_ORIGINAL_MEMORY_FILE = memory.MEMORY_FILE


class TestMemory(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        # Redirect MEMORY_FILE to a temp path
        memory.MEMORY_FILE = Path(self.tmp_dir.name) / "memory.jsonl"

    def tearDown(self):
        self.tmp_dir.cleanup()
        # Restore the original path after tests
        memory.MEMORY_FILE = _ORIGINAL_MEMORY_FILE

    def _read_lines(self):
        return self.file_path.read_text(encoding="utf-8").splitlines()

    def test_add_and_load_memory(self):
        memory.add_memory("first")
        memory.add_memory("second")
        items = memory.load_memories(limit=None)
        self.assertEqual([it["content"] for it in items], ["first", "second"])
