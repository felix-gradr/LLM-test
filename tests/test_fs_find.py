from pathlib import Path

from tools.fs_find import fs_find


def test_fs_find_by_filename(tmp_path: Path):
    # Create sample files
    (tmp_path / "foo.txt").write_text("hello world")
    (tmp_path / "bar.py").write_text("print('hi')")

    matches = fs_find("foo", root=tmp_path, include_content=False)
    assert any(m["path"].endswith("foo.txt") for m in matches)


def test_fs_find_by_content(tmp_path: Path):
    (tmp_path / "alpha.txt").write_text("The quick brown fox")
    matches = fs_find("brown fox", root=tmp_path, include_content=False)
    assert matches and matches[0]["path"].endswith("alpha.txt")


def test_fs_find_case_insensitive(tmp_path: Path):
    (tmp_path / "Caps.txt").write_text("MiXeD CaSe")
    assert fs_find("mixed case", root=tmp_path)
    assert not fs_find("mixed case", root=tmp_path, case_sensitive=True)