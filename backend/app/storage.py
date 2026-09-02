from app.config import settings


def init_storage() -> None:
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    settings.results_dir.mkdir(parents=True, exist_ok=True)
    settings.logs_dir.mkdir(parents=True, exist_ok=True)
    settings.qore_versions_dir.mkdir(parents=True, exist_ok=True)
