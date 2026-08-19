from app.database import SessionLocal
from app.models.batch import Batch
from app.models.job import Job
from app.schemas.batches import BatchResponse
from app.services.jobs.query import _to_job_response

DEFAULT_LIST_LIMIT = 50


def _to_batch_response(batch: Batch, jobs: list[Job]) -> BatchResponse:
    return BatchResponse(
        batch_id=batch.id,
        solver=batch.solver,
        state=batch.state,
        total=batch.total,
        completed=batch.completed,
        created_by=batch.created_by,
        created_at=batch.created_at,
        jobs=[_to_job_response(job) for job in jobs],
    )


def _child_jobs(session, batch_id: str) -> list[Job]:
    return (
        session.query(Job)
        .filter_by(batch_id=batch_id)
        .order_by(Job.batch_index)
        .all()
    )


def get_batch_response(batch_id: str) -> BatchResponse | None:
    with SessionLocal() as session:
        batch = session.get(Batch, batch_id)
        if batch is None:
            return None
        return _to_batch_response(batch, _child_jobs(session, batch_id))


def list_batch_responses(limit: int = DEFAULT_LIST_LIMIT, offset: int = 0) -> list[BatchResponse]:
    with SessionLocal() as session:
        batches = (
            session.query(Batch)
            .order_by(Batch.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return [_to_batch_response(batch, _child_jobs(session, batch.id)) for batch in batches]
