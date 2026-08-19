from app.config import settings
from app.schemas.jobs import JobResponse
from app.services.jobs import external_runner
from app.services.mps.parser import parse_mps


async def solve(
    mps_bytes: bytes,
    flags: dict,
    job_id: str | None = None,
    filename: str | None = None,
    created_by: str | None = None,
) -> JobResponse:
    config = str(flags.get("config") or "")

    spec_extra = {
        "config": config,
        "license_file": str(settings.qore_license_file),
        "module_dir": str(settings.qore_engine_dir),
    }

    # QORE's own read_model_from_file() silently drops any QMATRIX section
    # (verified empirically: is_qp() stays False after loading a file with
    # one) — parse it ourselves and hand the Hessian to qore_solve.py so it
    # can inject it via set_quadratic_objective(), which QORE's own docs
    # confirm is additive to whatever read_model_from_file built.
    problem = parse_mps(mps_bytes.decode("utf-8", errors="replace"))
    if problem.is_qp:
        spec_extra["quad_rows"] = problem.quad_rows.tolist()
        spec_extra["quad_cols"] = problem.quad_cols.tolist()
        spec_extra["quad_values"] = problem.quad_values.tolist()

    return await external_runner.run(
        "qore",
        str(settings.qore_python_executable),
        str(settings.qore_solve_script),
        mps_bytes,
        spec_extra=spec_extra,
        job_id=job_id,
        filename=filename,
        created_by=created_by,
    )
