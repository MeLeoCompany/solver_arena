from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.schemas.comparison import (
    CompareBatchesRequest,
    CompareBatchesResponse,
    CompareJobsRequest,
    CompareJobsResponse,
)
from app.services.comparison import objective, solution_diff, violations
from app.services.comparison.batch import BatchComparisonError, compare_batches
from app.services.comparison.loader import ComparisonError, load_comparable_job
from app.services.comparison.report.batches_report import render_compare_batches_pdf
from app.services.comparison.report.jobs_report import render_compare_jobs_pdf

router = APIRouter()


@router.post("/compare/jobs", response_model=CompareJobsResponse)
async def compare_jobs(request: CompareJobsRequest) -> CompareJobsResponse:
    if not request.alt_job_ids:
        raise HTTPException(status_code=400, detail="at least one alt_job_id is required")

    try:
        reference = load_comparable_job(request.reference_job_id)
        alternatives = [load_comparable_job(job_id) for job_id in request.alt_job_ids]
    except ComparisonError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return CompareJobsResponse(
        reference_job_id=reference.job_id,
        reference_minimize=reference.problem.minimize,
        objective=objective.compare(reference, alternatives),
        violations=violations.analyze([reference, *alternatives]),
        solution_diff=solution_diff.compare(reference, alternatives),
    )


@router.post("/compare/batches", response_model=CompareBatchesResponse)
async def compare_batches_endpoint(request: CompareBatchesRequest) -> CompareBatchesResponse:
    try:
        return compare_batches(request.reference_batch_id, request.alt_batch_id)
    except BatchComparisonError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/compare/jobs/report")
async def compare_jobs_report(request: CompareJobsRequest) -> Response:
    result = await compare_jobs(request)
    pdf_bytes = render_compare_jobs_pdf(result)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="compare-{result.reference_job_id[:8]}.pdf"'},
    )


@router.post("/compare/batches/report")
async def compare_batches_report(request: CompareBatchesRequest) -> Response:
    result = await compare_batches_endpoint(request)
    pdf_bytes = render_compare_batches_pdf(result)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="compare-batches-{result.reference_batch_id[:8]}.pdf"'
        },
    )
