import logging
import logging.handlers
import multiprocessing as mp
import sys

from app.config import settings

_FORMAT = "%(asctime)s %(processName)s [%(levelname)s] %(name)s: %(message)s"

_mp_context = mp.get_context("spawn")


class LoggingManager:
    """Владеет очередью логов и QueueListener'ом, который форвардит записи
    из solver-подпроцессов в те же хендлеры (консоль + файл), что и у
    основного процесса.
    """

    def __init__(self) -> None:
        self.log_queue: mp.Queue = _mp_context.Queue()
        self.listener = logging.handlers.QueueListener(
            self.log_queue, *logging.getLogger().handlers, respect_handler_level=True
        )
        self.listener.start()

    def shutdown(self) -> None:
        self.listener.stop()


logging_manager: LoggingManager | None = None


def configure_logging() -> None:
    """Настраивает консоль + ротируемый файл на root-логгере основного
    процесса, затем поднимает LoggingManager поверх них.

    Вызывать после run_migrations() — alembic сбрасывает логирование через
    fileConfig(), так что настраивать нужно после, а не до.
    """
    formatter = logging.Formatter(_FORMAT)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    settings.app_log_dir.mkdir(parents=True, exist_ok=True)
    file_handler = logging.handlers.RotatingFileHandler(
        settings.app_log_dir / "app.log",
        maxBytes=settings.app_log_max_bytes,
        backupCount=settings.app_log_backup_count,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(settings.log_level)
    root_logger.handlers = [console_handler, file_handler]

    global logging_manager
    if logging_manager is not None:
        logging_manager.shutdown()
    logging_manager = LoggingManager()


def configure_subprocess_logging(log_queue: mp.Queue) -> None:
    """Вызывается в спавненном solver-подпроцессе. log_queue приходит через
    args Process() — в spawn-процессе своя память, глобальный logging_manager
    родителя недоступен.
    """
    root_logger = logging.getLogger()
    root_logger.handlers = [logging.handlers.QueueHandler(log_queue)]
    root_logger.setLevel(settings.log_level)
