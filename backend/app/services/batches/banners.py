_WIDTH = 60


def _line(text: str = "") -> str:
    inner = f" {text}".ljust(_WIDTH - 2)
    return f"║{inner}║"


def task_start_banner(index: int, total: int, filename: str, job_id: str) -> list[str]:
    top = "╔" + "═" * (_WIDTH - 2) + "╗"
    bottom = "╚" + "═" * (_WIDTH - 2) + "╝"
    return [
        "",
        top,
        _line(f"ЗАДАЧА {index} / {total}"),
        _line(f"Файл: {filename}"),
        _line(f"job_id: {job_id}"),
        bottom,
    ]


def task_end_banner(index: int, total: int, state: str) -> list[str]:
    label = f" Задача {index}/{total} завершена: {state} "
    return ["─" * _WIDTH, f"{label:─^{_WIDTH}}", "─" * _WIDTH, ""]


def batch_cancelled_banner(completed: int, total: int) -> list[str]:
    return [
        "",
        "═" * _WIDTH,
        _line(f"БАТЧ ОТМЕНЁН: {completed} / {total} задач обработано"),
        "═" * _WIDTH,
    ]


def batch_done_banner(total: int) -> list[str]:
    return [
        "",
        "═" * _WIDTH,
        _line(f"БАТЧ ЗАВЕРШЁН: {total} / {total} задач обработано"),
        "═" * _WIDTH,
    ]
