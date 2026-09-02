import io
import zipfile

import pytest

from app.services.batches.zip_reader import BatchZipError, read_mps_files


def _zip_bytes(entries: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in entries.items():
            zf.writestr(name, content)
    return buf.getvalue()


def test_reads_mps_files_sorted_alphabetically():
    zip_bytes = _zip_bytes({"b.mps": b"B", "a.mps": b"A"})
    files = read_mps_files(zip_bytes)
    assert [name for name, _ in files] == ["a.mps", "b.mps"]
    assert dict(files) == {"a.mps": b"A", "b.mps": b"B"}


def test_reads_mps_files_sorted_numerically_not_lexicographically():
    # Plain string sort would put "hour[10]" and "hour[11]" right after
    # "hour[1]" (before "hour[2]") — batch_index/task numbering downstream
    # (runner.py) follows this order, so it needs to match how a human
    # reading the task numbers would expect them ordered.
    zip_bytes = _zip_bytes(
        {
            "hour[2]_task[1].mps": b"2",
            "hour[10]_task[1].mps": b"10",
            "hour[1]_task[1].mps": b"1",
        }
    )
    files = read_mps_files(zip_bytes)
    assert [name for name, _ in files] == [
        "hour[1]_task[1].mps",
        "hour[2]_task[1].mps",
        "hour[10]_task[1].mps",
    ]


def test_ignores_non_mps_entries():
    zip_bytes = _zip_bytes({"a.mps": b"A", "readme.txt": b"hi"})
    files = read_mps_files(zip_bytes)
    assert [name for name, _ in files] == ["a.mps"]


def test_flattens_directory_paths():
    zip_bytes = _zip_bytes({"nested/dir/a.mps": b"A"})
    files = read_mps_files(zip_bytes)
    assert files == [("a.mps", b"A")]


def test_rejects_non_zip_bytes():
    with pytest.raises(BatchZipError):
        read_mps_files(b"not a zip file")


def test_rejects_zip_with_no_mps_files():
    zip_bytes = _zip_bytes({"readme.txt": b"hi"})
    with pytest.raises(BatchZipError):
        read_mps_files(zip_bytes)


def test_rejects_duplicate_filenames_after_flattening():
    zip_bytes = _zip_bytes({"a/dup.mps": b"A", "b/dup.mps": b"B"})
    with pytest.raises(BatchZipError):
        read_mps_files(zip_bytes)


def test_rejects_too_many_files(monkeypatch):
    monkeypatch.setattr("app.services.batches.zip_reader.MAX_FILES", 2)
    zip_bytes = _zip_bytes({"a.mps": b"A", "b.mps": b"B", "c.mps": b"C"})
    with pytest.raises(BatchZipError):
        read_mps_files(zip_bytes)


def test_rejects_total_size_over_limit(monkeypatch):
    monkeypatch.setattr("app.services.batches.zip_reader.MAX_TOTAL_BYTES", 5)
    zip_bytes = _zip_bytes({"a.mps": b"0123456789"})
    with pytest.raises(BatchZipError):
        read_mps_files(zip_bytes)
