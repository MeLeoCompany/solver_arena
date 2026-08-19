from alembic import command
from alembic.config import Config

from app.config import settings


def run_migrations() -> None:
    config = Config(str(settings.alembic_ini_path))
    config.set_main_option("script_location", str(settings.migrations_dir))
    config.set_main_option("sqlalchemy.url", settings.database_url)
    command.upgrade(config, "head")
