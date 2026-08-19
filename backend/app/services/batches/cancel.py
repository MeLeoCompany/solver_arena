import logging

from app.services.batches.registry import batch_registry
from app.services.jobs.cancel import request_cancel as request_job_cancel


def request_batch_cancel(batch_id: str) -> bool:
    """Stops the batch after its currently running job finishes, and also
    cancels that job immediately (rather than waiting it out) so the user
    doesn't have to sit through a long-running solve just to cancel a batch.
    """
    ok = batch_registry.request_cancel(batch_id)
    if not ok:
        return False
    current_job_id = batch_registry.get_current_job(batch_id)
    if current_job_id is not None:
        request_job_cancel(current_job_id)
    logging.info("batch %s: cancel requested", batch_id)
    return True
