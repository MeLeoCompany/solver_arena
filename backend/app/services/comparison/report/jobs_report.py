import io

from reportlab.lib.pagesizes import A4
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from app.schemas.comparison import CompareJobsResponse
from app.services.comparison.report.builder import data_table, format_num, metric_explainer, section_heading
from app.services.comparison.report.styles import BODY, INTRO, PAGE_MARGIN, TITLE, WARNING_NOTE

# Descriptions/formulas mirror MetricExplainer usages in
# frontend/src/pages/ComparePage.tsx — intentionally duplicated text (same
# convention already used for state labels between frontend and backend),
# not worth a shared-content pipeline across two languages for three
# paragraphs of copy.

OBJECTIVE_FORMULA = (
    "Δ_abs = obj(эталон) − obj(альт)\n"
    "Δ_% = Δ_abs / max(|obj(эталон)|, |obj(альт)|, ε) × 100,   ε = 1e-9"
)

VIOLATIONS_FORMULA = (
    "Для ограничения i с границами [lo_i, hi_i]:\n"
    "нарушение_i = насколько (Ax)_i вышло за пределы [lo_i, hi_i], иначе 0\n"
    "max_violation = наибольшее нарушение среди всех ограничений\n"
    "в допуске = max_violation ≤ ε,   ε = 1e-6"
)

SOLUTION_DIFF_FORMULA = (
    "Δx = x(эталон) − x(альт)\n"
    "Кол-во отличий — число переменных с |Δx_i| > ε, влияющих на целевую функцию,   ε = 1e-6\n"
    "Impact линейный = Σ f_i·Δx_i  по этим переменным\n"
    "Impact квадратичный = 0.5·x(эталон)ᵀQx(эталон) − 0.5·x(альт)ᵀQx(альт)\n"
    "Impact итого = линейный + квадратичный"
)


def render_compare_jobs_pdf(response: CompareJobsResponse) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=PAGE_MARGIN,
        rightMargin=PAGE_MARGIN,
        topMargin=PAGE_MARGIN,
        bottomMargin=PAGE_MARGIN,
        title="Сравнение решений",
    )

    direction_word = "минимизация" if response.reference_minimize else "максимизация"

    story: list = [
        Paragraph("Сравнение решений", TITLE),
        Paragraph(
            f"Эталонная задача: {response.reference_job_id} · направление оптимизации: {direction_word}",
            INTRO,
        ),
        section_heading(f"Целевая функция ({direction_word})"),
    ]
    story.extend(
        metric_explainer(
            f"Направление оптимизации эталонной задачи — {direction_word}. Насколько значение целевой "
            "функции у альтернативной задачи отличается от эталонной — в абсолютных числах и в "
            "процентах. «Δ (эталон − альт)» — это разница, а не модуль: отрицательное значение означает, "
            "что у альтернативы число больше эталонного, положительное — меньше (независимо от "
            "направления оптимизации).",
            OBJECTIVE_FORMULA,
        )
    )
    story.append(_objective_table(response))
    for row in response.objective:
        if not row.error and row.alt_minimize != response.reference_minimize:
            direction = "минимизация" if row.alt_minimize else "максимизация"
            story.append(
                Paragraph(
                    f"⚠ {row.alt_job_id[:8]}: другое направление оптимизации ({direction}) — "
                    "сравнение может быть некорректным",
                    WARNING_NOTE,
                )
            )
    story.append(Spacer(1, 6))

    story.append(section_heading("Нарушение ограничений"))
    story.extend(
        metric_explainer(
            "Проверяет, насколько сильно решение выходит за границы ограничений задачи (например, "
            "x + y ≤ 10) — отдельно для решения каждой задачи, это не сравнение эталона с альтернативой. "
            "«В допуске» = да означает, что все ограничения выполнены (с точностью до погрешности "
            "решателя).",
            VIOLATIONS_FORMULA,
        )
    )
    story.append(_violations_table(response))
    story.append(Spacer(1, 6))

    story.append(section_heading("Разница векторов решения"))
    story.extend(
        metric_explainer(
            "Сравнивает сами значения переменных (не только итоговую целевую функцию) — сколько "
            "переменных заметно отличаются между эталоном и альтернативой, и как эти отличия "
            "сказываются на целевой функции. Влияние показано отдельно: линейная часть и квадратичная "
            "(для QP-задач с квадратичным членом в целевой функции — для обычных LP/MILP она всегда 0).",
            SOLUTION_DIFF_FORMULA,
        )
    )
    story.append(_solution_diff_table(response))

    doc.build(story)
    return buffer.getvalue()


def _objective_table(response: CompareJobsResponse):
    headers = ["Альт. задача", "Солвер", "Obj (эталон)", "Obj (альт)", "Δ (эталон − альт)", "Δ %", "Статус эталон / альт"]
    rows: list[list[str]] = []
    error_flags: list[bool] = []
    for row in response.objective:
        if row.error:
            rows.append([row.alt_job_id[:8], row.alt_solver, row.error, "", "", "", ""])
            error_flags.append(True)
        else:
            rows.append(
                [
                    row.alt_job_id[:8],
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


def _violations_table(response: CompareJobsResponse):
    headers = ["Задача", "Солвер", "Max violation", "Кол-во нарушений", "В допуске"]
    rows = []
    error_flags = []
    for row in response.violations:
        if row.error:
            rows.append([row.job_id[:8], row.solver, row.error, "", ""])
            error_flags.append(True)
        else:
            rows.append(
                [
                    row.job_id[:8],
                    row.solver,
                    format_num(row.max_violation),
                    str(row.num_violations),
                    "да" if row.within_tolerance else "нет",
                ]
            )
            error_flags.append(False)
    return data_table(headers, rows, error_flags)


def _solution_diff_table(response: CompareJobsResponse):
    headers = ["Альт. задача", "Солвер", "Кол-во отличий", "Макс. |Δx|", "Impact линейный", "Impact квадратичный", "Impact итого"]
    rows = []
    error_flags = []
    for row in response.solution_diff:
        if row.error:
            rows.append([row.alt_job_id[:8], row.alt_solver, row.error, "", "", "", ""])
            error_flags.append(True)
        else:
            rows.append(
                [
                    row.alt_job_id[:8],
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
