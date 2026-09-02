import platform
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent

_CPLEX_ENGINE_DIR = PROJECT_ROOT / "engines" / "cplex"
_DEFAULT_CPLEX_LIBRARY_PATH = (
    _CPLEX_ENGINE_DIR / "cplex1261.dll"
    if platform.system() == "Windows"
    else _CPLEX_ENGINE_DIR / "libcplex1261.so"
)

_QORE_ENGINE_DIR = PROJECT_ROOT / "engines" / "qore"  # vendored .so + license only
_QORE_SOLVERS_DIR = PROJECT_ROOT / "app" / "solvers" / "qore"  # our own scripts
# QORE's Python bindings are built for CPython 3.8's ABI and only load
# under that exact interpreter — not the app's own (3.13) venv. Installed
# via `uv python install 3.8`; override if it lives somewhere else.
_DEFAULT_QORE_PYTHON_EXECUTABLE = (
    Path.home() / ".local" / "share" / "uv" / "python" / "cpython-3.8-linux-x86_64-gnu" / "bin" / "python3.8"
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SOLVER_SERVER_", env_file=".env")

    data_dir: Path = PROJECT_ROOT / "data"
    database_url: str = "sqlite:///data/jobs.db"
    alembic_ini_path: Path = PROJECT_ROOT / "alembic.ini"
    migrations_dir: Path = PROJECT_ROOT / "migrations"

    log_hub_finished_ttl_sec: int = 6 * 3600
    cancel_grace_period_sec: float = 5.0

    session_cookie_name: str = "session_id"
    session_ttl_sec: int = 30 * 24 * 3600
    session_cookie_secure: bool = False

    api_token_ttl_sec: int = 90 * 24 * 3600

    admin_username: str | None = None
    admin_password: str | None = None

    log_level: str = "INFO"
    app_log_max_bytes: int = 10 * 1024 * 1024
    app_log_backup_count: int = 5

    cplex_library_path: Path = _DEFAULT_CPLEX_LIBRARY_PATH
    alglib_engine_dir: Path = PROJECT_ROOT / "engines" / "alglib"

    qore_engine_dir: Path = _QORE_ENGINE_DIR
    qore_python_executable: Path = _DEFAULT_QORE_PYTHON_EXECUTABLE
    qore_license_file: Path = _QORE_ENGINE_DIR / "license" / "License.json"
    qore_check_script: Path = _QORE_SOLVERS_DIR / "qore_check.py"
    qore_solve_script: Path = _QORE_SOLVERS_DIR / "qore_solve.py"
    qore_stubgen_script: Path = _QORE_SOLVERS_DIR / "qore_stubgen.py"

    availability_check_timeout_sec: float = 30.0

    @property
    def uploads_dir(self) -> Path:
        return self.data_dir / "uploads"

    @property
    def results_dir(self) -> Path:
        return self.data_dir / "results"

    @property
    def logs_dir(self) -> Path:
        """Логи солверов — per-job .log файлы, см. app/services/logs/."""
        return self.data_dir / "logs"

    @property
    def app_log_dir(self) -> Path:
        """Логи самого сервиса (не солверов) — см. app/logging_setup.py."""
        return PROJECT_ROOT / "logs"

    @property
    def qore_versions_dir(self) -> Path:
        """История загруженных QORE .so — под data/, переживает пересоздание
        контейнера (см. app/services/qore_versions/)."""
        return self.data_dir / "qore_versions"


settings = Settings()
