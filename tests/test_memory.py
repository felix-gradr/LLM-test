import unittest
import tempfile
from pathlib import Path

import memory


class TestMemory(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        # Redirect MEMORY_FILE to a temp path
        memory.MEMORY_FILE = Path(self.tmp_dir.name) / "mem.jsonl"

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_add_and_load_memory(self):
        memory.add_memory("first")
        memory.add_memory("second")
        items = memory.load_memories(limit=None)
        self.assertEqual([it["content"] for it in items], ["first", "second"])
