import zipfile
from io import BytesIO

MAX_FILES = 200
MAX_TOTAL_BYTES = 200 * 1024 * 1024


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

    files.sort(key=lambda item: item[0])
    return files
