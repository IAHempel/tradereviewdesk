"""Placeholder background worker entry point for future report jobs."""


def enqueue_report_job(job_id: str) -> dict[str, str]:
    return {"job_id": job_id, "status": "queued"}
