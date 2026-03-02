import { useEffect, useState } from 'react';
import PageHeader from '../components/PageHeader';
import DataTable from '../components/DataTable';
import StatusBadge from '../components/StatusBadge';
import useApi from '../hooks/useApi';
import { Job, JobLogLine } from '../types/api';
import LogViewer from '../components/LogViewer';
import { useToast } from '../components/ToastProvider';

const JobsPage = () => {
  const api = useApi();
  const { addToast } = useToast();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [logs, setLogs] = useState<JobLogLine[]>([]);
  const [error, setError] = useState<string | null>(null);

  const loadJobs = async () => {
    const payload = await api.get<{ total: number; items: Job[] }>('/jobs');
    setJobs(payload.items);
  };

  useEffect(() => {
    loadJobs().catch((err) => console.error(err));
  }, []);

  useEffect(() => {
    const interval = window.setInterval(() => {
      loadJobs().catch((err) => console.error(err));
    }, 5000);
    return () => window.clearInterval(interval);
  }, []);

  const selectJob = async (job: Job) => {
    setSelectedJob(job);
    setLogs([]);
    setError(null);
    try {
      const response = await api.get<{ job_id: string; lines: JobLogLine[] }>(`/jobs/${job.id}/logs`);
      setLogs(response.lines);
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message);
      }
    }
  };

  const retryJob = async (job: Job) => {
    setError(null);
    try {
      const newJob = await api.post<Job>(`/jobs/${job.id}/retry`, {});
      addToast('success', `Retry queued for ${job.type} job`);
      await loadJobs();
      setSelectedJob(newJob);
      setLogs([]);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Retry failed';
      addToast('error', message);
      setError(message);
    }
  };

  const selectedJobStatus = selectedJob
    ? jobs.find((job) => job.id === selectedJob.id)?.status || selectedJob.status
    : undefined;

  const selectedJobData = selectedJob
    ? jobs.find((job) => job.id === selectedJob.id) || selectedJob
    : null;

  useEffect(() => {
    if (!selectedJob) {
      return undefined;
    }

    let cancelled = false;

    const fetchLogs = async () => {
      try {
        const response = await api.get<{ job_id: string; lines: JobLogLine[] }>(`/jobs/${selectedJob.id}/logs`);
        if (!cancelled) {
          setLogs(response.lines);
        }
      } catch (err) {
        if (!cancelled && err instanceof Error) {
          setError(err.message);
        }
      }
    };

    fetchLogs().catch((err) => console.error(err));

    if (selectedJobStatus === 'pending' || selectedJobStatus === 'running') {
      const interval = window.setInterval(() => {
        fetchLogs().catch((err) => console.error(err));
      }, 2000);
      return () => {
        cancelled = true;
        window.clearInterval(interval);
      };
    }

    return () => {
      cancelled = true;
    };
  }, [api, selectedJob, selectedJobStatus]);

  return (
    <div>
      <PageHeader title="Jobs" subtitle="Observe long-running tasks and inspect logs" />
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
          rowClassName={(job) => (selectedJob?.id === job.id ? 'is-selected' : undefined)}
        />
        <div>
          {/* Error Message Panel */}
          {selectedJobData?.status === 'failed' && selectedJobData.error_message && (
            <div
              className="card"
              style={{
                borderLeft: '4px solid #dc2626',
                background: '#fef2f2',
                marginBottom: '1rem',
                padding: '1rem'
              }}
            >
              <div style={{ fontWeight: 600, color: '#991b1b', marginBottom: '0.5rem', fontSize: '0.9rem' }}>
                Error: {selectedJobData.type} failed
              </div>
              <div style={{ color: '#b91c1c', fontSize: '0.85rem', fontFamily: 'monospace' }}>
                {selectedJobData.error_message}
              </div>
            </div>
          )}

          {/* Job Details */}
          {selectedJobData && (
            <div className="card" style={{ marginBottom: '1rem', padding: '1rem' }}>
              <div style={{ fontSize: '0.85rem', color: '#475569' }}>
                <div style={{ display: 'grid', gridTemplateColumns: 'auto 1fr', gap: '0.5rem 1rem' }}>
                  <span style={{ fontWeight: 600 }}>Job ID:</span>
                  <span style={{ fontFamily: 'monospace' }}>{selectedJobData.id}</span>
                  <span style={{ fontWeight: 600 }}>Type:</span>
                  <span>{selectedJobData.type}</span>
                  <span style={{ fontWeight: 600 }}>Target:</span>
                  <span>{selectedJobData.target_db || '—'}</span>
                  <span style={{ fontWeight: 600 }}>Status:</span>
                  <StatusBadge status={selectedJobData.status} />
                  {selectedJobData.params && Object.keys(selectedJobData.params).length > 0 && (
                    <>
                      <span style={{ fontWeight: 600 }}>Parameters:</span>
                      <details style={{ fontSize: '0.8rem' }}>
                        <summary style={{ cursor: 'pointer', color: '#2563eb' }}>View params</summary>
                        <pre style={{ margin: '0.5rem 0 0', whiteSpace: 'pre-wrap', background: '#f1f5f9', padding: '0.5rem', borderRadius: '0.25rem' }}>
                          {JSON.stringify(selectedJobData.params, null, 2)}
                        </pre>
                      </details>
                    </>
                  )}
                </div>
              </div>
            </div>
          )}

          <LogViewer
            lines={logs}
            title={selectedJobData ? `Logs: ${selectedJobData.id.slice(0, 8)}` : 'Logs'}
          />
        </div>
      </div>
    </div>
  );
};

export default JobsPage;
