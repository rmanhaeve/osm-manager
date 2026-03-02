import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import useApi from '../hooks/useApi';
import { Job } from '../types/api';

type JobCounts = {
  running: number;
  pending: number;
  failed: number;
  recentError: Job | null;
};

const ActivityBar = () => {
  const api = useApi();
  const [counts, setCounts] = useState<JobCounts>({
    running: 0,
    pending: 0,
    failed: 0,
    recentError: null
  });

  useEffect(() => {
    const fetchJobs = async () => {
      try {
        const response = await api.get<{ total: number; items: Job[] }>('/jobs');
        const jobs = response.items;

        const running = jobs.filter((j) => j.status === 'running').length;
        const pending = jobs.filter((j) => j.status === 'pending').length;
        const failedJobs = jobs.filter((j) => j.status === 'failed');
        const failed = failedJobs.length;

        // Find most recent failed job
        const recentError = failedJobs.length > 0
          ? failedJobs.sort((a, b) => {
              const aTime = a.finished_at || a.started_at || '';
              const bTime = b.finished_at || b.started_at || '';
              return bTime.localeCompare(aTime);
            })[0]
          : null;

        setCounts({ running, pending, failed, recentError });
      } catch (err) {
        console.error('Failed to fetch job counts', err);
      }
    };

    fetchJobs();
    const interval = setInterval(fetchJobs, 10000);
    return () => clearInterval(interval);
  }, [api]);

  const hasActivity = counts.running > 0 || counts.pending > 0 || counts.failed > 0;

  if (!hasActivity) {
    return null;
  }

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '1rem',
        padding: '0.6rem 1rem',
        background: '#1e293b',
        borderRadius: '0.5rem',
        marginBottom: '1rem',
        fontSize: '0.85rem',
        flexWrap: 'wrap'
      }}
    >
      {counts.running > 0 && (
        <Link to="/jobs" style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: '#3b82f6' }}>
          <span
            style={{
              width: '0.6rem',
              height: '0.6rem',
              borderRadius: '50%',
              background: '#3b82f6',
              animation: 'pulse 1.5s infinite'
            }}
          />
          <span>{counts.running} Running</span>
        </Link>
      )}

      {counts.pending > 0 && (
        <Link to="/jobs" style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: '#f59e0b' }}>
          <span
            style={{
              width: '0.6rem',
              height: '0.6rem',
              borderRadius: '50%',
              background: '#f59e0b'
            }}
          />
          <span>{counts.pending} Pending</span>
        </Link>
      )}

      {counts.failed > 0 && (
        <Link to="/jobs" style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: '#ef4444' }}>
          <span
            style={{
              width: '0.6rem',
              height: '0.6rem',
              borderRadius: '50%',
              background: '#ef4444'
            }}
          />
          <span>{counts.failed} Failed</span>
          {counts.recentError && (
            <span style={{ opacity: 0.7, fontSize: '0.75rem' }}>
              ({counts.recentError.type} - {counts.recentError.target_db || 'no target'})
            </span>
          )}
        </Link>
      )}

      <style>
        {`
          @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.4; }
          }
        `}
      </style>
    </div>
  );
};

export default ActivityBar;
