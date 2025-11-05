import { useEffect, useState } from 'react';
import PageHeader from '../components/PageHeader';
import DataTable from '../components/DataTable';
import StatusBadge from '../components/StatusBadge';
import useApi from '../hooks/useApi';
import { Job, JobLogLine } from '../types/api';
import LogViewer from '../components/LogViewer';

const JobsPage = () => {
  const api = useApi();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [logs, setLogs] = useState<JobLogLine[]>([]);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadJobs = async () => {
    const payload = await api.get<{ total: number; items: Job[] }>('/jobs');
    setJobs(payload.items);
  };

  useEffect(() => {
    loadJobs().catch((err) => console.error(err));
  }, []);

  const selectJob = async (job: Job) => {
    setSelectedJob(job);
    const response = await api.get<{ job_id: string; lines: JobLogLine[] }>(`/jobs/${job.id}/logs`);
    setLogs(response.lines);
  };

  const retryJob = async (job: Job) => {
    setMessage(null);
    setError(null);
    try {
      const newJob = await api.post<Job>(`/jobs/${job.id}/retry`, {});
      setMessage('Retry queued. Refresh to track progress.');
      await loadJobs();
      setSelectedJob(newJob);
      setLogs([]);
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Retry failed. Check server logs for details.');
      }
    }
  };

  return (
    <div>
      <PageHeader title="Jobs" subtitle="Observe long-running tasks and inspect logs" />
      {message && (
        <div className="card" style={{ borderLeft: '4px solid #16a34a', color: '#166534', marginBottom: '1rem' }}>
          {message}
        </div>
      )}
      {error && (
        <div className="card" style={{ borderLeft: '4px solid #dc2626', color: '#991b1b', marginBottom: '1rem' }}>
          {error}
        </div>
      )}
      <div className="grid two">
        <DataTable
          data={jobs}
          columns={[
            {
              header: 'Job',
              accessor: (job) => (
                <button
                  type="button"
                  style={{ background: 'none', border: 'none', padding: 0, color: '#2563eb', cursor: 'pointer' }}
                  onClick={() => selectJob(job)}
                >
                  {job.id.slice(0, 8)}
                </button>
              )
            },
            { header: 'Type', accessor: (job) => job.type },
            { header: 'Target', accessor: (job) => job.target_db || '—' },
            {
              header: 'Status',
              accessor: (job) => (
                <div style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem' }}>
                  <StatusBadge status={job.status} />
                  {job.status === 'failed' && (
                    <button
                      type="button"
                      className="btn btn-small-secondary"
                      onClick={() => retryJob(job)}
                      title="Retry job"
                      aria-label="Retry job"
                    >
                      ↺
                    </button>
                  )}
                </div>
              )
            },
            {
              header: 'Started',
              accessor: (job) => (job.started_at ? new Date(job.started_at).toLocaleString() : '—')
            },
            {
              header: 'Duration',
              accessor: (job) => (job.duration_ms ? `${(job.duration_ms / 1000).toFixed(1)} s` : '—')
            },
          ]}
        />
        <LogViewer lines={logs} />
      </div>
    </div>
  );
};

export default JobsPage;
