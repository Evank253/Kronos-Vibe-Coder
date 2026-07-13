import os
import tempfile
from backend.jobs import init_db, create_job, get_job, update_job_status


def test_jobs_create_and_get(tmp_path):
    # ensure DB in temp location
    os.environ['PWD'] = str(tmp_path)
    init_db()
    job_id = 'job1'
    create_job(job_id, repo='owner/repo', payload={'k': 'v'})
    j = get_job(job_id)
    assert j is not None
    assert j['id'] == job_id
    update_job_status(job_id, 'completed', {'result': 'ok'})
    j2 = get_job(job_id)
    assert j2['status'] == 'completed'
