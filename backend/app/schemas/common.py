from enum import Enum


class JobState(str, Enum):
    """Где задача находится в своём жизненном цикле как процесс.

    Не говорит о результате решения — только о том, выполнилась ли задача.
    `failed` — упал сам процесс (OOM, исключение, инфра), а не солвер
    честно признал infeasible/timeout — это уже SolveStatus.
    """

    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SolveStatus(str, Enum):
    """Вердикт солвера по задаче. Имеет смысл только при JobState.DONE.

    Не покрывает все возможные исходы всех солверов — см. raw_status
    на моделях ответа для сырого кода конкретного солвера.
    """

    OPTIMAL = "optimal"
    FEASIBLE = "feasible"
    INFEASIBLE = "infeasible"
    TIMEOUT = "timeout"
    UNBOUNDED = "unbounded"
