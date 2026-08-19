import io

from reportlab.lib.pagesizes import A4
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from app.schemas.comparison import CompareBatchesResponse
from app.services.comparison.report.builder import data_table, format_num, metric_explainer, section_heading
from app.services.comparison.report.jobs_report import (
    OBJECTIVE_FORMULA,
    SOLUTION_DIFF_FORMULA,
    VIOLATIONS_FORMULA,
)
from app.services.comparison.report.styles import INTRO, PAGE_MARGIN, SUMMARY_NOTE, TITLE


def _file_label(reference: str | None, alt: str | None) -> str:
    if reference and alt and reference != alt:
        return f"{reference} / {alt}"
    return reference or alt or "—"


def _short(job_id: str | None) -> str:
    return job_id[:8] if job_id else "—"


def render_compare_batches_pdf(response: CompareBatchesResponse) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=PAGE_MARGIN,
        rightMargin=PAGE_MARGIN,
        topMargin=PAGE_MARGIN,
        bottomMargin=PAGE_MARGIN,
        title="Сравнение групп",
    )

    total = len(response.objective)
    with_error = sum(1 for row in response.objective if row.error)
    summary = f"Сопоставлено файлов: {total}"
    if with_error > 0:
        summary += f", из них с ошибкой сопоставления: {with_error}"

    story: list = [
        Paragraph("Сравнение групп", TITLE),
        Paragraph(
            f"Эталонная группа: {response.reference_batch_id[:8]} · альтернативная группа: "
            f"{response.alt_batch_id[:8]}",
            INTRO,
        ),
        Paragraph(summary, SUMMARY_NOTE),
        section_heading("Целевая функция"),
    ]
    story.extend(
        metric_explainer(
            "То же сравнение, что и для одиночных задач, только по каждому файлу группы отдельно. "
            "«Δ (эталон − альт)» — это разница, а не модуль: отрицательное значение означает, что у "
            "альтернативы число больше эталонного, положительное — меньше.",
            OBJECTIVE_FORMULA,
        )
    )
    story.append(_objective_table(response))
    story.append(Spacer(1, 6))

    story.append(section_heading("Нарушение ограничений"))
    story.extend(
        metric_explainer(
            "Проверяет, насколько сильно решение выходит за границы ограничений задачи — отдельно "
            "для решения каждого файла в каждой группе, это не сравнение эталона с альтернативой.",
            VIOLATIONS_FORMULA,
        )
    )
    story.append(_violations_table(response))
    story.append(Spacer(1, 6))

    story.append(section_heading("Разница векторов решения"))
    story.extend(
        metric_explainer(
            "Сравнивает сами значения переменных — сколько переменных заметно отличаются между "
            "эталоном и альтернативой в каждом файле группы, и как эти отличия сказываются на "
            "целевой функции (линейная часть и квадратичная — для QP-задач).",
            SOLUTION_DIFF_FORMULA,
        )
    )
    story.append(_solution_diff_table(response))

    doc.build(story)
    return buffer.getvalue()


def _objective_table(response: CompareBatchesResponse):
    headers = ["#", "Файл", "Эталон", "Альт", "Солвер", "Obj (эталон)", "Obj (альт)", "Δ (эталон − альт)", "Δ %", "Статус"]
    rows: list[list[str]] = []
    error_flags: list[bool] = []
    for row in response.objective:
        lead = [str(row.batch_index), _file_label(row.reference_filename, row.alt_filename), _short(row.reference_job_id), _short(row.alt_job_id)]
        if row.error:
            rows.append([*lead, row.error, "", "", "", "", ""])
            error_flags.append(True)
        else:
            rows.append(
                [
                    *lead,
                    row.alt_solver,
                    format_num(row.reference_objective),
                    format_num(row.alt_objective),
                    format_num(row.delta_abs),
                    f"{format_num(row.delta_rel_pct)}%",
                    f"{row.reference_status or '—'} / {row.alt_status or '—'}",
                ]
            )
            error_flags.append(False)
    return data_table(headers, rows, error_flags)


def _violations_table(response: CompareBatchesResponse):
    headers = ["#", "Файл", "Задача", "Солвер", "Max violation", "Кол-во нарушений", "В допуске"]
    rows = []
    error_flags = []
    for row in response.violations:
        lead = [str(row.batch_index), row.filename or "—", _short(row.job_id)]
        if row.error:
            rows.append([*lead, row.error, "", ""])
            error_flags.append(True)
        else:
            rows.append(
                [
                    *lead,
                    row.solver,
                    format_num(row.max_violation),
                    str(row.num_violations),
                    "да" if row.within_tolerance else "нет",
                ]
            )
            error_flags.append(False)
    return data_table(headers, rows, error_flags)


def _solution_diff_table(response: CompareBatchesResponse):
    headers = ["#", "Файл", "Эталон", "Альт", "Солвер", "Кол-во отличий", "Макс. |Δx|", "Impact линейный", "Impact квадратичный", "Impact итого"]
    rows = []
    error_flags = []
    for row in response.solution_diff:
        lead = [str(row.batch_index), _file_label(row.reference_filename, row.alt_filename), _short(row.reference_job_id), _short(row.alt_job_id)]
        if row.error:
            rows.append([*lead, row.error, "", "", "", "", ""])
            error_flags.append(True)
        else:
            rows.append(
                [
                    *lead,
                    row.alt_solver,
                    str(row.num_diffs),
                    format_num(row.max_diff),
                    format_num(row.objective_impact_linear),
                    format_num(row.objective_impact_quadratic),
                    format_num(row.objective_impact_total),
                ]
            )
            error_flags.append(False)
    return data_table(headers, rows, error_flags)
