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

  const loadJobs = async () => {
    const payload = await api.get<{ total: number; items: Job[] }>('/jobs');
    setJobs(payload.items);
  };

  useEffect(() => {
    loadJobs().catch((error) => console.error(error));
  }, []);

  const selectJob = async (job: Job) => {
    setSelectedJob(job);
    const response = await api.get<{ job_id: string; lines: JobLogLine[] }>(`/jobs/${job.id}/logs`);
    setLogs(response.lines);
  };

  return (
    <div>
      <PageHeader title="Jobs" subtitle="Observe long-running tasks and inspect logs" />
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
            { header: 'Status', accessor: (job) => <StatusBadge status={job.status} /> },
            {
              header: 'Started',
              accessor: (job) => (job.started_at ? new Date(job.started_at).toLocaleString() : '—')
            },
            {
              header: 'Duration',
              accessor: (job) => (job.duration_ms ? `${(job.duration_ms / 1000).toFixed(1)} s` : '—')
            }
          ]}
        />
        <LogViewer lines={logs} />
      </div>
    </div>
  );
};

export default JobsPage;
