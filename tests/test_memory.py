from memory import Memory
from pathlib import Path
import json, os

def test_memory_append_and_load(tmp_path):
    mem_path = tmp_path / "mem.jsonl"
    m = Memory(mem_path, max_retained=10)
    m.append({"foo": "bar"})
    m.append({"num": 1})
    loaded = m.load()
    assert len(loaded) == 2
    assert loaded[-1]["num"] == 1
