import re
import zipfile
from io import BytesIO

MAX_FILES = 200
MAX_TOTAL_BYTES = 1024 * 1024 * 1024  # 1 GiB

_DIGIT_RUN = re.compile(r"(\d+)")


def _natural_sort_key(name: str) -> list:
    """"hour[2]" before "hour[10]" — plain string order puts "hour[10]"
    first (lexicographic: '1' < '2'), which is not how anyone reading
    task numbers expects them ordered. Splits on digit runs and compares
    those numerically, text parts case-insensitively.
    """
    parts = _DIGIT_RUN.split(name)
    return [int(part) if part.isdigit() else part.lower() for part in parts]


class BatchZipError(ValueError):
    pass


def read_mps_files(zip_bytes: bytes) -> list[tuple[str, bytes]]:
    """Extract *.mps entries from an uploaded zip, flattening directory
    paths to their basename. Raises BatchZipError on anything suspicious.
    """
    try:
        archive = zipfile.ZipFile(BytesIO(zip_bytes))
    except zipfile.BadZipFile as exc:
        raise BatchZipError("uploaded file is not a valid zip archive") from exc

    entries = [info for info in archive.infolist() if not info.is_dir()]
    mps_entries = [info for info in entries if info.filename.lower().endswith(".mps")]

    if not mps_entries:
        raise BatchZipError("zip archive contains no .mps files")
    if len(mps_entries) > MAX_FILES:
        raise BatchZipError(f"zip archive has more than {MAX_FILES} .mps files")

    total_bytes = sum(info.file_size for info in mps_entries)
    if total_bytes > MAX_TOTAL_BYTES:
        raise BatchZipError("zip archive contents exceed the size limit")

    files: list[tuple[str, bytes]] = []
    seen_names: set[str] = set()
    for info in mps_entries:
        name = info.filename.rsplit("/", 1)[-1]
        if name in seen_names:
            raise BatchZipError(f"duplicate filename in archive: {name}")
        seen_names.add(name)
        files.append((name, archive.read(info)))

    # Sort by natural (numeric-aware) filename order rather than the zip's
    # own raw entry order — many zip tools already write entries in plain
    # alphabetical order regardless of how the user actually thinks of the
    # sequence, which not only isn't necessarily the intended task order,
    # it also isn't numeric order: "hour[10]" sorts before "hour[2]"
    # lexicographically. batch_index/task numbering downstream (runner.py)
    # follows this order.
    files.sort(key=lambda item: _natural_sort_key(item[0]))
    return files
